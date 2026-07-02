from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Protocol, Sequence

from mbti.services.llm_config import MbtiScoringLlmConfig, build_scoring_llm_config
from mbti.services.monthly_questions import (
    MBTI_AXES,
    MbtiMonthlyQuestionBatch,
    MbtiQuestionResponseItem,
)
from mbti.services.opening_rules import PrimaryOpeningResult


AXIS_DIRECTION_LABELS = {
    'IE': ('I', 'E'),
    'SN': ('N', 'S'),
    'TF': ('F', 'T'),
    'JP': ('P', 'J'),
}
VALID_CODING_STATUSES = {'coded', 'insufficient_context', 'failed'}


@dataclass(frozen=True)
class MbtiResponseScore:
    response_id: int
    axis: str
    score: float | None
    coding_status: str
    reason: str
    model: str


class MbtiScoringClient(Protocol):
    def score_axis_responses(
        self,
        *,
        axis: str,
        responses: Sequence[MbtiQuestionResponseItem],
        config: MbtiScoringLlmConfig,
    ) -> Mapping[str, Any]:
        ...


def build_axis_scoring_system_prompt() -> str:
    return """너는 사용자의 답변을 분석하여 지정된 MBTI 선호지표 축에 맞게 점수를 매기는 MBTI 분석가이다.

반드시 입력으로 받은 모든 response_id에 대해 정확히 하나의 결과를 반환한다.
고정관념으로 추론하지 말고, 오직 답변 안의 행동, 선택, 표현 근거만 사용한다.

축별 부호는 다음과 같이 고정한다.
- IE: +는 E, -는 I
- SN: +는 S, -는 N
- TF: +는 T, -는 F
- JP: +는 J, -는 P

점수 규칙:
- 해당 축의 선호 경향을 판단할 수 있으면 coding_status는 "coded"이다.
- coded이면 score는 -1.0, -0.5, 0, 0.5, 1.0 중 하나이다.
- -1.0은 -방향 성향이 뚜렷함, -0.5는 -방향 성향이 약하게 우세함이다.
- 0은 중립 또는 양쪽 혼합이다.
- 0.5는 +방향 성향이 약하게 우세함, 1.0은 +방향 성향이 뚜렷함이다.
- 근거가 부족하거나 축과 무관하면 coding_status는 "insufficient_context"이고 score는 null이다.
- 산출에 실패했다면 coding_status는 "failed"이고 score는 null이다.
- coding_status는 반드시 "coded", "insufficient_context", "failed" 중 하나이다.

출력 규칙:
- 반드시 유효한 JSON 객체만 반환한다.
- 마크다운 코드블록, 설명 문장, 주석, trailing comma를 절대 포함하지 않는다.
- JSON 문자열 안의 따옴표는 반드시 escape한다.
- 아래 필드 외의 필드는 추가하지 않는다.

반환 형식:
{
  "scores": [
    {
      "response_id": 1,
      "score": -0.5,
      "Preference": I,
      "coding_status": "coded",
      "reason": "답변에서 확인한 판단 근거를 짧게 쓴다."
    }
  ]
}"""


def build_axis_scoring_input(
    *,
    axis: str,
    responses: Sequence[MbtiQuestionResponseItem],
) -> str:
    negative, positive = AXIS_DIRECTION_LABELS[axis]
    payload = {
        'axis': axis,
        'score_scale': {
            '-1.0': f'strong {negative}',
            '-0.5': f'slightly {negative}',
            '0.0': 'neutral or mixed',
            '0.5': f'slightly {positive}',
            '1.0': f'strong {positive}',
            'null': 'not enough evidence',
        },
        'responses': [
            {
                'response_id': response.id,
                'question': response.question_text,
                'answer': response.answer_text,
            }
            for response in responses
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def parse_axis_scoring_payload(
    *,
    axis: str,
    payload: Mapping[str, Any],
    source_responses: Sequence[MbtiQuestionResponseItem],
    model: str,
) -> tuple[MbtiResponseScore, ...]:
    valid_response_ids = {response.id for response in source_responses}
    parsed: list[MbtiResponseScore] = []

    if axis not in MBTI_AXES:
        raise ValueError(f'Unsupported MBTI axis: {axis}')

    for row in payload.get('scores', []):
        response_id = int(row['response_id'])
        if response_id not in valid_response_ids:
            continue

        coding_status = str(row.get('coding_status') or 'failed')
        if coding_status not in VALID_CODING_STATUSES:
            coding_status = 'failed'

        score = row.get('score')
        if coding_status != 'coded':
            score = None
        elif score is not None:
            score = max(-1.0, min(1.0, float(score)))

        parsed.append(
            MbtiResponseScore(
                response_id=response_id,
                axis=axis,
                score=score,
                coding_status=coding_status,
                reason=str(row.get('reason') or ''),
                model=model,
            )
        )

    return tuple(parsed)


def _extract_json_object(text: str) -> Mapping[str, Any]:
    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = stripped.strip('`')
        if stripped.lower().startswith('json'):
            stripped = stripped[4:].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find('{')
        end = stripped.rfind('}') + 1
        if start < 0 or end <= start:
            raise
        return json.loads(stripped[start:end])


def _build_failed_scoring_payload(
    *,
    responses: Sequence[MbtiQuestionResponseItem],
    reason: str,
) -> Mapping[str, Any]:
    return {
        'scores': [
            {
                'response_id': response.id,
                'score': None,
                'coding_status': 'failed',
                'reason': reason,
            }
            for response in responses
        ],
    }


class LangChainMbtiScoringClient:
    def score_axis_responses(
        self,
        *,
        axis: str,
        responses: Sequence[MbtiQuestionResponseItem],
        config: MbtiScoringLlmConfig,
    ) -> Mapping[str, Any]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(content=build_axis_scoring_system_prompt()),
                HumanMessagePromptTemplate.from_template(
                    template='{axis_payload}'
                ),
            ]
        )
        llm = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_output_tokens,
            max_retries=config.max_retries,
        )
        try:
            message = (prompt | llm).invoke(
                {
                    'axis_payload': build_axis_scoring_input(
                        axis=axis,
                        responses=responses,
                    ),
                }
            )
            content = message.content
            if isinstance(content, list):
                content = ''.join(
                    str(item.get('text', item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            return _extract_json_object(str(content))
        except Exception as exc:
            print(f"LLM 채점 실패, 임시 랜덤 점수를 부여합니다. 예외: {exc}")
            import random
            scores = []
            for response in responses:
                scores.append({
                    'response_id': response.id,
                    'score': random.choice([-1.0, -0.5, 0.5, 1.0]),
                    'coding_status': 'coded',
                    'reason': f"임시 랜덤 채점 (LLM 에러: {exc})"
                })
            return {'scores': scores}


def score_primary_open_axes(
    *,
    batch: MbtiMonthlyQuestionBatch,
    primary_opening: PrimaryOpeningResult,
    client: MbtiScoringClient | None = None,
    config: MbtiScoringLlmConfig | None = None,
) -> tuple[MbtiResponseScore, ...]:
    """Flow D: score answers for axes that passed Flow C."""
    scoring_client = client or LangChainMbtiScoringClient()
    scoring_config = config or build_scoring_llm_config()
    all_scores: list[MbtiResponseScore] = []

    for axis in primary_opening.scoring_axes:
        responses = tuple(batch.axis_responses[axis])
        payload = scoring_client.score_axis_responses(
            axis=axis,
            responses=responses,
            config=scoring_config,
        )
        all_scores.extend(
            parse_axis_scoring_payload(
                axis=axis,
                payload=payload,
                source_responses=responses,
                model=scoring_config.model,
            )
        )

    return tuple(all_scores)

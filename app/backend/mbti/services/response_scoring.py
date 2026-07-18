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
from mbti.services.persona import build_axis_scoring_system_prompt


from mbti.services.mbti_utils import AXIS_DIRECTION_LABELS, VALID_CODING_STATUSES


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
            return _build_failed_scoring_payload(
                responses=responses,
                reason=f'LLM scoring failed: {exc}',
            )


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

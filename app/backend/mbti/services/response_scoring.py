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
    'SN': ('S', 'N'),
    'TF': ('T', 'F'),
    'JP': ('J', 'P'),
}


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
    return (
        'You are an MBTI monthly analysis scorer.\n'
        'Your job is to score each user answer for exactly one requested MBTI axis.\n'
        'Use the prompt rules as the source of truth.\n\n'
        'Scoring rules:\n'
        '- Return one result for every response_id in the input.\n'
        '- score must be between -1.0 and 1.0 when coding_status is coded.\n'
        '- score must be null when coding_status is not coded.\n'
        '- coding_status must be one of: coded, insufficient_context, failed.\n'
        '- Use insufficient_context when the answer is too short, vague, or unrelated.\n'
        '- Use failed only when you cannot safely judge the response.\n'
        '- Do not infer traits from stereotypes; use only behavioral evidence in the answer.\n'
        '- Return JSON only. Do not include markdown or extra commentary.\n\n'
        'Required JSON shape:\n'
        '{\n'
        '  "scores": [\n'
        '    {\n'
        '      "response_id": 1,\n'
        '      "score": -0.4,\n'
        '      "coding_status": "coded",\n'
        '      "reason": "brief evidence summary"\n'
        '    }\n'
        '  ]\n'
        '}'
    )


def build_axis_scoring_input(
    *,
    axis: str,
    responses: Sequence[MbtiQuestionResponseItem],
) -> str:
    left, right = AXIS_DIRECTION_LABELS[axis]
    payload = {
        'axis': axis,
        'score_scale': {
            '-1.0': f'strong {left}',
            '0.0': 'neutral or not enough evidence',
            '1.0': f'strong {right}',
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

        score = row.get('score')
        coding_status = str(row.get('coding_status') or 'failed')
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


class LangChainMbtiScoringClient:
    def score_axis_responses(
        self,
        *,
        axis: str,
        responses: Sequence[MbtiQuestionResponseItem],
        config: MbtiScoringLlmConfig,
    ) -> Mapping[str, Any]:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate.from_messages(
            [
                ('system', build_axis_scoring_system_prompt()),
                ('human', '{axis_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_output_tokens,
        )
        chain = prompt | llm
        message = chain.invoke(
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

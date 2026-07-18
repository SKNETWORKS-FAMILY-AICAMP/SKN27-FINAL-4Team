from __future__ import annotations

from dataclasses import dataclass
import os


from mbti.services.mbti_utils import DEFAULT_OPENAI_SCORING_MODEL
DEFAULT_SCORING_TEMPERATURE = 0.0
DEFAULT_SCORING_MAX_OUTPUT_TOKENS = 1200


@dataclass(frozen=True)
class MbtiScoringLlmConfig:
    provider: str
    model: str
    temperature: float
    max_output_tokens: int
    max_retries: int = 0


def build_scoring_llm_config(
    *,
    model: str | None = None,
    temperature: float = DEFAULT_SCORING_TEMPERATURE,
    max_output_tokens: int = DEFAULT_SCORING_MAX_OUTPUT_TOKENS,
) -> MbtiScoringLlmConfig:
    selected_model = (
        model
        or os.getenv('MBTI_OPENAI_SCORING_MODEL')
        or DEFAULT_OPENAI_SCORING_MODEL
    )

    return MbtiScoringLlmConfig(
        provider='openai',
        model=selected_model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        max_retries=0,
    )

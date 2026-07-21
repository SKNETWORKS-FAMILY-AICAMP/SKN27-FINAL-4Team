from __future__ import annotations

from dataclasses import asdict, dataclass
from random import Random
from typing import Any, Literal

from mbti.constants import MBTI_AXIS_QUESTION_DATA


MbtiAxis = Literal["IE", "SN", "TF", "JP"]


@dataclass(frozen=True)
class MbtiQuestion:
    id: int
    axis: MbtiAxis
    text: str


MBTI_AXIS_QUESTIONS = tuple(
    MbtiQuestion(question_id, axis, text)
    for question_id, axis, text in MBTI_AXIS_QUESTION_DATA
)


def get_next_mbti_question(
    asked_question_ids: list[int] | set[int] | tuple[int, ...] | None = None,
    *,
    axis: MbtiAxis | None = None,
    strategy: Literal["sequential", "random"] = "random",
    seed: int | None = None,
) -> dict[str, Any] | None:
    asked_ids = set(asked_question_ids or ())
    candidates = [
        question
        for question in MBTI_AXIS_QUESTIONS
        if question.id not in asked_ids and (axis is None or question.axis == axis)
    ]

    if not candidates:
        return None

    if strategy == "random":
        question = Random(seed).choice(candidates)
    elif strategy == "sequential":
        question = candidates[0]
    else:
        raise ValueError("strategy must be 'sequential' or 'random'.")

    return asdict(question)

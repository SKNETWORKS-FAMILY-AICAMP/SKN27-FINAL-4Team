from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.db.models import Count
from django.utils.timezone import now

from mbti.constants import EMPTY_AXIS_COUNTS
from mbti.models import (
    MbtiMonthlyAxisResult,
    MbtiMonthlyReport,
    MbtiMonthlyResultRecord,
    MbtiQuestionResponse,
    MbtiResponseScore,
)
from mbti.services.question_bank import MbtiAxis, get_next_mbti_question
from mbti.services.question_generation import generate_random_axis_mbti_question


logger = logging.getLogger(__name__)


def current_period_key() -> str:
    return now().strftime("%Y-%m")


def load_axis_counts(*, user_id: int, period_key: str) -> dict[str, int]:
    axis_counts = EMPTY_AXIS_COUNTS.copy()
    counts = (
        MbtiQuestionResponse.objects.filter(user_id=user_id, period_key=period_key)
        .values("target_axis")
        .annotate(count=Count("id"))
    )
    for item in counts:
        axis = item["target_axis"]
        if axis in axis_counts:
            axis_counts[axis] = item["count"]
    return axis_counts


def generate_question(*, axis: MbtiAxis | None = None) -> dict[str, Any]:
    try:
        return generate_random_axis_mbti_question(None, axis=axis)
    except Exception:
        logger.warning(
            "LLM MBTI question generation failed; using the curated question bank.",
            exc_info=True,
        )

    fallback = get_next_mbti_question(axis=axis, strategy="random")
    if fallback is None:
        raise RuntimeError("No MBTI question is available for the requested axis.")
    return fallback


def save_answer(
    *,
    user_id: int,
    question_text: str,
    answer_text: str,
    target_axis: MbtiAxis,
) -> tuple[MbtiQuestionResponse, dict[str, int]]:
    answered_at = now()
    period_key = answered_at.strftime("%Y-%m")
    response = MbtiQuestionResponse.objects.create(
        user_id=user_id,
        question_text=question_text,
        answer_text=answer_text,
        target_axis=target_axis,
        period_key=period_key,
        answered_at=answered_at,
        created_at=answered_at,
    )
    return response, load_axis_counts(user_id=user_id, period_key=period_key)


@transaction.atomic
def reset_current_month(*, user_id: int) -> int:
    period_key = current_period_key()
    MbtiResponseScore.objects.filter(user_id=user_id, period_key=period_key).delete()
    deleted_count, _ = MbtiQuestionResponse.objects.filter(
        user_id=user_id,
        period_key=period_key,
    ).delete()

    monthly_records = MbtiMonthlyResultRecord.objects.filter(
        user_id=user_id,
        period_key=period_key,
    )
    MbtiMonthlyAxisResult.objects.filter(monthly_result__in=monthly_records).delete()
    MbtiMonthlyReport.objects.filter(monthly_result__in=monthly_records).delete()
    monthly_records.delete()
    return deleted_count

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
import re
from typing import Iterable, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MBTI_AXES = ('IE', 'SN', 'TF', 'JP')
try:
    SEOUL_TZ = ZoneInfo('Asia/Seoul')
except ZoneInfoNotFoundError:
    SEOUL_TZ = timezone(timedelta(hours=9), name='Asia/Seoul')
PERIOD_KEY_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


class QuestionResponseLike(Protocol):
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


@dataclass(frozen=True)
class MbtiQuestionResponseItem:
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


@dataclass(frozen=True)
class MbtiMonthlyQuestionBatch:
    user_id: int
    period_key: str
    period_start: datetime
    period_end: datetime
    axis_responses: dict[str, list[MbtiQuestionResponseItem]]
    axis_counts: dict[str, int]
    total_count: int


def _coerce_to_timezone(value: datetime, tz: tzinfo) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def resolve_month_period(
    *,
    period_key: str | None = None,
    now: datetime | None = None,
    tz: tzinfo = SEOUL_TZ,
) -> tuple[str, datetime, datetime]:
    """Flow A: resolve the monthly analysis target period."""
    if period_key is None:
        current = _coerce_to_timezone(now or datetime.now(tz), tz)
        year = current.year
        month = current.month
    else:
        if PERIOD_KEY_PATTERN.match(period_key) is None:
            raise ValueError('period_key must use YYYY-MM format.')
        year_text, month_text = period_key.split('-', 1)
        year = int(year_text)
        month = int(month_text)

    resolved_key = f'{year:04d}-{month:02d}'
    period_start = datetime(year, month, 1, tzinfo=tz)

    if month == 12:
        period_end = datetime(year + 1, 1, 1, tzinfo=tz)
    else:
        period_end = datetime(year, month + 1, 1, tzinfo=tz)

    return resolved_key, period_start, period_end


def build_monthly_question_batch(
    *,
    user_id: int,
    period_key: str,
    period_start: datetime,
    period_end: datetime,
    responses: Iterable[QuestionResponseLike],
) -> MbtiMonthlyQuestionBatch:
    """Flow B core: group MBTI Q&A rows by IE/SN/TF/JP without requiring a DB."""
    axis_responses: dict[str, list[MbtiQuestionResponseItem]] = {
        axis: [] for axis in MBTI_AXES
    }

    for response in responses:
        if response.target_axis not in axis_responses:
            continue

        axis_responses[response.target_axis].append(
            MbtiQuestionResponseItem(
                id=response.id,
                question_text=response.question_text,
                answer_text=response.answer_text,
                target_axis=response.target_axis,
                answered_at=response.answered_at,
            )
        )

    for axis in MBTI_AXES:
        axis_responses[axis].sort(key=lambda item: (item.answered_at, item.id))

    axis_counts = {
        axis: len(axis_responses[axis])
        for axis in MBTI_AXES
    }

    return MbtiMonthlyQuestionBatch(
        user_id=user_id,
        period_key=period_key,
        period_start=period_start,
        period_end=period_end,
        axis_responses=axis_responses,
        axis_counts=axis_counts,
        total_count=sum(axis_counts.values()),
    )


def load_monthly_question_batch(
    *,
    user_id: int,
    period_key: str | None = None,
    now: datetime | None = None,
) -> MbtiMonthlyQuestionBatch:
    """Flow A->B ORM adapter: query mbti_question_responses and aggregate by axis."""
    from mbti.models import MbtiQuestionResponse

    resolved_key, period_start, period_end = resolve_month_period(
        period_key=period_key,
        now=now,
    )

    responses = (
        MbtiQuestionResponse.objects
        .filter(
            user_id=user_id,
            period_key=resolved_key,
            target_axis__in=MBTI_AXES,
        )
        .order_by('answered_at', 'id')
    )

    return build_monthly_question_batch(
        user_id=user_id,
        period_key=resolved_key,
        period_start=period_start,
        period_end=period_end,
        responses=responses,
    )

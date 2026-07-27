"""Canonical date-window and display helpers for report periods."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.utils import timezone

from mindreport.constants import (
    PERIOD_LABELS,
    PERIOD_MONTH,
    PERIOD_WEEK,
    SUPPORTED_PERIODS,
)


@dataclass(frozen=True)
class PeriodWindow:
    start: datetime
    end_exclusive: datetime

    @property
    def end_inclusive(self) -> datetime:
        return self.end_exclusive - timedelta(microseconds=1)


def resolve_period_window(
    *,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> PeriodWindow:
    if period_type not in SUPPORTED_PERIODS:
        raise ValueError(f'Unsupported mindreport period_type: {period_type}')

    today = timezone.localdate()
    if period_type == PERIOD_WEEK:
        resolved_date = target_date or today
        start_date = resolved_date - timedelta(days=resolved_date.weekday())
        start = datetime.combine(start_date, datetime.min.time())
        end = start + timedelta(days=7)
    else:
        resolved_year = year or today.year
        resolved_month = month or today.month
        start = datetime(resolved_year, resolved_month, 1)
        if resolved_month == 12:
            end = datetime(resolved_year + 1, 1, 1)
        else:
            end = datetime(resolved_year, resolved_month + 1, 1)

    return PeriodWindow(
        start=timezone.make_aware(start),
        end_exclusive=timezone.make_aware(end),
    )


def period_label(period_type: str, explicit_name: str = '') -> str:
    return explicit_name or PERIOD_LABELS.get(period_type, PERIOD_LABELS[PERIOD_WEEK])


def period_range_text(
    *,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> str:
    window = resolve_period_window(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    local_start = timezone.localtime(window.start).date()
    local_end = timezone.localtime(window.end_inclusive).date()
    if period_type == PERIOD_MONTH:
        return f'{local_start.year}.{local_start.month:02d} 월간 결산'
    return f'{local_start:%Y.%m.%d} ~ {local_end:%Y.%m.%d}'


def suggestion_time_context(
    *,
    period_type: str,
    generated_on: date,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, str | int]:
    """Return generation-anchored timing guidance without persisting new data."""
    window = resolve_period_window(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    analysis_start = timezone.localtime(window.start).date()
    analysis_end = min(timezone.localtime(window.end_inclusive).date(), generated_on)
    duration_days = 28 if period_type == PERIOD_MONTH else 7
    action_end = generated_on + timedelta(days=duration_days - 1)
    return {
        'period_type': period_type,
        'analysis_period_start': analysis_start.isoformat(),
        'analysis_period_end': analysis_end.isoformat(),
        'generated_on': generated_on.isoformat(),
        'action_window_start': generated_on.isoformat(),
        'action_window_end': action_end.isoformat(),
        'action_window_days': duration_days,
        'action_window_label': (
            '리포트 생성 후 4주'
            if period_type == PERIOD_MONTH
            else '리포트 생성 후 7일'
        ),
    }


def is_last_week_of_month(target_date: date) -> bool:
    days_to_sunday = 6 - target_date.weekday()
    sunday_date = target_date + timedelta(days=days_to_sunday)
    _, last_day = calendar.monthrange(target_date.year, target_date.month)
    return sunday_date.month != target_date.month or sunday_date.day == last_day


def last_completed_week_target_date(reference_date: date | None = None) -> date:
    """Return a date inside the most recently completed Monday-Sunday week."""
    resolved_date = reference_date or timezone.localdate()
    current_week_start = resolved_date - timedelta(days=resolved_date.weekday())
    return current_week_start - timedelta(days=1)


def last_completed_month(reference_date: date | None = None) -> tuple[int, int]:
    """Return the year and month immediately preceding the reference date."""
    resolved_date = reference_date or timezone.localdate()
    previous_month_end = resolved_date.replace(day=1) - timedelta(days=1)
    return previous_month_end.year, previous_month_end.month

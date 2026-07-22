from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone


def previous_period_key(reference=None) -> str:
    local_reference = timezone.localtime(reference or timezone.now())
    first_of_month = local_reference.replace(day=1)
    previous_month = first_of_month - timedelta(days=1)
    return previous_month.strftime('%Y-%m')


def next_monthly_run(reference=None, *, hour: int = 0, minute: int = 5):
    local_reference = timezone.localtime(reference or timezone.now())
    candidate = local_reference.replace(
        day=1,
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if candidate <= local_reference:
        if local_reference.month == 12:
            candidate = candidate.replace(year=local_reference.year + 1, month=1)
        else:
            candidate = candidate.replace(month=local_reference.month + 1)
    return candidate


def seconds_until(target: datetime, reference=None) -> float:
    current = timezone.localtime(reference or timezone.now())
    return max(0.0, (target - current).total_seconds())

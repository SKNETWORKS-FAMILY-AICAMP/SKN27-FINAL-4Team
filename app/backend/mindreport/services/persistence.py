"""Persistence boundary for generated mind reports."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from mindreport.constants import PERIOD_MONTH
from mindreport.models import MindReport
from mindreport.services.payloads import serialize_report
from mindreport.services.periods import period_label, resolve_period_window


def list_latest_period_reports(user) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    seen_periods: set[tuple[Any, ...]] = set()
    monthly_label = period_label(PERIOD_MONTH)

    for report in MindReport.objects.filter(user=user):
        created_date = timezone.localtime(report.created_at).date()
        if report.report_type.startswith(monthly_label):
            period_key = (PERIOD_MONTH, created_date.year, created_date.month)
        else:
            week_start = created_date - timedelta(days=created_date.weekday())
            period_key = ('week', week_start)
        if period_key in seen_periods:
            continue
        seen_periods.add(period_key)
        reports.append(serialize_report(report))
    return reports


def period_report_exists(
    *,
    user,
    period_type: str,
    period_name: str,
    target_date=None,
    year: int | None = None,
    month: int | None = None,
) -> bool:
    """Return whether the user already has a report for the resolved period."""
    window = resolve_period_window(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    return MindReport.objects.filter(
        user=user,
        report_type__startswith=period_name,
        created_at__gte=window.start,
        created_at__lt=window.end_exclusive,
    ).exists()


def save_period_report(
    *,
    user,
    payload: dict[str, Any],
    period_type: str,
    period_name: str,
    target_date=None,
    year: int | None = None,
    month: int | None = None,
) -> MindReport:
    defaults = {
        'report_type': payload['type'],
        'range_text': payload['range'],
        'title': payload['title'],
        'summary': payload['summary'],
        'stress_causes': payload['stressCauses'],
        'relief_causes': payload['reliefCauses'],
        'cause_labels': payload['causeLabels'],
        'emotions': payload['emotions'],
        'analysis': payload['analysis'],
        'recommendations': payload['recommendations'],
        'is_fallback': payload['is_fallback'],
        'is_safety_response': payload['is_safety_response'],
    }
    window = resolve_period_window(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    period_reports = MindReport.objects.filter(
        user=user,
        report_type__startswith=period_name,
        created_at__gte=window.start,
        created_at__lt=window.end_exclusive,
    )

    with transaction.atomic():
        report = period_reports.select_for_update().first()
        if report is None:
            return MindReport.objects.create(user=user, **defaults)
        for field, value in defaults.items():
            setattr(report, field, value)
        report.save(update_fields=list(defaults))
        period_reports.exclude(pk=report.pk).delete()
        return report

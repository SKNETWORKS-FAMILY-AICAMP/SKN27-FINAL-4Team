"""Persistence boundary for generated mind reports."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from mindreport.constants import PERIOD_MONTH
from mindreport.models import MindReport
from mindreport.services.payloads import serialize_report
from mindreport.services.periods import period_label, period_range_text


def list_latest_period_reports(user) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    seen_periods: set[tuple[Any, ...]] = set()
    monthly_label = period_label(PERIOD_MONTH)

    # Prioritize real non-fallback reports (is_fallback=False) over dummy fallback reports for the same period
    queryset = MindReport.objects.filter(user=user).order_by('is_fallback', '-created_at')

    for report in queryset:
        period_type = PERIOD_MONTH if report.report_type.startswith(monthly_label) else 'week'
        period_key = (period_type, report.range_text)
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
    """Return whether the user already has a valid non-expired report for the resolved period."""
    expected_range = period_range_text(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    report = MindReport.objects.filter(
        user=user,
        report_type__startswith=period_name,
        range_text=expected_range,
    ).first()

    if report is None:
        return False

    # Safety responses expire after 24 hours (1 day), requiring regeneration
    if report.is_safety_response and (timezone.now() - report.created_at >= timedelta(hours=24)):
        return False

    return True


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
    expected_range = period_range_text(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    payload_type = str(payload['type'])
    if not payload_type.startswith(period_name):
        payload_type = (
            f'{period_name} (데이터 부족)'
            if payload.get('is_fallback')
            else period_name
        )
    defaults = {
        'report_type': payload_type,
        'range_text': expected_range,
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
    period_reports = MindReport.objects.filter(
        user=user,
        report_type__startswith=period_name,
        range_text=expected_range,
    )

    with transaction.atomic():
        report = period_reports.select_for_update().first()
        if report is None:
            return MindReport.objects.create(user=user, **defaults)
        for field, value in defaults.items():
            setattr(report, field, value)
        # A refreshed report starts a new suggestion window. Reuse the existing
        # timestamp as its latest generation time instead of adding a DB field.
        report.created_at = timezone.now()
        report.save(update_fields=[*defaults, 'created_at'])
        period_reports.exclude(pk=report.pk).delete()
        return report

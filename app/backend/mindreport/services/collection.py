from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.utils import timezone

from chat.models import ChatMessage
from mindreport.services.criteria_service import ReportCriteriaService
from mindreport.services.scoring import PERIOD_MONTH, PERIOD_WEEK, SUPPORTED_PERIODS, ReportSourceMessage


@dataclass(frozen=True)
class MindReportCollectionResult:
    status: str
    period_type: str
    eligibility: dict[str, Any]
    source_messages: tuple[ReportSourceMessage, ...]
    message: str


def _week_range(target_date: date) -> tuple[datetime, datetime]:
    start_date = target_date - timedelta(days=target_date.weekday())
    end_date = start_date + timedelta(days=6)
    return (
        timezone.make_aware(datetime.combine(start_date, datetime.min.time())),
        timezone.make_aware(datetime.combine(end_date, datetime.max.time())),
    )


def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    start = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1)) - timedelta(microseconds=1)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1)) - timedelta(microseconds=1)
    return start, end


def collect_source_messages(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> tuple[ReportSourceMessage, ...]:
    if period_type == PERIOD_WEEK:
        start, end = _week_range(target_date or timezone.now().date())
    elif period_type == PERIOD_MONTH:
        now = timezone.now()
        resolved_year = year or now.year
        resolved_month = month or now.month
        start, end = _month_range(resolved_year, resolved_month)
    else:
        raise ValueError(f'Unsupported mindreport period_type: {period_type}')

    queryset = ChatMessage.objects.filter(
        session__user=user,
        role='user',
        created_at__gte=start,
        created_at__lte=end,
    )
    return tuple(
        ReportSourceMessage(
            message_id=message.id,
            source_date=timezone.localtime(message.created_at).date(),
            content=message.content,
            emotion_label=message.emotion_label,
        )
        for message in queryset.order_by('created_at', 'id')
    )


def check_generation_criteria(
    *,
    user,
    period_type: str,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    if period_type == PERIOD_WEEK:
        return ReportCriteriaService.check_weekly_report_eligibility(
            user,
            target_date=target_date,
        )
    if period_type == PERIOD_MONTH:
        return ReportCriteriaService.check_monthly_report_eligibility(
            user,
            year=year,
            month=month,
        )
    raise ValueError(f'Unsupported mindreport period_type: {period_type}')


class MindReportDataCollector:
    def run(
        self,
        *,
        user,
        period_type: str,
        target_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> MindReportCollectionResult:
        if period_type not in SUPPORTED_PERIODS:
            raise ValueError(f'Unsupported mindreport period_type: {period_type}')

        source_messages = collect_source_messages(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        eligibility = check_generation_criteria(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )

        if not eligibility['is_eligible']:
            return MindReportCollectionResult(
                status='insufficient_data',
                period_type=period_type,
                eligibility=eligibility,
                source_messages=source_messages,
                message='리포트 생성 기준을 충족하지 않았습니다.',
            )

        return MindReportCollectionResult(
            status='eligible',
            period_type=period_type,
            eligibility=eligibility,
            source_messages=source_messages,
            message='리포트 생성 기준을 충족했습니다.',
        )

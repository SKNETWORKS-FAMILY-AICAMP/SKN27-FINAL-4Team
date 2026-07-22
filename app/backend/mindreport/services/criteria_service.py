"""Generation eligibility policy for weekly and monthly mind reports."""

from __future__ import annotations

from chat.models import ChatMessage
from mindreport.constants import (
    PERIOD_MONTH,
    PERIOD_WEEK,
    REPORT_REQUIRED_MESSAGE_COUNTS,
)
from mindreport.services.periods import resolve_period_window


class ReportCriteriaService:
    @staticmethod
    def get_chat_count(
        user,
        *,
        period_type: str,
        target_date=None,
        year: int | None = None,
        month: int | None = None,
    ) -> int:
        window = resolve_period_window(
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        return ChatMessage.objects.filter(
            session__user=user,
            role='user',
            created_at__gte=window.start,
            created_at__lt=window.end_exclusive,
        ).count()

    @classmethod
    def check_report_eligibility(
        cls,
        user,
        *,
        period_type: str,
        target_date=None,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, int | bool]:
        current_count = cls.get_chat_count(
            user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        required_count = REPORT_REQUIRED_MESSAGE_COUNTS[period_type]
        return {
            'is_eligible': current_count >= required_count,
            'current_count': current_count,
            'required_count': required_count,
            'missing_count': max(0, required_count - current_count),
        }

    @classmethod
    def get_weekly_chat_count(cls, user, target_date=None):
        return cls.get_chat_count(
            user,
            period_type=PERIOD_WEEK,
            target_date=target_date,
        )

    @classmethod
    def get_monthly_chat_count(cls, user, year=None, month=None):
        return cls.get_chat_count(
            user,
            period_type=PERIOD_MONTH,
            year=year,
            month=month,
        )

    @classmethod
    def check_weekly_report_eligibility(cls, user, target_date=None):
        return cls.check_report_eligibility(
            user,
            period_type=PERIOD_WEEK,
            target_date=target_date,
        )

    @classmethod
    def check_monthly_report_eligibility(cls, user, year=None, month=None):
        return cls.check_report_eligibility(
            user,
            period_type=PERIOD_MONTH,
            year=year,
            month=month,
        )

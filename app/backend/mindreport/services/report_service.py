"""Application service coordinating graph generation and persistence."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Callable

from mindreport.constants import PERIOD_LABELS, PERIOD_MONTH, PERIOD_WEEK
from mindreport.exceptions import MindReportError, MindReportGenerationError
from mindreport.services.graph_flow import MindReportSupervisorAgent
from mindreport.services.payloads import payload_from_graph_state, serialize_report
from mindreport.services.persistence import (
    list_latest_period_reports,
    period_report_exists,
    save_period_report,
)


logger = logging.getLogger(__name__)


class MindReportService:
    def __init__(
        self,
        supervisor_factory: Callable[[], MindReportSupervisorAgent] = (
            MindReportSupervisorAgent
        ),
    ):
        self.supervisor_factory = supervisor_factory

    def list_reports(self, *, user) -> list[dict[str, Any]]:
        return list_latest_period_reports(user)

    def load_reports(
        self,
        *,
        user,
        target_date: date,
        include_monthly: bool,
    ) -> list[dict[str, Any]]:
        """Load reports and automatically catch up a missing scheduled period."""
        self.ensure_period_report(
            user=user,
            period_type=PERIOD_WEEK,
            period_name=PERIOD_LABELS[PERIOD_WEEK],
            target_date=target_date,
        )
        if include_monthly:
            self.ensure_period_report(
                user=user,
                period_type=PERIOD_MONTH,
                period_name=PERIOD_LABELS[PERIOD_MONTH],
                year=target_date.year,
                month=target_date.month,
            )
        return self.list_reports(user=user)

    def ensure_period_report(
        self,
        *,
        user,
        period_type: str,
        period_name: str,
        target_date=None,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any] | None:
        if period_report_exists(
            user=user,
            period_type=period_type,
            period_name=period_name,
            target_date=target_date,
            year=year,
            month=month,
        ):
            return None

        # The supervisor owns the eligibility decision. A missing scheduled
        # period must run through the same graph so eligible users receive the
        # full report and ineligible users receive the normal fallback.
        return self.generate_period(
            user=user,
            period_type=period_type,
            period_name=period_name,
            target_date=target_date,
            year=year,
            month=month,
        )

    def refresh_reports(
        self,
        *,
        user,
        target_date: date,
        include_monthly: bool,
    ) -> list[dict[str, Any]]:
        self.generate_period(
            user=user,
            period_type=PERIOD_WEEK,
            period_name=PERIOD_LABELS[PERIOD_WEEK],
            target_date=target_date,
        )
        if include_monthly:
            self.generate_period(
                user=user,
                period_type=PERIOD_MONTH,
                period_name=PERIOD_LABELS[PERIOD_MONTH],
                year=target_date.year,
                month=target_date.month,
            )
        return self.list_reports(user=user)

    def generate_period(
        self,
        *,
        user,
        period_type: str,
        period_name: str,
        target_date=None,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any]:
        try:
            state = self.supervisor_factory().run(
                user=user,
                period_type=period_type,
                period_name=period_name,
                target_date=target_date,
                year=year,
                month=month,
            )
            keyword_result = state.get('keyword_result')
            cause_result = state.get('cause_result')
            cause_keywords = tuple(
                getattr(cause_result, 'cause_keywords', ()) or ()
            )
            logger.info(
                (
                    'Mind report cause outcome user=%s period=%s '
                    'keyword_status=%s cause_status=%s '
                    'stress_count=%s relief_count=%s unresolved_count=%s'
                ),
                user.pk,
                period_type,
                getattr(keyword_result, 'status', None),
                getattr(cause_result, 'status', None),
                sum(item.cause_type == 'stress' for item in cause_keywords),
                sum(item.cause_type == 'relief' for item in cause_keywords),
                len(getattr(cause_result, 'unresolved_candidates', ()) or ()),
            )
            payload = payload_from_graph_state(state)
            report = save_period_report(
                user=user,
                payload=payload,
                period_type=period_type,
                period_name=period_name,
                target_date=target_date,
                year=year,
                month=month,
            )
            return serialize_report(report)
        except MindReportError:
            raise
        except Exception as exc:
            logger.exception(
                'Mind report generation failed for user=%s period=%s.',
                user.pk,
                period_type,
            )
            raise MindReportGenerationError(
                '마음 리포트를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.'
            ) from exc

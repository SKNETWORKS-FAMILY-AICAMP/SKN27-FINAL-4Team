from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from mindreport.models import MindReport
from mindreport.services.graph_flow import MindReportSupervisorAgent


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class MindReportGenerateAPIView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get(self, request):
        user = self._resolve_user(request)
        if not user:
            return Response({'error': 'DB에 사용자가 없습니다.'}, status=401)

        return Response({
            'status': 'success',
            'message': '저장된 마음 리포트를 불러왔습니다.',
            'reports': self._stored_reports(user),
        })

    def post(self, request):
        user = self._resolve_user(request)
        if not user:
            return Response({'error': 'DB에 사용자가 없습니다.'}, status=401)

        now = timezone.now()
        target_date = now.date()
        self._generate_period_report(
            user=user,
            period_type='week',
            period_name='주간',
            target_date=target_date,
        )

        if self._is_last_week_of_month(target_date):
            self._generate_period_report(
                user=user,
                period_type='month',
                period_name='월간',
                year=target_date.year,
                month=target_date.month,
            )

        return Response({
            'status': 'success',
            'message': '최신 대화로 마음 리포트를 갱신했습니다.',
            'reports': self._stored_reports(user),
        })

    def _generate_period_report(
        self,
        *,
        user,
        period_type: str,
        period_name: str,
        target_date=None,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any]:
        state = MindReportSupervisorAgent().run(
            user=user,
            period_type=period_type,
            period_name=period_name,
            target_date=target_date,
            year=year,
            month=month,
        )
        report_data = self._payload_from_graph_state(state)
        defaults = {
            'report_type': report_data['type'],
            'range_text': report_data['range'],
            'title': report_data['title'],
            'summary': report_data['summary'],
            'stress_causes': report_data.get('stressCauses', []),
            'relief_causes': report_data.get('reliefCauses', []),
            'emotions': report_data.get('emotions', []),
            'analysis': report_data.get('analysis', []),
            'recommendations': report_data.get('recommendations', []),
            'is_fallback': report_data.get('is_fallback', False),
            'is_safety_response': report_data.get('is_safety_response', False),
        }

        period_reports = self._current_period_reports(
            user=user,
            period_type=period_type,
            period_name=period_name,
            target_date=target_date,
            year=year,
            month=month,
        )
        with transaction.atomic():
            report = period_reports.first()
            if report:
                for field, value in defaults.items():
                    setattr(report, field, value)
                report.save(update_fields=list(defaults))
                period_reports.exclude(pk=report.pk).delete()
            else:
                report = MindReport.objects.create(user=user, **defaults)

        return self._serialize_report(report)

    @staticmethod
    def _resolve_user(request):
        if request.user.is_authenticated:
            return request.user
        return get_user_model().objects.first()

    @classmethod
    def _stored_reports(cls, user) -> list[dict[str, Any]]:
        reports = []
        seen_periods = set()
        for report in MindReport.objects.filter(user=user):
            created_date = timezone.localtime(report.created_at).date()
            if report.report_type.startswith('월간'):
                period_key = ('month', created_date.year, created_date.month)
            else:
                week_start = created_date - timedelta(days=created_date.weekday())
                period_key = ('week', week_start)
            if period_key in seen_periods:
                continue
            seen_periods.add(period_key)
            reports.append(cls._serialize_report(report))
        return reports

    @staticmethod
    def _serialize_report(report: MindReport) -> dict[str, Any]:
        prefix = 'monthly' if report.report_type.startswith('월간') else 'weekly'
        if report.is_safety_response:
            prefix = f'safety-{prefix}'
        elif report.is_fallback:
            prefix = f'fallback-{prefix}'
        return {
            'id': f'{prefix}-{report.id}',
            'type': report.report_type,
            'range': report.range_text,
            'title': report.title,
            'summary': report.summary,
            'stressCauses': list(report.stress_causes),
            'reliefCauses': list(report.relief_causes),
            'emotions': list(report.emotions),
            'analysis': list(report.analysis),
            'recommendations': list(report.recommendations),
            'is_fallback': report.is_fallback,
            'is_safety_response': report.is_safety_response,
        }

    @staticmethod
    def _current_period_reports(
        *,
        user,
        period_type: str,
        period_name: str,
        target_date=None,
        year: int | None = None,
        month: int | None = None,
    ):
        if period_type == 'month':
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
        else:
            start_date = target_date - timedelta(days=target_date.weekday())
            start = datetime.combine(start_date, datetime.min.time())
            end = start + timedelta(days=7)

        start = timezone.make_aware(start)
        end = timezone.make_aware(end)
        return MindReport.objects.filter(
            user=user,
            report_type__startswith=period_name,
            created_at__gte=start,
            created_at__lt=end,
        )

    @staticmethod
    def _payload_from_graph_state(state) -> dict[str, Any]:
        if state.get('status') in {'completed', 'safety_ready'}:
            payload = state.get('report_payload')
        elif state.get('status') == 'fallback_ready':
            payload = state.get('fallback_payload')
        else:
            payload = None

        if not payload:
            raise RuntimeError(
                f"Mind report graph ended without a frontend payload: {state.get('status')}"
            )

        return {
            **payload,
            'stressCauses': list(payload.get('stressCauses', [])),
            'reliefCauses': list(payload.get('reliefCauses', [])),
            'emotions': list(payload.get('emotions', [])),
            'analysis': list(payload.get('analysis', [])),
            'recommendations': list(payload.get('recommendations', [])),
            'is_fallback': bool(payload.get('is_fallback', False)),
            'is_safety_response': bool(payload.get('is_safety_response', False)),
        }

    @staticmethod
    def _is_last_week_of_month(target_date) -> bool:
        days_to_sunday = 6 - target_date.weekday()
        sunday_date = target_date + timedelta(days=days_to_sunday)
        _, last_day = calendar.monthrange(target_date.year, target_date.month)
        return sunday_date.month != target_date.month or sunday_date.day == last_day

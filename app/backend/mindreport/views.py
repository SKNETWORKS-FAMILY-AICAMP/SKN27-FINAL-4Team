from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mindreport.exceptions import MindReportError
from mindreport.services.graph_flow import MindReportSupervisorAgent
from mindreport.services.periods import is_last_week_of_month
from mindreport.services.report_service import MindReportService
from user.views import CsrfExemptSessionAuthentication


class MindReportGenerateAPIView(APIView):
    """Read scheduled reports and optionally check the latest data immediately."""

    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_date = timezone.localdate()
        try:
            reports = self._service().load_reports(
                user=request.user,
                target_date=target_date,
                include_monthly=self._is_last_week_of_month(target_date),
            )
        except MindReportError as exc:
            response_status = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if exc.retryable
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(
                {'status': 'error', 'code': exc.code, 'message': str(exc)},
                status=response_status,
            )
        return Response({
            'status': 'success',
            'message': '정기 주간·월간 마음 리포트를 불러왔습니다.',
            'reports': reports,
        })

    def post(self, request):
        target_date = timezone.localdate()
        try:
            reports = self._service().refresh_reports(
                user=request.user,
                target_date=target_date,
                include_monthly=self._is_last_week_of_month(target_date),
            )
        except MindReportError as exc:
            response_status = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if exc.retryable
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(
                {'status': 'error', 'code': exc.code, 'message': str(exc)},
                status=response_status,
            )
        return Response({
            'status': 'success',
            'message': '다음 정기 갱신을 기다리지 않고 최신 대화를 반영했어요.',
            'reports': reports,
        })

    @staticmethod
    def _service() -> MindReportService:
        # Resolve at call time so tests and alternative runtimes can inject the agent.
        return MindReportService(supervisor_factory=MindReportSupervisorAgent)

    @staticmethod
    def _is_last_week_of_month(target_date) -> bool:
        return is_last_week_of_month(target_date)

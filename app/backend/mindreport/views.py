"""
기능: 프론트엔드(Vue)에서 마음 리포트와 관련된 API 요청(예: 리포트 보관함 조회, 리포트 생성 등)을 보냈을 때, 이를 처리하고 응답(JSON)을 반환하는 컨트롤러 역할을 하는 파일입니다.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .services.criteria_service import ReportCriteriaService
from .services.fallback_service import FallbackReportService
from .services.flow import MindReportFlowService, format_for_frontend

class MindReportGenerateAPIView(APIView):
    # 실제 연동 시에는 인증된 사용자만 접근 가능하도록 주석 해제 (테스트를 위해 잠시 주석 처리 가능)
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        마음 리포트 생성 기준을 확인하고, 결과에 따라 정식 리포트 또는 데이터 부족 보완 리포트를 반환합니다.
        월말(마지막 주)일 경우 주간과 월간 리포트를 동시에 반환합니다.
        """
        user = request.user
        if not user.is_authenticated:
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.first()
            if not user:
                return Response({"error": "DB에 유저가 없습니다."}, status=401)
            
        import calendar
        from datetime import timedelta
        
        now = timezone.now()
        target_date = now.date()
        
        # 이번 주가 월의 마지막 주인지 확인 (일요일이 다음 달로 넘어가거나, 오늘이 말일과 가까운지)
        # 이번 주 일요일 계산
        days_to_sunday = 6 - target_date.weekday()
        sunday_date = target_date + timedelta(days=days_to_sunday)
        
        # 일요일의 월이 현재 월과 다르거나, 현재 월의 마지막 날짜인 경우 마지막 주로 간주
        _, last_day_of_month = calendar.monthrange(target_date.year, target_date.month)
        is_last_week = (sunday_date.month != target_date.month) or (sunday_date.day == last_day_of_month)
        
        from .models import MindReport
        
        generated_reports = []
        
        # ==========================================
        # 1. 주간 리포트 처리
        # ==========================================
        weekly_criteria = ReportCriteriaService.check_weekly_report_eligibility(user)
        if not weekly_criteria["is_eligible"]:
            fallback_report = MindReport.objects.filter(user=user, is_fallback=True, report_type__contains="주간").order_by('-created_at').first()
            if not fallback_report:
                fallback_report = FallbackReportService.generate_and_save_fallback_report(
                    user=user, 
                    report_type="주간", 
                    range_text=timezone.now().strftime("%Y.%m.%d") + " 생성"
                )
                
            generated_reports.append({
                "id": f"fallback-{fallback_report.id}",
                "type": fallback_report.report_type,
                "range": fallback_report.range_text,
                "title": fallback_report.title,
                "summary": fallback_report.summary,
                "stressCauses": fallback_report.stress_causes,
                "reliefCauses": fallback_report.relief_causes,
                "emotions": fallback_report.emotions,
                "analysis": fallback_report.analysis,
                "recommendations": fallback_report.recommendations,
                "is_fallback": fallback_report.is_fallback
            })
        else:
            MindReport.objects.filter(user=user, is_fallback=True, report_type__contains="주간").delete()
            
            # --- 정식 파이프라인(대화수 충족 로직) 가동 ---
            flow_service = MindReportFlowService()
            flow_result = flow_service.run(user=user, period_type="week")
            report_data = format_for_frontend(flow_result=flow_result, user_id=user.id, period_name="주간")
            
            final_report = MindReport.objects.create(
                user=user,
                report_type=report_data["type"],
                range_text=report_data["range"],
                title=report_data["title"],
                summary=report_data["summary"],
                stress_causes=report_data["stressCauses"],
                relief_causes=report_data["reliefCauses"],
                emotions=report_data["emotions"],
                analysis=report_data["analysis"],
                recommendations=report_data.get("recommendations", []),
                is_fallback=False
            )
            report_data["id"] = f"weekly-{final_report.id}"
            generated_reports.append(report_data)

        # ==========================================
        # 2. 월간 리포트 처리 (마지막 주일 경우에만)
        # ==========================================
        if is_last_week:
            monthly_criteria = ReportCriteriaService.check_monthly_report_eligibility(user)
            if not monthly_criteria["is_eligible"]:
                m_fallback = MindReport.objects.filter(user=user, is_fallback=True, report_type__contains="월간").order_by('-created_at').first()
                if not m_fallback:
                    m_fallback = FallbackReportService.generate_and_save_fallback_report(
                        user=user, 
                        report_type="월간", 
                        range_text=timezone.now().strftime("%Y.%m") + " 월간 결산"
                    )
                
                generated_reports.append({
                    "id": f"fallback-m-{m_fallback.id}",
                    "type": m_fallback.report_type,
                    "range": m_fallback.range_text,
                    "title": m_fallback.title,
                    "summary": m_fallback.summary,
                    "stressCauses": m_fallback.stress_causes,
                    "reliefCauses": m_fallback.relief_causes,
                    "emotions": m_fallback.emotions,
                    "analysis": m_fallback.analysis,
                    "recommendations": m_fallback.recommendations,
                    "is_fallback": m_fallback.is_fallback
                })
            else:
                MindReport.objects.filter(user=user, is_fallback=True, report_type__contains="월간").delete()
                
                # --- 정식 파이프라인(대화수 충족 로직) 가동 ---
                flow_service = MindReportFlowService()
                flow_result = flow_service.run(user=user, period_type="month")
                report_data = format_for_frontend(flow_result=flow_result, user_id=user.id, period_name="월간")
                
                final_report = MindReport.objects.create(
                    user=user,
                    report_type=report_data["type"],
                    range_text=report_data["range"],
                    title=report_data["title"],
                    summary=report_data["summary"],
                    stress_causes=report_data["stressCauses"],
                    relief_causes=report_data["reliefCauses"],
                    emotions=report_data["emotions"],
                    analysis=report_data["analysis"],
                    recommendations=report_data.get("recommendations", []),
                    is_fallback=False
                )
                report_data["id"] = f"monthly-{final_report.id}"
                generated_reports.append(report_data)

        return Response({
            "status": "success", 
            "message": "리포트 생성이 완료되었습니다.",
            "reports": generated_reports
        })


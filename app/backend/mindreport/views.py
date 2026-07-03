"""
기능: 프론트엔드(Vue)에서 마음 리포트와 관련된 API 요청(예: 리포트 보관함 조회, 리포트 생성 등)을 보냈을 때, 이를 처리하고 응답(JSON)을 반환하는 컨트롤러 역할을 하는 파일입니다.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .services.criteria_service import ReportCriteriaService
from .services.fallback_service import FallbackReportService

class MindReportGenerateAPIView(APIView):
    # 실제 연동 시에는 인증된 사용자만 접근 가능하도록 주석 해제 (테스트를 위해 잠시 주석 처리 가능)
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        마음 리포트 생성 기준을 확인하고, 결과에 따라 정식 리포트 또는 데이터 부족 보완 리포트를 반환합니다.
        """
        # 임시 유저 처리 (인증 설정 전 테스트용)
        user = request.user
        if not user.is_authenticated:
            # 로그인하지 않은 상태면 가짜 유저 데이터로 에러 방지 (실제 서비스에선 에러 리턴)
            return Response({"error": "로그인이 필요합니다."}, status=401)
            
        # 1. 생성 기준 확인 (현재 주간 기준으로 테스트)
        criteria_result = ReportCriteriaService.check_weekly_report_eligibility(user)
        
        # 2. 기준 미달 시 Fallback 리포트 생성 및 반환
        if not criteria_result["is_eligible"]:
            fallback_data = FallbackReportService.generate_fallback_report(
                user=user, 
                report_type="주간", 
                range_text=timezone.now().strftime("%Y.%m.%d") + " 생성"
            )
            return Response({
                "status": "fallback", 
                "message": "데이터가 부족하여 보완 정책이 실행되었습니다.",
                "criteria": criteria_result,
                "report": fallback_data
            })
            
        # 3. 기준 충족 시 정식 리포트 생성 (추후 ai 폴더의 모델과 연결할 부분)
        # 현재는 통과했다는 Mock 데이터를 보냅니다.
        standard_data = {
            "id": f"weekly-{user.id}-{timezone.now().timestamp()}",
            "type": "주간",
            "range": timezone.now().strftime("%Y.%m.%d") + " 생성",
            "title": f"정식 마음 리포트 생성 완료",
            "summary": "충분한 대화가 모여 리포트가 정상적으로 분석되었습니다.",
            "stressCauses": ["업무", "피로"],
            "reliefCauses": ["휴식"],
            "emotions": [{"day": "오늘", "icon": "😄"}],
            "analysis": [
                "대화 기준(5개 이상)을 충족하여 정상적인 분석을 완료했습니다.",
                "다음 주 AI 모델이 연동되면 실제 분석 데이터가 이곳에 표시됩니다."
            ],
            "is_fallback": False
        }
        
        return Response({
            "status": "success", 
            "message": "리포트 생성이 완료되었습니다.",
            "criteria": criteria_result,
            "report": standard_data
        })


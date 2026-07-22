"""
기능: 설정된 최소 대화 수에 미달할 때 대체(Fallback) 리포트를 생성합니다.
"""
import logging
import sys

from django.conf import settings


logger = logging.getLogger(__name__)

# ai 폴더를 import 할 수 있도록 PYTHONPATH 경로 임시 추가
if str(settings.PROJECT_ROOT) not in sys.path:
    sys.path.append(str(settings.PROJECT_ROOT))

from ai.agents.web_agent import FallbackWebAgent
from mindreport.services.payloads import report_recipient_name

class FallbackReportService:
    @staticmethod
    def generate_fallback_report(user, report_type="주간", range_text="이번 주"):
        """
        사용자 정보와 Tavily 근거 기반 Web Agent를 사용하여 데이터 부족 안내를 생성합니다.
        """
        # 1. 사용자 프로필 정보 조회
        age = None
        gender = None
        hobbies = []
        interests = []
        
        # profile이 존재하지 않을 수도 있으므로 예외 처리
        try:
            profile = user.profile
            age = profile.age
            gender = profile.gender
            hobbies = profile.hobbies
            interests = profile.interests
        except Exception:
            pass
            
        # 2. MBTI 정보 조회 (월간 리포트인 경우 등)
        user_mbti = None
        if "월간" in report_type:
            try:
                from mbti.models import MbtiOnboardingProfile
                mbti_profile = MbtiOnboardingProfile.objects.filter(user_id=user.id).first()
                if mbti_profile and mbti_profile.mbti_type:
                    user_mbti = mbti_profile.mbti_type
            except Exception:
                logger.exception('Failed to load MBTI context for mind-report fallback.')
                
        # 3. Web Agent로 트렌디한 콘텐츠/활동 추천 받기
        recommendations = FallbackWebAgent.get_trendy_contents(
            age=age, 
            gender=gender, 
            hobbies=hobbies, 
            interests=interests,
            mbti=user_mbti
        )
        
        # 4. 프론트엔드 ReportView.vue 구조에 맞게 JSON(Dict) 조립
        analysis_lines = []
        
        recommendations_names = []
        if recommendations:
            analysis_lines.append(
                "아래 활동은 대화에서 분석한 결과가 아니라, 기다리는 동안 참고할 수 있도록 Tavily 웹 검색 결과를 바탕으로 정리한 제안이에요."
            )
        else:
            analysis_lines.append(
                "현재는 근거를 확인할 수 있는 웹 추천을 준비하지 못했어요. 임의의 활동을 대신 표시하지 않고 대화 기록을 계속 수집할게요."
            )

        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            act = str(rec.get("activity") or "").strip()
            if not act:
                continue
            reason = str(rec.get("reason") or "").strip()
            how_to = str(rec.get("how_to") or "").strip()

            analysis_lines.append(f"✅ {act}")
            if reason:
                analysis_lines.append(f"  - 왜 추천하나요?: {reason}")
            if how_to:
                analysis_lines.append(f"  - 어떻게 시작할까요?: {how_to}")
            recommendations_names.append(act)

        analysis_lines.append(
            f"기록이 아직 적어도, {report_recipient_name(user)}은 마음을 천천히 알아갈 충분한 시간이 있어요."
        )
                
        report_data = {
            "id": f"fallback-{user.id}",
            "type": f"{report_type} (데이터 부족)",
            "range": range_text,
            "title": f"마음 리포트 분석 대기 중",
            "summary": "아직 대화 기록이 조금 부족해요. 기록이 더 모이면 실제 대화를 바탕으로 마음의 흐름을 살펴볼게요.",
            "stressCauses": [],
            "reliefCauses": [],
            "emotions": [], # 데이터가 없으므로 비움
            "analysis": analysis_lines,
            "recommendations": recommendations_names,
            "is_fallback": True
        }
        
        return report_data

    @staticmethod
    def generate_and_save_fallback_report(user, report_type="주간", range_text=None):
        """
        기존 대체 리포트가 있으면 삭제하고 새로 생성하여 DB에 저장합니다.
        """
        from django.utils import timezone
        from mindreport.models import MindReport
        
        if range_text is None:
            range_text = timezone.now().strftime("%Y.%m.%d") + " 생성"
            
        # 기존 폴백 리포트 삭제
        MindReport.objects.filter(user=user, is_fallback=True).delete()
        
        # 새 리포트 데이터 생성
        report_data = FallbackReportService.generate_fallback_report(user, report_type, range_text)
        
        # DB에 저장
        report = MindReport.objects.create(
            user=user,
            report_type=report_data["type"],
            range_text=report_data["range"],
            title=report_data["title"],
            summary=report_data["summary"],
            stress_causes=report_data["stressCauses"],
            relief_causes=report_data["reliefCauses"],
            emotions=report_data["emotions"],
            analysis=report_data["analysis"],
            recommendations=report_data["recommendations"],
            is_fallback=True
        )
        return report

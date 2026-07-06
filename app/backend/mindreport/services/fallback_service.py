"""
기능: 채팅 데이터 부족 시(주간 5개/월간 20개 미만) 사용자에게 제공할 대체(Fallback) 리포트를 생성하는 서비스입니다.
"""
import sys
from django.conf import settings
from user.models import UserProfile

# ai 폴더를 import 할 수 있도록 PYTHONPATH 경로 임시 추가
if str(settings.PROJECT_ROOT) not in sys.path:
    sys.path.append(str(settings.PROJECT_ROOT))

from ai.agents.web_agent import FallbackWebAgent

class FallbackReportService:
    @staticmethod
    def generate_fallback_report(user, report_type="주간", range_text="이번 주"):
        """
        사용자 정보와 Web Agent(Mocking)를 사용하여 데이터 부족 보완 리포트를 생성합니다.
        """
        # 1. 사용자 프로필 정보 조회
        age = None
        gender = None
        hobbies = []
        interests = []
        
        # profile이 존재하지 않을 수도 있으므로 예외 처리
        if hasattr(user, 'profile'):
            profile = user.profile
            age = profile.age
            gender = profile.gender
            hobbies = profile.hobbies
            interests = profile.interests
            
        # 2. Web Agent로 트렌디한 콘텐츠/활동 추천 받기
        recommendations = FallbackWebAgent.get_trendy_contents(
            age=age, 
            gender=gender, 
            hobbies=hobbies, 
            interests=interests
        )
        
        # 3. 프론트엔드 ReportView.vue 구조에 맞게 JSON(Dict) 조립
        analysis_lines = [
            "아직 마음 리포트를 짠! 하고 보여드리기엔 대화 기록이 조금 부족해요 🥺 저와 조금 더 이야기를 나눠주시면, 마음의 흐름을 꼼꼼하게 살펴서 딱 맞는 리포트를 분석해 드릴게요! ✨",
            "우리의 소중한 대화가 모이는 동안 심심하시지 않게, 지금 당장 가볍게 기분 전환하기 딱 좋은 맞춤 활동들을 쏙쏙 골라왔어요! 🎁"
        ]
        
        recommendations_names = []
        for rec in recommendations:
            if isinstance(rec, dict):
                act = rec.get("activity", "")
                reason = rec.get("reason", "")
                how_to = rec.get("how_to", "")
                
                analysis_lines.append(f"✅ {act}")
                if reason:
                    analysis_lines.append(f"  - 왜 추천하나요? {reason}")
                if how_to:
                    analysis_lines.append(f"  - 어떻게 시작할까요? {how_to}")
                recommendations_names.append(act)
            else:
                # 만약 이전 로직처럼 문자열만 온 경우 방어 코드
                analysis_lines.append(f"✅ {rec}")
                recommendations_names.append(rec)
                
        report_data = {
            "id": f"fallback-{user.id}",
            "type": f"{report_type} (데이터 부족)",
            "range": range_text,
            "title": f"마음 리포트 분석 대기 중",
            "summary": "기록이 아직 적어 가볍게 시도할 수 있는 활동을 추천합니다.",
            "stressCauses": ["기록 수집 중..."],
            "reliefCauses": ["기록 수집 중..."],
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
            
        # 기존 가짜 리포트 삭제
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

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
        report_data = {
            "id": f"fallback-{user.id}",
            "type": f"{report_type} (데이터 부족)",
            "range": range_text,
            "title": f"마음 리포트 분석 대기 중",
            "summary": "기록이 아직 적어 가볍게 시도할 수 있는 활동을 추천합니다.",
            "stressCauses": ["기록 수집 중..."],
            "reliefCauses": ["기록 수집 중..."],
            "emotions": [], # 데이터가 없으므로 비움
            "analysis": [
                "아직 마음 리포트를 분석하기 위한 충분한 대화 기록이 모이지 않았어요. 챗봇과 조금 더 많은 이야기를 나누면, 나의 감정 흐름과 스트레스 원인을 더욱 정확히 분석해 드릴 수 있습니다.",
                "데이터가 모이는 동안, 사용자의 정보와 최근 트렌드를 반영하여 가볍게 즐길 수 있는 활동을 찾아봤습니다.",
                f"추천 환기 활동: {', '.join(recommendations)}"
            ],
            "recommendations": recommendations,
            "is_fallback": True
        }
        
        return report_data

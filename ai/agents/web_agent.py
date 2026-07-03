"""
기능: 데이터 부족 시 사용자의 프로필(나이, 성별, 관심사)을 바탕으로 최근 인기 있는 콘텐츠나 활동을 추천해주는 Web Agent 역할을 하는 파일입니다.
"""
import random

class FallbackWebAgent:
    """
    데이터 부족 시 사용자의 인구통계학적 특성(나이, 성별)과 관심사를 바탕으로
    요즘 인기 있는 환기 활동이나 콘텐츠를 추천하는 에이전트.
    """
    
    @staticmethod
    def get_trendy_contents(age, gender, hobbies=None, interests=None):
        """
        MVP 버전: 실제 검색 API 대신 하드코딩된 트렌드 풀을 반환합니다.
        추후 네이버 검색 API나 구글 트렌드 API, 또는 OpenAI API로 연동할 확장 포인트입니다.
        """
        # 타겟별 대표 트렌드 Mocking 데이터
        trends_db = {
            "20_male": ["웨이트 트레이닝", "PS5 콘솔 게임", "러닝크루 참여", "국내 단기 여행", "맛집 탐방"],
            "20_female": ["요가/필라테스", "감성 카페 투어", "전시회 관람", "베이킹 클래스", "호캉스"],
            "30_male": ["골프/테니스", "위스키/와인 시음", "캠핑/차박", "자전거 라이딩", "자동차 드라이브"],
            "30_female": ["오마카세 투어", "해외여행 계획하기", "플라워 클래스", "테니스", "홈인테리어"],
            "default": ["가벼운 동네 산책", "따뜻한 차 마시기", "넷플릭스 영화 시청", "좋아하는 음악 듣기", "스트레칭"]
        }
        
        # 나이대 계산 (예: 25 -> 20)
        age_group = (age // 10 * 10) if age and isinstance(age, int) else None
        
        key = "default"
        if age_group and gender:
            if "남" in gender:
                key = f"{age_group}_male"
            elif "여" in gender:
                key = f"{age_group}_female"
                
        candidates = trends_db.get(key, trends_db["default"])
        
        # 무작위로 3개 추천 추출
        recommendations = random.sample(candidates, min(len(candidates), 3))
        
        # 사용자의 실제 취미가 등록되어 있다면 첫 번째 추천을 대체
        if hobbies and isinstance(hobbies, list) and len(hobbies) > 0:
            recommendations[0] = f"{hobbies[0]}"
            
        return recommendations

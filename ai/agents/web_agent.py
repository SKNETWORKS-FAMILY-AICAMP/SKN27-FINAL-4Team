"""
기능: 데이터 부족 시 사용자의 프로필(나이, 성별, 관심사)을 바탕으로 최근 인기 있는 콘텐츠나 활동을 추천해주는 Web Agent 역할을 하는 파일입니다.
"""
import random
import os

class FallbackWebAgent:
    """
    데이터 부족 시 사용자의 인구통계학적 특성(나이, 성별)과 관심사를 바탕으로
    요즘 인기 있는 환기 활동이나 콘텐츠를 추천하는 에이전트.
    """
    
    @staticmethod
    def get_trendy_contents(age, gender, hobbies=None, interests=None):
        """
        OpenAI API를 사용하여 사용자 프로필 기반의 가벼운 환기 활동 3가지를 생성합니다.
        API 호출 실패 시 기존 Mocking 데이터(trends_db)를 Fallback으로 반환합니다.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # 1. API 키가 있으면 OpenAI 사용 시도
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                
                age_str = f"{age}세" if age else "연령 미상"
                gender_str = gender if gender else "성별 미상"
                hobbies_str = ", ".join(hobbies) if hobbies else "없음"
                interests_str = ", ".join(interests) if interests else "없음"
                
                prompt = (
                    f"사용자 정보: {age_str} {gender_str}, 취미: {hobbies_str}, 관심사: {interests_str}\n\n"
                    "위 사용자에게 딱 맞는 요즘 트렌디하고 가벼운 기분 전환(스트레스 해소) 활동 3가지를 추천해주세요.\n"
                    "부연 설명이나 번호 매기기 없이, 오직 추천 활동 이름 3개만 쉼표(,)로 구분해서 출력하세요. "
                    "(예시: 가벼운 동네 산책, 감성 카페 투어, 따뜻한 차 마시기)"
                )
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 사용자의 심리와 취향을 분석해 가벼운 환기 활동을 추천해주는 웰니스 도우미입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=100
                )
                
                result_text = response.choices[0].message.content.strip()
                # 쉼표를 기준으로 분리하고 양옆 공백 제거
                recommendations = [r.strip() for r in result_text.split(',') if r.strip()]
                
                # 정확히 3개가 나왔는지 확인
                if len(recommendations) >= 3:
                    return recommendations[:3]
                elif len(recommendations) > 0:
                    return recommendations
                    
            except Exception as e:
                print(f"OpenAI API Error: {e}")
                # 오류 발생 시 아래의 Fallback (Mock Data) 로직으로 자연스럽게 넘어감
        
        # 2. OpenAI 호출 실패, API 키 없음, 또는 결과 형식이 이상할 때의 Fallback 로직
        trends_db = {
            "20_male": ["웨이트 트레이닝", "PS5 콘솔 게임", "러닝크루 참여", "국내 단기 여행", "맛집 탐방"],
            "20_female": ["요가/필라테스", "감성 카페 투어", "전시회 관람", "베이킹 클래스", "호캉스"],
            "30_male": ["골프/테니스", "위스키/와인 시음", "캠핑/차박", "자전거 라이딩", "자동차 드라이브"],
            "30_female": ["오마카세 투어", "해외여행 계획하기", "플라워 클래스", "테니스", "홈인테리어"],
            "default": ["가벼운 동네 산책", "따뜻한 차 마시기", "넷플릭스 영화 시청", "좋아하는 음악 듣기", "스트레칭"]
        }
        
        age_group = (age // 10 * 10) if age and isinstance(age, int) else None
        
        key = "default"
        if age_group and gender:
            if "남" in gender:
                key = f"{age_group}_male"
            elif "여" in gender:
                key = f"{age_group}_female"
                
        candidates = trends_db.get(key, trends_db["default"])
        recommendations = random.sample(candidates, min(len(candidates), 3))
        
        if hobbies and isinstance(hobbies, list) and len(hobbies) > 0:
            recommendations[0] = f"{hobbies[0]}"
            
        return recommendations

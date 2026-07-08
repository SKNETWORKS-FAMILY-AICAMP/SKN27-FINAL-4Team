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
    def get_trendy_contents(age, gender, hobbies=None, interests=None, mbti=None):
        """
        OpenAI API를 사용하여 사용자 프로필 기반의 가벼운 환기 활동 3가지를 생성합니다.
        API 호출 실패 시 기존 Mocking 데이터(trends_db)를 Fallback으로 반환합니다.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        tavily_key = os.environ.get("TAVILY_API_KEY")
        
        # 1. API 키가 있으면 OpenAI 사용 시도
        if api_key:
            try:
                from openai import OpenAI
                import requests
                client = OpenAI(api_key=api_key)
                
                age_str = f"{age}대" if age else "연령 미상"
                gender_str = gender if gender else "성별 미상"
                hobbies_str = ", ".join(hobbies) if hobbies else "없음"
                interests_str = ", ".join(interests) if interests else "없음"
                
                # Tavily 웹 검색 로직 추가 (나이/성별 기반 최신 트렌드만 검색)
                age_str = f"{age}대" if age else "20대/30대"
                gender_str = gender if gender else "남녀 모두"
                
                search_context = ""
                if hobbies or interests:
                    search_context = f"사용자의 기존 취미/관심사: {', '.join((hobbies or []) + (interests or []))}\n"
                    
                mbti_context = ""
                if mbti:
                    mbti_context = f"사용자의 MBTI 성향: {mbti}\n"
                
                # Tavily 웹 검색 로직 추가
                tavily_search_str = ""
                if tavily_key:
                    try:
                        query = f"요즘 {age_str} {gender_str} 사이에서 유행하는 이색적인 스트레스 해소 힐링 활동 트렌드"
                        resp = requests.post(
                            "https://api.tavily.com/search",
                            json={"api_key": tavily_key, "query": query, "search_depth": "basic", "max_results": 3},
                            timeout=5
                        )
                        if resp.status_code == 200:
                            results = resp.json().get("results", [])
                            tavily_search_str = "\n[실시간 웹 트렌드 검색 결과]\n" + "\n".join(f"- {r.get('content', '')}" for r in results)
                    except Exception as search_err:
                        print(f"Tavily Search Error: {search_err}")

                prompt = (
                    f"타겟 사용자: {age_str} {gender_str}\n"
                    f"{search_context}"
                    f"{mbti_context}"
                    f"{tavily_search_str}\n\n"
                    "당신은 실시간 인터넷 트렌드를 분석하는 에이전트입니다.\n"
                    "위 타겟 연령대와 성별 사이에서 **최근 웹에서 새롭게 떠오르고 있는(유행하는) 트렌디하고 이색적인 기분 전환/스트레스 해소 활동 3가지**를 검색 결과를 바탕으로 추천해주세요.\n"
                    "사용자 성향(MBTI)이 주어졌다면 해당 성향에 잘 맞는 힐링 활동으로 맞춤 추천하세요. "
                    "단, **[절대 지켜야 할 규칙]: 화면에 '사용자의 MBTI(예: INFP)가 이러이러해서 추천한다'는 식의 직접적인 언급이나 설명은 절대로 출력하지 마세요.** 추천 활동과 내용에만 성향을 은근히 반영하세요.\n"
                    "뻔한 답변(산책, 음악 감상 등)을 피하고, 요즘 핫한 구체적인 트렌드 활동을 추천해야 합니다.\n"
                    "반드시 매우 따뜻하고 명랑하며, 이모지를 적절히 섞어 쓴 다정한 친구 같은 말투로 작성해주세요! (해요체 사용)\n"
                    "반드시 아래 JSON 형식으로 응답하세요:\n"
                    "{\n"
                    '  "recommendations": [\n'
                    '    {"activity": "활동 이름", "reason": "추천하는 이유 (1~2문장, 명랑하게)", "how_to": "어떤 방식으로 접근/시작하면 좋을지 (1~2문장, 따뜻하게)"}\n'
                    "  ]\n"
                    "}"
                )
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 실시간 인터넷 트렌드를 긁어와서 사용자에게 새롭고 핫한 힐링/환기 활동을 추천하는 웹 트렌드 분석가입니다. 반드시 JSON으로만 응답하세요."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                result_text = response.choices[0].message.content.strip()
                import json
                data = json.loads(result_text)
                
                recommendations = data.get("recommendations", [])
                
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
            "20_male": ["웨이트 트레이닝", "PS5 콘솔 게임", "하이록스 참여", "러닝크루 참여", "국내 단기 여행", "맛집 탐방"],
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
        recommendations_str = random.sample(candidates, min(len(candidates), 3))
        
        if hobbies and isinstance(hobbies, list) and len(hobbies) > 0:
            recommendations_str[0] = f"{hobbies[0]}"
            
        recommendations = [
            {
                "activity": rec,
                "reason": "요즘같이 지칠 때 가장 쉽고 확실하게 기분 전환을 할 수 있는 활동이랍니다! 완전 강추해요 🥰",
                "how_to": "처음부터 무리하지 말고 딱 10분만 가볍게 투자해 보는 건 어떨까요? 분명 기분이 한결 나아질 거예요! 🎈"
            }
            for rec in recommendations_str
        ]
            
        return recommendations

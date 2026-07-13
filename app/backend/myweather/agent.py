import json
import math
import os
import re
from datetime import datetime

import requests


TAVILY_SEARCH_URL = os.environ.get("TAVILY_SEARCH_URL", "https://api.tavily.com/search")
TAVILY_DEFAULT_DOMAINS = [
    "weather.daum.net",
    "www.weatheri.co.kr",
    "www.weather.go.kr",
]
TAVILY_MAX_RESULTS = int(os.environ.get("TAVILY_MAX_RESULTS", "4"))
TAVILY_SEARCH_DEPTH = os.environ.get("TAVILY_SEARCH_DEPTH", "advanced")
TAVILY_TIMEOUT_SECONDS = int(os.environ.get("TAVILY_TIMEOUT_SECONDS", "8"))


class WeatherWebAgent:
    @staticmethod
    def analyze(weather, user_profile=None):
        tavily_context = WeatherWebAgent._search_weather_context(weather)
        return WeatherWebAgent._generate_analysis(weather, user_profile or {}, tavily_context)

    @staticmethod
    def _search_weather_context(weather):
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        if not tavily_key:
            return {
                "answer": "",
                "snippets": "",
                "sources": [],
                "query": "",
                "available": False,
            }

        location = weather.get("location", {}).get("name", "현재 지역")
        condition = weather.get("condition", "날씨 정보 없음")
        temperature = weather.get("temperature")
        humidity = weather.get("humidity")
        today = datetime.now().strftime("%Y-%m-%d")
        query = (
            f"{today} {location} 현재 날씨 상태 기온 습도 강수 바람 체감 외출 난이도 "
            f"실내 쾌적도 집중 날씨 생활 가이드 {condition} 기온 {temperature}도 습도 {humidity}%"
        )
        domains = WeatherWebAgent._tavily_domains()

        try:
            response = requests.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "topic": "general",
                    "search_depth": TAVILY_SEARCH_DEPTH,
                    "max_results": TAVILY_MAX_RESULTS,
                    "include_answer": True,
                    "include_raw_content": False,
                    "include_images": False,
                    "include_domains": domains,
                },
                timeout=TAVILY_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
        except Exception as exc:
            print(f"[WeatherWebAgent] Tavily search failed: {exc}")
            return {
                "answer": "",
                "snippets": "",
                "sources": [],
                "query": query,
                "available": False,
            }

        snippets = []
        sources = []
        for result in results:
            title = result.get("title") or "검색 결과"
            content = WeatherWebAgent._compact_text(result.get("content") or "")
            url = result.get("url") or ""
            snippets.append(f"- {title}: {content} ({url})")
            if url:
                sources.append({
                    "title": title,
                    "url": url,
                })
        return {
            "answer": WeatherWebAgent._compact_text(payload.get("answer") or ""),
            "snippets": "\n".join(snippets),
            "sources": sources[:TAVILY_MAX_RESULTS],
            "query": query,
            "available": bool(results or payload.get("answer")),
        }


    @staticmethod
    def _calculate_weather_indices(weather):
        T_str = weather.get("temperature")
        RH_str = weather.get("humidity")
        V_str = weather.get("wind_speed")
        
        try:
            T = float(T_str)
        except:
            T = 20.0
        try:
            RH = float(RH_str)
        except:
            RH = 50.0
        try:
            V = float(V_str)
        except:
            V = 0.0

        # 1. 불쾌지수 (Discomfort Index)
        DI = 1.8 * T - 0.55 * (1 - RH / 100.0) * (1.8 * T - 26) + 32
        if DI >= 80:
            di_level = "매우 높음"
        elif DI >= 75:
            di_level = "높음"
        elif DI >= 68:
            di_level = "보통"
        else:
            di_level = "낮음"

        # 2. 식중독지수 (Food Poisoning Index - Heuristic)
        if T >= 35: fpi = 95
        elif T >= 30: fpi = 80 + (RH - 50) * 0.4
        elif T >= 25: fpi = 60 + (RH - 50) * 0.3
        elif T >= 15: fpi = 40 + (RH - 50) * 0.2
        else: fpi = 20
        fpi = max(0, min(100, fpi))
        if fpi >= 86: fpi_level = "위험"
        elif fpi >= 71: fpi_level = "경고"
        elif fpi >= 55: fpi_level = "주의"
        else: fpi_level = "관심"

        # 3. 체감온도 (Sensible Temperature)
        if T > 10:
            e = (RH / 100.0) * 6.105 * math.exp(17.27 * T / (237.7 + T))
            ST = T + 0.33 * e - 0.70 * V - 4.0
        else:
            V_kmh = V * 3.6
            if V_kmh > 4.8:
                ST = 13.12 + 0.6215 * T - 11.37 * (V_kmh**0.16) + 0.3965 * T * (V_kmh**0.16)
            else:
                ST = T
        if ST >= 33: st_level = "위험 (폭염)"
        elif ST >= 31: st_level = "경고"
        elif ST <= -15: st_level = "위험 (한파)"
        elif ST <= -10: st_level = "경고"
        else: st_level = "보통"

        # 4. 감기가능지수 (Cold Risk Index)
        if T < 5: cri = 90 - (RH - 30) * 0.5
        elif T < 10: cri = 70 - (RH - 40) * 0.5
        elif T < 15: cri = 50 - (RH - 50) * 0.5
        else: cri = 20
        cri = max(0, min(100, cri))
        if cri >= 90: cri_level = "매우 높음"
        elif cri >= 70: cri_level = "높음"
        elif cri >= 50: cri_level = "보통"
        else: cri_level = "낮음"

        return {
            "불쾌지수": {"score": int(DI), "level": di_level},
            "식중독지수": {"score": int(fpi), "level": fpi_level},
            "체감온도": {"score": int(ST), "level": st_level},
            "감기가능지수": {"score": int(cri), "level": cri_level},
        }

    @staticmethod
    def _generate_analysis(weather, user_profile, tavily_context):
        try:
            from ai.agents.llm import get_llm

            indices = WeatherWebAgent._calculate_weather_indices(weather)
            prompt = WeatherWebAgent._build_prompt(weather, user_profile, tavily_context, indices)
            llm = get_llm(temperature=0.35, max_tokens=4000)
            # Remove json_object binding to prevent 400 validation error on certain wrappers,
            # as _parse_json_response robustly handles markdown JSON.

            response = llm.invoke([
                (
                    "system",
                    "당신은 사용자의 마이룸 창문 밖 날씨를 하루 생활 감각으로 번역하는 한국어 날씨 동행자입니다. "
                    "날씨를 진단이나 치료로 해석하지 말고, 외출 부담, 실내 쾌적도, 집중 난이도, 휴식 리듬처럼 일상에서 바로 이해되는 언어로 풀어주세요. "
                    "반드시 유효한 JSON 객체만 출력하세요. 마크다운, 코드블록, 주석, JSON 밖 설명은 쓰지 마세요.",
                ),
                ("user", prompt),
            ])
            data = WeatherWebAgent._parse_json_response(response.content)
            return WeatherWebAgent._normalize(data, tavily_context, weather)
        except Exception as exc:
            try:
                print(f"[WeatherWebAgent] LLM output was: {response}")
            except Exception:
                pass
            print(f"[WeatherWebAgent] LLM analysis failed: {exc}")
            return WeatherWebAgent._fallback(weather)

    @staticmethod
    def _build_prompt(weather, user_profile, tavily_context, indices):
        location = weather.get("location", {}).get("name", "현재 지역")
        hobbies = ", ".join(user_profile.get("hobbies") or [])
        age = user_profile.get("age")
        gender = user_profile.get("gender") or ""
        tavily_answer = tavily_context.get("answer") or "검색 요약 없음"

        return (
            "[사용자&날씨 정보]\n"
            f"위치: {location}\n"
            f"기상: {weather.get('condition')}, {weather.get('temperature')}도, 습도 {weather.get('humidity')}%, 강수 {weather.get('rainfall_1h')}mm, 풍속 {weather.get('wind_speed')}m/s\n"
            f"사용자: {age if age is not None else '미상'}세, {gender or '미상'}, MBTI {user_profile.get('mbti') or '미상'}\n"
            f"취미/감정: {hobbies or '없음'} / {user_profile.get('today_emotion') or '해당 없음'}\n\n"
            "[산출된 기상 지표]\n"
            f"불쾌지수: {indices['불쾌지수']['score']}({indices['불쾌지수']['level']}), 식중독지수: {indices['식중독지수']['score']}({indices['식중독지수']['level']}), "
            f"체감온도: {indices['체감온도']['score']}({indices['체감온도']['level']}), 감기가능지수: {indices['감기가능지수']['score']}({indices['감기가능지수']['level']})\n\n"
            "[검색 맥락]\n"
            f"{tavily_answer}\n\n"
            "[출력 작성 원칙]\n"
            "1. weatherAnalysis (150~200자): 사용자의 나이, 성별, MBTI 성향에 맞추어 '흥미롭게 읽히도록' 날씨를 해설하되, 사용자 정보(나이/성별/MBTI 등)를 텍스트에 직접 노출하거나 인용하지 마세요. 분석 리포트처럼 딱딱하지 않고 부드럽고 자연스럽게 작성하세요.\n"
            "2. conditionGuide (4개 필수): 불쾌지수, 식중독지수, 체감온도, 감기가능지수의 산출된 점수와 레벨을 그대로 넣고, reason(20~40자)에 해당 지수의 현재 상태가 의미하는 바를 짧고 간결하게 설명하세요.\n"
            "3. weeklyForecast (100~150자): 검색 맥락을 활용하여 내일~주간 흐름을 간단명료하게 요약하세요.\n"
            "4. recommendations (3개 필수): 사용자의 취미와 '오늘의 감정'을 바탕으로 상황에 맞는 행동을 추천하세요. MBTI는 절대 반영하지 마세요. 성별, 나이, 감정을 문장에 직접 노출하지 말고 배경으로만 은은하게 참고하세요.\n"
            "   - reason (50~80자): 행동을 추천하는 구체적인 이유.\n"
            "   - howTo (50~100자): 즉시 실행 가능한 방법.\n"
            "5. 전반적 어투: 전문적이고 따뜻하게 작성하며, 의학적 지시나 공포를 주는 표현은 금지합니다.\n\n"
            "Output ONLY in JSON format:\n"
            "{\n"
            '  "weatherAnalysis": "맞춤형 날씨 해설 (직접 언급 금지)",\n'
            '  "moodImpact": "기분 영향 (선택)",\n'
            '  "conditionGuide": [{"label": "불쾌지수", "level": "...", "score": 0, "reason": "..."}],\n'
            '  "weeklyForecast": "주간 예보 요약",\n'
            '  "recommendations": [{"title": "...", "reason": "...", "howTo": "..."}],\n'
            '  "careNote": ""\n'
            "}"
        )

    @staticmethod
    def _normalize(data, tavily_context=None, weather=None):
        recommendations = data.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = []
        return {
            "weatherAnalysis": WeatherWebAgent._soften_phrasing(
                data.get("weatherAnalysis") or "현재 기상 데이터를 기반으로 날씨 분석을 준비 중입니다.",
                weather,
            ),
            "moodImpact": WeatherWebAgent._soften_phrasing(
                data.get("moodImpact") or "",
                weather,
            ),
            "conditionGuide": WeatherWebAgent._normalize_condition_guide(
                data.get("conditionGuide"),
                weather,
            ),
            "hourlyForecasts": weather.get("hourly_forecasts", []) if weather else [],
            "weeklyForecast": data.get("weeklyForecast") or "주간 날씨 정보를 가져오는 중입니다.",
            "recommendations": WeatherWebAgent._normalize_recommendations(recommendations, weather),
            "careNote": WeatherWebAgent._soften_phrasing(
                data.get("careNote") or "",
                weather,
            ),
            "sources": (tavily_context or {}).get("sources", []),
            "webSearchUsed": bool((tavily_context or {}).get("available")),
        }

    @staticmethod
    def _fallback(weather):
        condition = weather.get("condition") or "현재 날씨"
        humidity = WeatherWebAgent._to_float(weather.get("humidity"))
        temperature = WeatherWebAgent._to_float(weather.get("temperature"))
        condition_guide = WeatherWebAgent._fallback_condition_guide(weather)
        time_rhythm = WeatherWebAgent._fallback_time_rhythm(weather)

        recommendations = [
            {
                "title": "창문 옆 컨디션 체크",
                "reason": f"{condition} 날씨에는 지금 내 리듬이 어떤지 먼저 살펴보면 좋아요.",
                "howTo": "물 한 모금 마시고 어깨와 목을 30초만 천천히 풀어보세요.",
            },
            {
                "title": "작은 공간 정리",
                "reason": "날씨가 흐름을 흔들 때는 눈에 보이는 공간을 조금 정돈하면 마음도 따라 안정돼요.",
                "howTo": "책상 위 한 구역만 비우고, 오늘 할 일 하나를 가까이에 놓아보세요.",
            },
        ]

        if humidity is not None and humidity >= 70:
            recommendations.append({
                "title": "보송한 공기 만들기",
                "reason": "습도가 높으면 방 안 공기가 조금 답답하게 느껴질 수 있어요.",
                "howTo": "가능하면 짧게 환기하고, 외출 전에는 우산이나 겉옷을 가볍게 확인해보세요.",
            })
        elif temperature is not None and temperature >= 28:
            recommendations.append({
                "title": "열감 낮추기",
                "reason": "기온이 높으면 방 안에서도 리듬이 느슨해질 수 있어요.",
                "howTo": "시원한 물을 가까이에 두고, 해야 할 일은 짧은 단위로 나눠보세요.",
            })
        else:
            recommendations.append({
                "title": "가벼운 산책 준비",
                "reason": "날씨 부담이 크지 않다면 짧은 움직임이 기분 전환에 좋아요.",
                "howTo": "10분 정도만 천천히 걷고 돌아오는 방식으로 시작해보세요.",
            })

        return {
            "weatherAnalysis": f"현재 날씨는 {condition}입니다. 분석 데이터 로딩이 지연되고 있으나, 이 기상 정보를 바탕으로 가볍게 오늘의 페이스를 조절해보세요.",
            "moodImpact": "",
            "conditionGuide": condition_guide,
            "hourlyForecasts": weather.get("hourly_forecasts", []) if weather else [],
            "weeklyForecast": "일주일 예보 정보를 가져오는 데 시간이 걸리고 있습니다.",
            "recommendations": recommendations[:3],
            "careNote": "",
            "sources": [],
            "webSearchUsed": False,
            "is_fallback": True,
        }

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _tavily_domains():
        raw_domains = os.environ.get("TAVILY_INCLUDE_DOMAINS", "").strip()
        if not raw_domains:
            return TAVILY_DEFAULT_DOMAINS
        return [domain.strip() for domain in raw_domains.split(",") if domain.strip()]

    @staticmethod
    def _compact_text(text, limit=420):
        text = re.sub(r"\s+", " ", str(text)).strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}..."

    @staticmethod
    def _parse_json_response(content):
        text = str(content).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _normalize_condition_guide(items, weather=None):
        if not isinstance(items, list):
            return WeatherWebAgent._fallback_condition_guide(weather or {})

        labels = ["불쾌지수", "식중독지수", "체감온도", "감기가능지수"]
        normalized = []
        for index, item in enumerate(items[:4]):
            if not isinstance(item, dict):
                continue
            raw_score = item.get("score", 50)
            try:
                score = int(float(raw_score))
            except (TypeError, ValueError):
                score = 50
            
            level = item.get("level") or "보통"
            normalized.append({
                "label": WeatherWebAgent._soften_phrasing(item.get("label") or labels[index], weather),
                "level": level,
                "score": score,
                "reason": WeatherWebAgent._soften_phrasing(
                    item.get("reason") or "현재 날씨 기준으로 가볍게 참고할 수 있는 지표예요.",
                    weather,
                ),
            })

        if len(normalized) < 4:
            fallback = WeatherWebAgent._fallback_condition_guide(weather or {})
            seen = {item["label"] for item in normalized}
            normalized.extend(item for item in fallback if item["label"] not in seen)
        return normalized[:4]

    @staticmethod
    def _normalize_time_rhythm(items, weather=None):
        if not isinstance(items, list):
            return WeatherWebAgent._fallback_time_rhythm(weather or {})

        default_times = ["지금", "이후", "밤"]
        normalized = []
        for index, item in enumerate(items[:3]):
            if not isinstance(item, dict):
                continue
            normalized.append({
                "time": WeatherWebAgent._soften_phrasing(item.get("time") or default_times[index], weather),
                "title": WeatherWebAgent._soften_phrasing(item.get("title") or "날씨 리듬", weather),
                "description": WeatherWebAgent._soften_phrasing(
                    item.get("description") or "현재 날씨를 기준으로 편하게 참고해보세요.",
                    weather,
                ),
            })

        if len(normalized) < 3:
            fallback = WeatherWebAgent._fallback_time_rhythm(weather or {})
            normalized.extend(fallback[len(normalized):])
        return normalized[:3]

    @staticmethod
    def _fallback_condition_guide(weather):
        indices = WeatherWebAgent._calculate_weather_indices(weather)
        return [
            {"label": "불쾌지수", "level": indices["불쾌지수"]["level"], "score": indices["불쾌지수"]["score"], "reason": "현재 기온과 습도를 반영한 쾌적도 상태입니다."},
            {"label": "식중독지수", "level": indices["식중독지수"]["level"], "score": indices["식중독지수"]["score"], "reason": "현재 날씨에 따른 음식물 부패 위험도입니다."},
            {"label": "체감온도", "level": indices["체감온도"]["level"], "score": indices["체감온도"]["score"], "reason": "바람을 고려하여 실제로 느끼는 온도 상태입니다."},
            {"label": "감기가능지수", "level": indices["감기가능지수"]["level"], "score": indices["감기가능지수"]["score"], "reason": "기상 조건에 따른 호흡기 질환 가능성입니다."},
        ]

    @staticmethod
    def _fallback_time_rhythm(weather):
        condition = (weather or {}).get("condition") or "현재 날씨"
        humidity = WeatherWebAgent._to_float((weather or {}).get("humidity"))
        temperature = WeatherWebAgent._to_float((weather or {}).get("temperature"))
        later_note = "예보가 바뀔 수 있어 외출 전 한 번 더 확인하면 좋아요."
        if humidity is not None and humidity >= 70:
            later_note = "습도가 높게 느껴지면 환기보다 제습이나 온도 조절이 먼저예요."
        elif temperature is not None and temperature >= 28:
            later_note = "기온 부담이 이어질 수 있어 물과 쉬는 시간을 가까이 두면 좋아요."

        return [
            {
                "time": "지금",
                "title": condition,
                "description": "현재 관측값 기준으로 창밖 분위기를 먼저 확인했어요.",
            },
            {
                "time": "이후",
                "title": "생활 리듬 조절",
                "description": later_note,
            },
            {
                "time": "밤",
                "title": "실내 컨디션",
                "description": "밤에는 방 안 온도와 습도를 편한 쪽으로 맞춰두면 좋아요.",
            },
        ]

    @staticmethod
    def _score_level(score):
        if score >= 67:
            return "높음"
        if score >= 34:
            return "보통"
        return "낮음"

    @staticmethod
    def _normalize_recommendations(recommendations, weather=None):
        normalized = []
        for item in recommendations[:3]:
            if not isinstance(item, dict):
                continue
            normalized.append({
                "title": WeatherWebAgent._soften_phrasing(item.get("title") or "작은 날씨 루틴", weather),
                "reason": WeatherWebAgent._soften_phrasing(
                    item.get("reason") or "지금 날씨에 맞춰 오늘의 리듬을 편하게 잡는 데 도움이 돼요.",
                    weather,
                ),
                "howTo": WeatherWebAgent._soften_phrasing(
                    item.get("howTo") or "바로 할 수 있는 작은 행동부터 시작해보세요.",
                    weather,
                ),
            })
        return normalized

    @staticmethod
    def _soften_phrasing(text, weather=None):
        text = str(text)
        replacements = {
            "혈액 순환": "기분 전환",
            "면역": "컨디션",
            "치료": "돌봄",
            "증상": "몸의 신호",
            "완화": "덜어내기",
        }
        condition = (weather or {}).get("condition") or ""
        if "맑음" in condition:
            replacements.update({
                "따뜻한 햇살": "밝은 바깥 분위기",
                "강한 햇살": "밝은 바깥 분위기",
                "햇살": "바깥 분위기",
                "햇빛": "바깥 공기",
                "신선한 공기와 ": "바깥 공기가 ",
                "맑은 공기": "가벼운 바깥 공기",
                "맑고": "비 소식은 적고",
                "맑은": "비 소식이 적은",
                "자외선 차단제를 바르는": "외출 전 바깥 상황을 한 번 확인하는",
                "자외선 차단제": "외출 준비",
            })
        for source, target in replacements.items():
            text = text.replace(source, target)
        text = text.replace("분위기이", "분위기가")
        text = text.replace("창문 밖은 비 소식은", "창문 밖은 비 소식이")
        text = text.replace("밖은 비 소식은", "밖은 비 소식이")
        text = text.replace("비 소식은 적고", "비 소식이 적고")
        return text

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication

from .agent import WeatherWebAgent
from .services import WeatherInputError, WeatherServiceError, fetch_current_weather


def _request_value(request, key):
    if request.method == "GET":
        value = request.query_params.get(key)
    else:
        value = request.data.get(key)
    if isinstance(value, str):
        value = value.strip()
    return value or None


def _build_user_profile(user):
    profile = UserProfile.objects.filter(user=user).first()
    today_emotion = None
    try:
        from chat.models import ChatMessage
        from django.utils import timezone
        from django.db.models import Count
        
        today = timezone.localdate()
        emotion_counts = ChatMessage.objects.filter(
            session__user=user,
            emotion_label__isnull=False,
            created_at__date=today
        ).exclude(emotion_label__in=['', 'normal']).values('emotion_label').annotate(count=Count('emotion_label')).order_by('-count')
        
        if emotion_counts.exists():
            raw_emotion = emotion_counts.first()['emotion_label']
            emotion_map = {'anger': '분노', 'sadness': '슬픔', 'joy': '기쁨', 'normal': '평온함'}
            today_emotion = emotion_map.get(raw_emotion, raw_emotion)
    except Exception as e:
        print(f"Failed to fetch today emotion: {e}")

    return {
        "hobbies": getattr(profile, "hobbies", []) if profile else [],
        "today_emotion": today_emotion,
    }


@api_view(["GET", "POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def current_weather(request):
    lat = _request_value(request, "lat")
    lon = _request_value(request, "lon")
    region = _request_value(request, "region")

    try:
        weather = fetch_current_weather(lat=lat, lon=lon, region=region)
    except WeatherInputError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except ValueError:
        return Response(
            {"detail": "lat/lon은 숫자여야 합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except WeatherServiceError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    user_profile = _build_user_profile(request.user)

    # 토큰 소모 최적화: 유저의 상태(감정, 취미 등)와 날씨 기준 시각이 동일하면 LLM 결과를 캐싱
    import hashlib
    import json
    from django.core.cache import cache

    cache_state = {
        "version": 9,  # 단기·중기 7일 예보를 사용하는 검색 기반 주간요약 반영
        "user_id": request.user.id,
        "base_date": weather.get("base_date"),
        "base_time": weather.get("base_time"),
        "location_name": weather.get("location", {}).get("name"),
        "condition": weather.get("condition"),
        "temperature": weather.get("temperature"),
        "weekly_forecasts": [
            (
                item.get("date"),
                item.get("condition"),
                item.get("min_temperature"),
                item.get("max_temperature"),
                item.get("precipitation_probability"),
            )
            for item in weather.get("weekly_forecasts", [])
        ],
        "weather_alert_status": weather.get("weather_alerts", {}).get("status"),
        "weather_alerts": [
            (
                item.get("type"),
                item.get("level"),
                item.get("region"),
                item.get("effective_at"),
            )
            for item in weather.get("weather_alerts", {}).get("items", [])
        ],
        "emotion": user_profile.get("today_emotion"),
        "hobbies": user_profile.get("hobbies"),
    }
    
    state_str = json.dumps(cache_state, sort_keys=True)
    cache_key = "weather_insight_" + hashlib.md5(state_str.encode('utf-8')).hexdigest()

    insight = cache.get(cache_key)
    if not insight:
        print("======== [LLM 분석 실행] 캐시가 없으므로 LLM API를 호출합니다! ========")
        insight = WeatherWebAgent.analyze(weather, user_profile)
        # LLM 실패로 인한 Fallback 응답일 경우 60초만 캐시, 정상 응답은 1시간 캐시
        timeout_seconds = 60 if insight.get("is_fallback") else 3600
        cache.set(cache_key, insight, timeout=timeout_seconds)
    else:
        print("======== [캐시 적중] 저장된 LLM 리포트를 즉시 반환합니다! (토큰 0 소모) ========")

    attributions = [
        {
            "id": "kma",
            "label": "기상청 API허브",
            "url": "https://apihub.kma.go.kr/apiInfo.do",
            "license": "공공누리 제1유형(출처표시)",
            "detail": "API허브의 초단기실황·초단기예보·단기예보·중기기온·중기육상예보·현재 특보현황을 구조화 기상 데이터로 사용합니다. 일부 항목에는 제3자 권리가 포함될 수 있습니다.",
        }
    ]
    if insight.get("webSearchUsed"):
        attributions.append(
            insight.get("webSearchProvider")
            or {
                "id": "tavily",
                "label": "Tavily 웹 검색",
                "terms_url": "https://www.tavily.com/terms",
            }
        )

    tavily_status = insight.get("webSearchProvider") or {}
    tavily_cache_minutes = max(1, int(tavily_status.get("cache_seconds", 1800)) // 60)
    tavily_search_depth = tavily_status.get("search_depth", "basic")
    tavily_search_credits = tavily_status.get("credits_per_search", 1)
    tavily_domains = ", ".join(tavily_status.get("include_domains") or [])

    return Response({
        "weather": weather,
        "insight": insight,
        "attributions": attributions,
        "processing_notice": {
            "location": {
                "purpose": "기상청 예보 격자 변환 및 현재 지역 날씨 조회",
                "server_storage": "별도 저장하지 않음",
                "browser_storage": "현재 위치 좌표는 브라우저 탭 종료 시까지, 수동 선택 지역은 변경 또는 삭제 시까지",
            },
            "openai": {
                "data": ["선택한 취미", "오늘의 감정", "지역 단위 날씨"],
                "purpose": "개인화된 날씨 해설과 생활 추천 생성",
                "service_cache": "최대 1시간",
                "vendor_retention": "OpenAI API 정책에 따라 일반적으로 최대 30일의 부정사용 모니터링 로그",
                "training": "API 입력·출력은 명시적으로 동의하지 않는 한 모델 학습에 사용되지 않음",
                "policy_url": "https://platform.openai.com/docs/models/default-usage-policies-by-endpoint",
            },
            "tavily": {
                "data": ["지역명", "검색 기준일"],
                "purpose": "네이버 날씨·웨더아이·케이웨더 공개 검색 결과를 활용한 주간예보 설명과 생활 추천 맥락 검색",
                "service_cache": f"지역·검색일별 최대 {tavily_cache_minutes}분 공동 캐시",
                "personal_profile_sent": False,
                "vendor_retention": "Tavily 정책 및 계약에 따름. 검색어 일부가 서비스 개선에 사용될 수 있음",
                "privacy_url": "https://www.tavily.com/privacy",
            },
        },
        "methodology": {
            "summary": "불쾌지수·체감온도는 관측값으로 서비스가 계산한 참고값이며, 기상청이 별도로 발표한 생활기상지수 원문은 아닙니다. 습도·풍속은 왼쪽 현재 날씨 패널에서만 표시합니다.",
            "graph": "두 막대는 카드에 표시된 최소·최대 눈금 안에서 현재값의 위치를 나타냅니다. 현재 특보는 지수로 환산하지 않고 기상청 API허브의 특보 종류와 단계를 그대로 표시합니다.",
            "indices": insight.get("conditionGuide", []),
            "formula_source_url": "https://www.weather.go.kr/kma/servlet/NeoboardProcess?bid=press&mode=download&num=1194231&fno=2",
        },
        "api_limits": {
            "checked_at": "2026-07-15",
            "kma_api_hub": {
                "free": "일반회원 일 최대 20,000건·5GB, 동네예보·중기예보·특보현황 세부 API 활용신청 필요",
                "applied": (
                    f"실황·초단기예보 격자별 {weather.get('api_meta', {}).get('cache_seconds', 600)}초 공동 캐시·최대 2시간 정상값 대체, "
                    f"단기·중기 주간예보 3시간 공동 캐시·최대 24시간 정상값 대체, "
                    f"전국 특보현황 {weather.get('weather_alerts', {}).get('cache_seconds', 300)}초 공동 캐시"
                ),
                "configured": True,
                "url": "https://apihub.kma.go.kr/apiList.do?seqApi=10&seqApiSub=286",
                "warning_url": weather.get("weather_alerts", {}).get("docs_url", "https://apihub.kma.go.kr/apiInfo.do"),
            },
            "tavily": {
                "free": "월 1,000크레딧, development 키 분당 100회",
                "production": "production 키 분당 1,000회; 유료 플랜 또는 PAYGO 필요",
                "applied": f"{tavily_search_depth} 검색 {tavily_search_credits}크레딧, {tavily_domains or '지정 도메인'}만 검색, 지역·검색일별 {tavily_cache_minutes}분 공동 캐시, 429 Retry-After 준수",
                "url": "https://docs.tavily.com/documentation/rate-limits",
            },
            "openai": {
                "limit": "프로젝트·사용 등급별 요청/토큰 한도가 다름",
                "applied": "사용자·날씨 상태별 최대 1시간 생성문 캐시, 제한 오류 재시도 후 안전한 기본 안내",
                "url": "https://platform.openai.com/docs/guides/rate-limits",
            },
        },
    })

import logging

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.views import CsrfExemptSessionAuthentication

from .agent import WeatherWebAgent
from .constants import (
    API_LIMITS_CHECKED_AT,
    OPENAI_WEATHER_SHARED_FIELDS,
    STATIC_DEFAULT_WEATHER_REPRESENTATIVE_NAMES,
    TAVILY_WEATHER_SHARED_FIELDS,
)
from .models import WeatherRegion
from .service.exceptions import WeatherInputError, WeatherServiceError
from .service.insight_cache_service import (
    get_or_create_weather_insight,
    select_weather_hobby,
)
from .service.user_profile_service import build_weather_user_profile
from .services import fetch_current_weather

logger = logging.getLogger(__name__)


def _request_value(request, key):
    if request.method == "GET":
        value = request.query_params.get(key)
    else:
        value = request.data.get(key)
    if isinstance(value, str):
        value = value.strip()
    return value or None


def _request_flag(request, key):
    return str(_request_value(request, key) or "").lower() in {"1", "true", "yes", "on"}


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

    user_profile = select_weather_hobby(
        request.user.id,
        build_weather_user_profile(request.user),
        rotate=_request_flag(request, "rotate_hobby"),
    )
    insight, cache_hit = get_or_create_weather_insight(
        weather,
        request.user.id,
        user_profile,
        WeatherWebAgent.analyze,
    )
    if not cache_hit:
        logger.info("[LLM 분석 실행] 캐시가 없으므로 LLM API를 호출합니다!")
    else:
        logger.debug("[캐시 적중] 저장된 LLM 리포트를 즉시 반환합니다! (토큰 0 소모)")

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
                "data": list(OPENAI_WEATHER_SHARED_FIELDS),
                "purpose": "개인화된 날씨 해설과 생활 추천 생성",
                "service_cache": "최대 1시간",
                "vendor_retention": "OpenAI API 정책에 따라 일반적으로 최대 30일의 부정사용 모니터링 로그",
                "training": "API 입력·출력은 명시적으로 동의하지 않는 한 모델 학습에 사용되지 않음",
                "policy_url": "https://platform.openai.com/docs/models/default-usage-policies-by-endpoint",
            },
            "tavily": {
                "data": list(TAVILY_WEATHER_SHARED_FIELDS),
                "purpose": "네이버 날씨·웨더아이·케이웨더 공개 검색 결과를 활용한 주간예보 설명과 생활 추천 맥락 검색",
                "service_cache": f"지역·검색일별 최대 {tavily_cache_minutes}분 공동 캐시",
                "personal_profile_sent": False,
                "vendor_retention": "Tavily 정책 및 계약에 따름. 검색어 일부가 서비스 개선에 사용될 수 있음",
                "privacy_url": "https://www.tavily.com/privacy",
            },
        },
        "methodology": {
            "summary": "체감온도는 기상청 계절별 산식을, 불쾌지수는 기상청 과거 공식 산식을 재현합니다. 식중독지수는 기온·습도 기반 참고 산식의 계산값을 그대로 표시하며, 40℃·100% 산출값을 포괄하는 0~300 범위와 비례 조정한 단계 기준을 사용합니다. 현행 공식 발표값과는 구분합니다. 자외선지수는 기상청 생활기상지수 V5 API의 공식 발표값만 표시합니다.",
            "graph": "막대 색은 각 지수에 명시된 단계 구간, 흰색 표식은 현재 지수값의 위치입니다. 특보는 환산하지 않고 기상청 발표 단계를 그대로 표시합니다.",
            "indices": insight.get("conditionGuide", []),
            "formula_source_url": "https://data.kma.go.kr/climate/windChill/selectWindChillChart.do",
            "discomfort_source_url": "https://data.kma.go.kr/data/lwi/lwiList.do?pgmNo=635",
            "food_poisoning_source_url": "https://www.weather.go.kr/w/forecast/life/index-info.do",
            "uv_index_source_url": "https://www.weather.go.kr/w/forecast/life/index-info.do",
        },
        "api_limits": {
            "checked_at": API_LIMITS_CHECKED_AT,
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
            "kma_life_index": {
                "free": "공공데이터포털 개발계정 일 10,000건, 별도 활용신청 필요",
                "applied": "지역·발표시각별 1시간 공동 캐시, 장애 시 최대 6시간 내 공식 발표값만 명시적으로 재사용",
                "configured": weather.get("uv_index", {}).get("status") != "unconfigured",
                "available": weather.get("uv_index", {}).get("status") == "available",
                "url": "https://www.data.go.kr/data/15085288/openapi.do",
            },
            "tavily": {
                "free": "월 1,000크레딧, development 키 분당 100회",
                "production": "production 키 분당 1,000회; 유료 플랜 또는 PAYGO 필요",
                "applied": f"{tavily_search_depth} 검색 {tavily_search_credits}크레딧, {tavily_domains or '지정 도메인'}만 검색, 지역·검색일별 {tavily_cache_minutes}분 공동 캐시, 429 Retry-After 준수",
                "url": "https://docs.tavily.com/documentation/rate-limits",
            },
            "openai": {
                "limit": "프로젝트·사용 등급별 요청/토큰 한도가 다름",
                "applied": "사용자·날씨 상태별 최대 1시간 생성문 캐시, 생성 실패 시 임의 추천 없이 미제공 상태 표시",
                "url": "https://platform.openai.com/docs/guides/rate-limits",
            },
        },
    })


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_weather_regions(request):
    ordered_names = list(WeatherRegion.objects.order_by("id").values_list("name", flat=True))
    if not ordered_names:
        ordered_names = list(STATIC_DEFAULT_WEATHER_REPRESENTATIVE_NAMES)
    return Response(ordered_names)

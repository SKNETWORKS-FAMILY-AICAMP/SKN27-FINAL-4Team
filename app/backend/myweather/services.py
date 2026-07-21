import math
import os
import re
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime
from datetime import timedelta

import requests
from django.core.cache import cache
from django.utils import timezone

from .constants import (
    CATEGORY_MAP,
    KMA_EMPTY_VALUES,
    KMA_PRECIPITATION_EMPTY_VALUES,
    KMA_RESPONSE_ENCODINGS,
    KMA_RETRYABLE_STATUS_CODES,
    KMA_SHORT_FORECAST_RELEASE_HOURS,
    KOREAN_WEEKDAY_LABELS,
    PTY_LABELS,
    SKY_LABELS,
    WEEKLY_FORECAST_FILL_FIELDS,
)
from .service.exceptions import WeatherServiceError
from .service.life_index_service import fetch_uv_index
from .service.region_service import (
    resolve_location,
    resolve_mid_forecast_codes,
)
from .service.warning_service import (
    filter_kma_warnings,
    parse_kma_warning_rows,
    warning_region_aliases,
)


KMA_API_HUB_VILAGE_ENDPOINT = os.environ.get(
    "KMA_API_HUB_VILAGE_ENDPOINT",
    "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0",
)
KMA_CURRENT_WEATHER_OPERATION = "getUltraSrtNcst"
KMA_ULTRA_SHORT_FORECAST_OPERATION = "getUltraSrtFcst"
KMA_SHORT_FORECAST_OPERATION = "getVilageFcst"
KMA_API_HUB_MID_ENDPOINT = os.environ.get(
    "KMA_API_HUB_MID_ENDPOINT",
    "https://apihub.kma.go.kr/api/typ02/openApi/MidFcstInfoService",
)
KMA_MID_TEMPERATURE_OPERATION = "getMidTa"
KMA_MID_LAND_OPERATION = "getMidLandFcst"
KMA_CACHE_SECONDS = max(60, int(os.environ.get("KMA_CACHE_SECONDS", "600")))
KMA_STALE_CACHE_SECONDS = max(
    KMA_CACHE_SECONDS,
    int(os.environ.get("KMA_STALE_CACHE_SECONDS", "7200")),
)
KMA_TIMEOUT_SECONDS = max(3, int(os.environ.get("KMA_TIMEOUT_SECONDS", "8")))
KMA_RETRY_COUNT = max(0, int(os.environ.get("KMA_RETRY_COUNT", "1")))
KMA_WARNING_ENDPOINT = os.environ.get(
    "KMA_API_HUB_WARNING_ENDPOINT",
    "https://apihub.kma.go.kr/api/typ01/url/wrn_now_data.php",
)
KMA_WARNING_CACHE_SECONDS = max(
    60,
    int(os.environ.get("KMA_WARNING_CACHE_SECONDS", "300")),
)
KMA_WARNING_STALE_SECONDS = max(
    KMA_WARNING_CACHE_SECONDS,
    int(os.environ.get("KMA_WARNING_STALE_SECONDS", "1800")),
)
KMA_WEEKLY_CACHE_SECONDS = max(
    KMA_CACHE_SECONDS,
    int(os.environ.get("KMA_WEEKLY_CACHE_SECONDS", "10800")),
)
KMA_WEEKLY_STALE_SECONDS = max(
    KMA_WEEKLY_CACHE_SECONDS,
    int(os.environ.get("KMA_WEEKLY_STALE_SECONDS", "86400")),
)

def get_kma_api_hub_key():
    """실황·예보·특보에 공통으로 사용하는 기상청 API허브 인증키."""
    return (
        os.environ.get("KMA_API_HUB_AUTH_KEY")
        or os.environ.get("KMA_APIHUB_AUTH_KEY")
        or ""
    ).strip()


_warning_region_aliases = warning_region_aliases


def _decode_kma_hub_response(response):
    content = response.content
    for encoding in KMA_RESPONSE_ENCODINGS:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _request_kma_warning_rows(auth_key):
    last_error = None
    for attempt in range(KMA_RETRY_COUNT + 1):
        try:
            response = requests.get(
                KMA_WARNING_ENDPOINT,
                params={
                    "fe": "e",
                    "tm": "",
                    "disp": "1",
                    "help": "1",
                    "authKey": auth_key,
                },
                timeout=KMA_TIMEOUT_SECONDS,
            )
            if response.status_code in KMA_RETRYABLE_STATUS_CODES and attempt < KMA_RETRY_COUNT:
                time.sleep(0.25 * (2 ** attempt))
                continue
            response.raise_for_status()
            text = _decode_kma_hub_response(response)
            rows = parse_kma_warning_rows(text)
            lowered = text.lower()
            if not rows and any(token in lowered for token in ("authkey", "인증키", "error")):
                raise WeatherServiceError("기상청 API허브 인증 또는 응답 오류")
            return rows
        except (requests.RequestException, WeatherServiceError) as exc:
            last_error = exc
            if attempt >= KMA_RETRY_COUNT:
                break
    raise WeatherServiceError(
        f"기상청 API허브 특보 조회 실패: {last_error.__class__.__name__}"
    ) from last_error


def fetch_weather_warnings(location):
    source_url = "https://www.weather.go.kr/w/weather/warning/status.do"
    docs_url = (
        "https://apihub.kma.go.kr/apiList.do?"
        "apiMov=%ED%8A%B9.%EC%A0%95%EB%B3%B4+%EC%9E%90%EB%A3%8C+%EC%A1%B0%ED%9A%8C&"
        "seqApi=10&seqApiSub=288"
    )
    auth_key = get_kma_api_hub_key()
    if not auth_key:
        return {
            "available": False,
            "status": "key_required",
            "items": [],
            "region": location.get("name", "현재 지역"),
            "message": "기상청 API허브 인증키 설정 후 현재 특보를 표시합니다.",
            "source_url": source_url,
            "docs_url": docs_url,
        }

    if not _warning_region_aliases(location.get("name")):
        return {
            "available": False,
            "status": "region_unmapped",
            "items": [],
            "region": location.get("name", "현재 지역"),
            "message": "현재 좌표의 특보구역을 확정할 수 없어 공식 특보 페이지를 확인해 주세요.",
            "source_url": source_url,
            "docs_url": docs_url,
        }

    cache_key = "myweather:kma:warnings:current"
    stale_key = "myweather:kma:warnings:stale"
    rows = _cached_payload(cache_key)
    cache_status = "fresh"
    if rows is None:
        try:
            rows = _request_kma_warning_rows(auth_key)
            cache.set(cache_key, rows, timeout=KMA_WARNING_CACHE_SECONDS)
            cache.set(stale_key, rows, timeout=KMA_WARNING_STALE_SECONDS)
            cache_status = "miss"
        except WeatherServiceError:
            rows = _cached_payload(stale_key)
            if rows is None:
                return {
                    "available": False,
                    "status": "unavailable",
                    "items": [],
                    "region": location.get("name", "현재 지역"),
                    "message": "기상청 특보를 일시적으로 확인할 수 없습니다.",
                    "source_url": source_url,
                    "docs_url": docs_url,
                }
            cache_status = "stale"

    alerts = filter_kma_warnings(rows, location.get("name")) or []
    return {
        "available": True,
        "status": "active" if alerts else "none",
        "items": alerts,
        "region": location.get("name", "현재 지역"),
        "message": "발효 중인 기상특보가 있습니다." if alerts else "현재 발효 중인 기상특보가 없습니다.",
        "checked_at": timezone.localtime().strftime("%Y%m%d%H%M"),
        "cache_status": cache_status,
        "cache_seconds": KMA_WARNING_CACHE_SECONDS,
        "source_url": source_url,
        "docs_url": docs_url,
    }


def get_current_weather_url():
    endpoint = KMA_API_HUB_VILAGE_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_CURRENT_WEATHER_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_CURRENT_WEATHER_OPERATION}"


def get_ultra_short_forecast_url():
    endpoint = KMA_API_HUB_VILAGE_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_ULTRA_SHORT_FORECAST_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_ULTRA_SHORT_FORECAST_OPERATION}"


def get_short_forecast_url():
    endpoint = KMA_API_HUB_VILAGE_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_SHORT_FORECAST_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_SHORT_FORECAST_OPERATION}"


def get_mid_temperature_url():
    endpoint = KMA_API_HUB_MID_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_MID_TEMPERATURE_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_MID_TEMPERATURE_OPERATION}"


def get_mid_land_url():
    endpoint = KMA_API_HUB_MID_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_MID_LAND_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_MID_LAND_OPERATION}"


def latlon_to_grid(lat, lon):
    """기상청 동네예보 격자 변환 공식."""
    re = 6371.00877
    grid = 5.0
    slat1 = 30.0
    slat2 = 60.0
    olon = 126.0
    olat = 38.0
    xo = 43
    yo = 136

    degrad = math.pi / 180.0
    re_grid = re / grid
    slat1_rad = slat1 * degrad
    slat2_rad = slat2 * degrad
    olon_rad = olon * degrad
    olat_rad = olat * degrad

    sn = math.tan(math.pi * 0.25 + slat2_rad * 0.5) / math.tan(math.pi * 0.25 + slat1_rad * 0.5)
    sn = math.log(math.cos(slat1_rad) / math.cos(slat2_rad)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1_rad * 0.5)
    sf = (sf ** sn) * math.cos(slat1_rad) / sn
    ro = math.tan(math.pi * 0.25 + olat_rad * 0.5)
    ro = re_grid * sf / (ro ** sn)

    ra = math.tan(math.pi * 0.25 + lat * degrad * 0.5)
    ra = re_grid * sf / (ra ** sn)
    theta = lon * degrad - olon_rad
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    return {
        "nx": int(math.floor(ra * math.sin(theta) + xo + 0.5)),
        "ny": int(math.floor(ro - ra * math.cos(theta) + yo + 0.5)),
    }


def current_kma_base_time():
    """초단기실황은 매시각 10분 이후 호출 가능하므로 10분 전이면 이전 정시를 사용한다."""
    kst_now = timezone.localtime()
    safe_time = kst_now if kst_now.minute >= 10 else kst_now - timedelta(hours=1)
    return safe_time.strftime("%Y%m%d"), safe_time.strftime("%H00")


def ultra_short_forecast_base_time():
    """초단기예보는 매시 30분 발표 후 여유를 두고 이전 시각을 조회한다."""
    kst_now = timezone.localtime()
    safe_time = kst_now if kst_now.minute >= 45 else kst_now - timedelta(hours=1)
    return safe_time.strftime("%Y%m%d"), safe_time.strftime("%H30")


def short_forecast_base_time():
    """단기예보 발표시각 중 API 반영 여유 15분을 지난 가장 최근 회차를 선택한다."""
    safe_time = timezone.localtime() - timedelta(minutes=15)
    release_candidates = [
        safe_time.replace(hour=hour, minute=0, second=0, microsecond=0)
        for hour in KMA_SHORT_FORECAST_RELEASE_HOURS
        if hour <= safe_time.hour
    ]
    if release_candidates:
        selected = release_candidates[-1]
    else:
        previous_day = safe_time - timedelta(days=1)
        selected = previous_day.replace(hour=23, minute=0, second=0, microsecond=0)
    return selected.strftime("%Y%m%d"), selected.strftime("%H00")


def mid_forecast_base_time():
    """중기예보의 06/18시 발표 중 최근 24시간 안의 최신 회차를 선택한다."""
    safe_time = timezone.localtime() - timedelta(minutes=30)
    if safe_time.hour >= 18:
        selected = safe_time.replace(hour=18, minute=0, second=0, microsecond=0)
    elif safe_time.hour >= 6:
        selected = safe_time.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        previous_day = safe_time - timedelta(days=1)
        selected = previous_day.replace(hour=18, minute=0, second=0, microsecond=0)
    return selected.strftime("%Y%m%d%H00")


def normalize_obsr_value(value):
    if value in KMA_EMPTY_VALUES:
        return None
    try:
        numeric = float(value)
        if numeric >= 900 or numeric <= -900:
            return None
    except (TypeError, ValueError):
        return value
    return str(value)


def parse_kma_items(items):
    observations = {}
    raw = {}
    for item in items:
        category = item.get("category")
        value = normalize_obsr_value(item.get("obsrValue"))
        raw[category] = value
        if category in CATEGORY_MAP:
            key, label, unit = CATEGORY_MAP[category]
            observations[key] = {
                "label": label,
                "value": value,
                "unit": unit,
            }

    pty_value = raw.get("PTY", "0")
    precipitation_label = PTY_LABELS.get(str(pty_value), "알 수 없음")
    temperature = observations.get("temperature", {}).get("value")
    humidity = observations.get("humidity", {}).get("value")
    wind_speed = observations.get("wind_speed", {}).get("value")
    rainfall = observations.get("rainfall_1h", {}).get("value")

    return {
        "condition": precipitation_label,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "rainfall_1h": rainfall,
        "observations": observations,
        "raw_categories": raw,
    }


def normalize_forecast_value(value):
    if value in KMA_EMPTY_VALUES:
        return None
    return str(value)


def has_precipitation_amount(value):
    if value in KMA_PRECIPITATION_EMPTY_VALUES:
        return False
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        text = str(value).strip().lower().replace(" ", "")
        return text not in {"0", "0.0", "0mm", "0.0mm"}


def merge_forecast_rainfall(observed_rainfall, forecast):
    """Keep a positive observation, otherwise fill it from the matching rainy forecast."""
    if has_precipitation_amount(observed_rainfall):
        return observed_rainfall
    precipitation_type = str(forecast.get("forecast_precipitation_type") or "0")
    forecast_rainfall = forecast.get("forecast_rainfall_1h")
    if precipitation_type not in {"0", "None", ""} and has_precipitation_amount(forecast_rainfall):
        return forecast_rainfall
    return observed_rainfall


def parse_ultra_short_forecast_items(items):
    forecasts_by_time = {}
    for item in items:
        category = item.get("category")
        if category not in {"SKY", "PTY", "T1H", "RN1"}:
            continue
        fcst_date = item.get("fcstDate") or ""
        fcst_time = item.get("fcstTime") or ""
        value = normalize_forecast_value(item.get("fcstValue"))
        if not fcst_date or not fcst_time:
            continue
        key = f"{fcst_date}{fcst_time}"
        forecasts_by_time.setdefault(key, {})[category] = value

    if not forecasts_by_time:
        return {}

    now = timezone.localtime().replace(second=0, microsecond=0, tzinfo=None)
    forecast_times = []
    for key in forecasts_by_time:
        try:
            forecast_times.append((datetime.strptime(key, "%Y%m%d%H%M"), key))
        except ValueError:
            continue
    if not forecast_times:
        return {}

    forecast_times.sort()
    future_times = [(forecast_at, key) for forecast_at, key in forecast_times if forecast_at >= now]
    # 현재 하늘 상태는 날짜 경계를 포함한 실제 시간 차가 가장 작은 예보값을 쓴다.
    selected_key = min(forecast_times, key=lambda entry: abs(entry[0] - now))[1]
    selected = forecasts_by_time[selected_key]
    pty_value = selected.get("PTY") or "0"
    sky_value = selected.get("SKY")
    has_precipitation = str(pty_value) not in {"0", "None", ""}
    condition = PTY_LABELS.get(str(pty_value)) if has_precipitation else SKY_LABELS.get(str(sky_value))

    hourly_forecasts = []
    display_times = future_times[:6] if future_times else forecast_times[-1:]
    for _, key in display_times:
        data = forecasts_by_time[key]
        pty = data.get("PTY") or "0"
        sky = data.get("SKY")
        cond = PTY_LABELS.get(str(pty)) if str(pty) not in {"0", "None", ""} else SKY_LABELS.get(str(sky), "알 수 없음")
        
        hourly_forecasts.append({
            "time": f"{key[8:10]}:{key[10:12]}",
            "condition": cond,
            "temperature": data.get("T1H"),
            "rainfall": data.get("RN1"),
            "sky_code": sky,
            "pty_code": pty,
        })

    return {
        "condition": condition or "알 수 없음",
        "sky_code": sky_value,
        "sky": SKY_LABELS.get(str(sky_value), ""),
        "forecast_precipitation_type": pty_value,
        "forecast_rainfall_1h": selected.get("RN1"),
        "forecast_time": {
            "date": selected_key[:8],
            "time": selected_key[8:12],
        },
        "raw_forecast_categories": selected,
        "hourly_forecasts": hourly_forecasts,
    }


def _numeric_forecast_value(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _day_label(date_value):
    try:
        parsed_date = datetime.strptime(date_value, "%Y%m%d").date()
    except (TypeError, ValueError):
        return ""
    return f"{parsed_date.month}/{parsed_date.day}({KOREAN_WEEKDAY_LABELS[parsed_date.weekday()]})"


def _conditions_for_slots(slots):
    conditions = []
    for slot in slots:
        precipitation_type = str(slot.get("PTY") or "0")
        if precipitation_type not in {"0", "None", ""}:
            condition = PTY_LABELS.get(precipitation_type, "강수")
        else:
            condition = SKY_LABELS.get(str(slot.get("SKY") or ""), "")
        if condition:
            conditions.append(condition)
    if not conditions:
        return "알 수 없음"
    ranked = [item for item, _ in Counter(conditions).most_common(2)]
    return "/".join(ranked)


def parse_short_forecast_items(items):
    """단기예보의 시간별 값을 날짜별 최저·최고·대표날씨·최대 강수확률로 묶는다."""
    slots_by_date = {}
    for item in items:
        forecast_date = str(item.get("fcstDate") or "")
        forecast_time = str(item.get("fcstTime") or "")
        category = str(item.get("category") or "")
        if not forecast_date or not forecast_time or not category:
            continue
        slot = slots_by_date.setdefault(forecast_date, {}).setdefault(forecast_time, {})
        slot[category] = normalize_forecast_value(item.get("fcstValue"))

    daily = []
    for forecast_date in sorted(slots_by_date):
        slots = [slots_by_date[forecast_date][key] for key in sorted(slots_by_date[forecast_date])]
        hourly_temperatures = [
            value
            for value in (_numeric_forecast_value(slot.get("TMP")) for slot in slots)
            if value is not None
        ]
        official_minimums = [
            value
            for value in (_numeric_forecast_value(slot.get("TMN")) for slot in slots)
            if value is not None
        ]
        official_maximums = [
            value
            for value in (_numeric_forecast_value(slot.get("TMX")) for slot in slots)
            if value is not None
        ]
        precipitation_probabilities = [
            value
            for value in (_numeric_forecast_value(slot.get("POP")) for slot in slots)
            if value is not None
        ]
        minimum = official_minimums[0] if official_minimums else (
            min(hourly_temperatures) if hourly_temperatures else None
        )
        maximum = official_maximums[0] if official_maximums else (
            max(hourly_temperatures) if hourly_temperatures else None
        )
        daily.append({
            "date": datetime.strptime(forecast_date, "%Y%m%d").date().isoformat(),
            "day": _day_label(forecast_date),
            "condition": _conditions_for_slots(slots),
            "min_temperature": minimum,
            "max_temperature": maximum,
            "precipitation_probability": max(precipitation_probabilities) if precipitation_probabilities else None,
            "source": "기상청 API허브 단기예보",
        })
    return daily


def parse_mid_forecast_items(temperature_items, land_items, tm_fc):
    """중기 기온과 육상예보를 같은 날짜의 일별 값으로 합친다."""
    temperatures = temperature_items[0] if temperature_items else {}
    land = land_items[0] if land_items else {}
    try:
        release_date = datetime.strptime(str(tm_fc)[:8], "%Y%m%d").date()
    except (TypeError, ValueError):
        return []

    daily = []
    for offset in range(4, 11):
        forecast_date = release_date + timedelta(days=offset)
        morning_weather = land.get(f"wf{offset}Am")
        afternoon_weather = land.get(f"wf{offset}Pm")
        if offset >= 8:
            morning_weather = land.get(f"wf{offset}") or morning_weather
            afternoon_weather = None
        conditions = []
        for value in (morning_weather, afternoon_weather):
            if value and value not in conditions:
                conditions.append(value)
        rain_values = [
            value
            for value in (
                _numeric_forecast_value(land.get(f"rnSt{offset}Am")),
                _numeric_forecast_value(land.get(f"rnSt{offset}Pm")),
                _numeric_forecast_value(land.get(f"rnSt{offset}")),
            )
            if value is not None
        ]
        minimum = _numeric_forecast_value(temperatures.get(f"taMin{offset}"))
        maximum = _numeric_forecast_value(temperatures.get(f"taMax{offset}"))
        if not conditions and minimum is None and maximum is None and not rain_values:
            continue
        date_key = forecast_date.strftime("%Y%m%d")
        daily.append({
            "date": forecast_date.isoformat(),
            "day": _day_label(date_key),
            "condition": "/".join(conditions) or "알 수 없음",
            "min_temperature": minimum,
            "max_temperature": maximum,
            "precipitation_probability": max(rain_values) if rain_values else None,
            "source": "기상청 API허브 중기예보",
        })
    return daily


def merge_weekly_forecasts(short_forecasts, mid_forecasts, today=None):
    """오늘부터 7일간은 단기예보를 우선하고 비어 있는 구간만 중기예보로 채운다."""
    today = today or timezone.localdate()
    last_date = today + timedelta(days=6)
    merged = {item["date"]: deepcopy(item) for item in mid_forecasts}
    for short_item in short_forecasts:
        date_key = short_item["date"]
        existing = merged.get(date_key, {})
        combined = {**existing, **deepcopy(short_item)}
        for field in WEEKLY_FORECAST_FILL_FIELDS:
            if combined.get(field) is None and existing.get(field) is not None:
                combined[field] = existing[field]
        if existing:
            combined["source"] = "기상청 API허브 단기·중기예보"
        merged[date_key] = combined

    weekly = []
    for date_key in sorted(merged):
        try:
            forecast_date = datetime.strptime(date_key, "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= forecast_date <= last_date:
            weekly.append(merged[date_key])
    return weekly[:7]


def _cached_payload(cache_key):
    cached = cache.get(cache_key)
    return deepcopy(cached) if cached is not None else None


def _request_kma_json(url, params):
    last_error = None
    for attempt in range(KMA_RETRY_COUNT + 1):
        try:
            response = requests.get(url, params=params, timeout=KMA_TIMEOUT_SECONDS)
            if response.status_code in KMA_RETRYABLE_STATUS_CODES and attempt < KMA_RETRY_COUNT:
                if response.status_code == 429:
                    try:
                        retry_after = float(response.headers.get("Retry-After", "0.25"))
                    except (TypeError, ValueError):
                        retry_after = 0.25
                    time.sleep(max(0.25, min(2.0, retry_after)))
                else:
                    time.sleep(0.25 * (2 ** attempt))
                continue
            if response.status_code >= 400:
                raise WeatherServiceError(f"기상청 API 호출에 실패했습니다: HTTP {response.status_code}")
            return response.json()
        except (requests.RequestException, ValueError, WeatherServiceError) as exc:
            last_error = exc
            if attempt >= KMA_RETRY_COUNT:
                break
    if isinstance(last_error, WeatherServiceError):
        raise last_error
    if isinstance(last_error, ValueError):
        raise WeatherServiceError("기상청 API 응답을 JSON으로 해석하지 못했습니다.") from last_error
    raise WeatherServiceError(
        f"기상청 API 호출에 실패했습니다: {last_error.__class__.__name__}"
    ) from last_error


def _validate_kma_payload(payload):
    header = payload.get("response", {}).get("header", {})
    result_code = header.get("resultCode")
    if result_code not in ("00", "0"):
        message = header.get("resultMsg") or "기상청 API 오류"
        raise WeatherServiceError(f"{message} ({result_code})")
    return (
        payload.get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )


def fetch_sky_forecast(auth_key, grid):
    base_date, base_time = ultra_short_forecast_base_time()
    cache_key = f"myweather:kma:fcst:{base_date}:{base_time}:{grid['nx']}:{grid['ny']}"
    cached = _cached_payload(cache_key)
    if cached is not None:
        cached["cache_status"] = "fresh"
        return cached
    params = {
        "authKey": auth_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"],
    }

    stale_key = f"myweather:kma:fcst:stale:{grid['nx']}:{grid['ny']}"
    try:
        payload = _request_kma_json(get_ultra_short_forecast_url(), params)
        items = _validate_kma_payload(payload)
    except WeatherServiceError:
        stale = _cached_payload(stale_key)
        if stale is not None:
            stale["cache_status"] = "stale"
            return stale
        return {}
    parsed = parse_ultra_short_forecast_items(items)
    if not parsed:
        return {}
    parsed["forecast_base_date"] = base_date
    parsed["forecast_base_time"] = base_time
    parsed["cache_status"] = "miss"
    cache.set(cache_key, parsed, timeout=KMA_CACHE_SECONDS)
    cache.set(stale_key, parsed, timeout=KMA_STALE_CACHE_SECONDS)
    return parsed


def fetch_weekly_forecast(auth_key, grid, location):
    short_date, short_time = short_forecast_base_time()
    mid_time = mid_forecast_base_time()
    mid_codes = resolve_mid_forecast_codes(location)
    cache_key = (
        f"myweather:kma:weekly:{short_date}:{short_time}:{mid_time}:"
        f"{grid['nx']}:{grid['ny']}:{mid_codes['land']}:{mid_codes['temperature']}"
    )
    cached = _cached_payload(cache_key)
    if cached is not None:
        cached["cache_status"] = "fresh"
        return cached

    stale_key = (
        f"myweather:kma:weekly:stale:{grid['nx']}:{grid['ny']}:"
        f"{mid_codes['land']}:{mid_codes['temperature']}"
    )
    common_params = {
        "authKey": auth_key,
        "pageNo": 1,
        "dataType": "JSON",
    }
    errors = []
    short_forecasts = []
    mid_temperature_items = []
    mid_land_items = []

    try:
        short_payload = _request_kma_json(get_short_forecast_url(), {
            **common_params,
            "numOfRows": 1000,
            "base_date": short_date,
            "base_time": short_time,
            "nx": grid["nx"],
            "ny": grid["ny"],
        })
        short_forecasts = parse_short_forecast_items(_validate_kma_payload(short_payload))
    except WeatherServiceError:
        errors.append("short_forecast")

    try:
        temperature_payload = _request_kma_json(get_mid_temperature_url(), {
            **common_params,
            "numOfRows": 10,
            "regId": mid_codes["temperature"],
            "tmFc": mid_time,
        })
        mid_temperature_items = _validate_kma_payload(temperature_payload)
    except WeatherServiceError:
        errors.append("mid_temperature")

    try:
        land_payload = _request_kma_json(get_mid_land_url(), {
            **common_params,
            "numOfRows": 10,
            "regId": mid_codes["land"],
            "tmFc": mid_time,
        })
        mid_land_items = _validate_kma_payload(land_payload)
    except WeatherServiceError:
        errors.append("mid_land")

    mid_forecasts = parse_mid_forecast_items(mid_temperature_items, mid_land_items, mid_time)
    weekly = merge_weekly_forecasts(short_forecasts, mid_forecasts)
    stale = _cached_payload(stale_key)
    if stale is not None and errors and len(stale.get("days", [])) > len(weekly):
        stale["cache_status"] = "stale"
        stale["errors"] = errors
        return stale
    if not weekly:
        if stale is not None:
            stale["cache_status"] = "stale"
            stale["errors"] = errors
            return stale
        return {"days": [], "cache_status": "unavailable", "errors": errors}

    result = {
        "days": weekly,
        "short_base_date": short_date,
        "short_base_time": short_time,
        "mid_base_time": mid_time,
        "mid_region_codes": mid_codes,
        "cache_status": "partial" if errors else "miss",
        "errors": errors,
    }
    cache.set(cache_key, result, timeout=KMA_WEEKLY_CACHE_SECONDS)
    cache.set(stale_key, result, timeout=KMA_WEEKLY_STALE_SECONDS)
    return result


def fetch_current_weather(lat=None, lon=None, region=None):
    auth_key = get_kma_api_hub_key()
    if not auth_key:
        raise WeatherServiceError("기상청 API허브 인증키가 설정되어 있지 않습니다.")

    location = resolve_location(lat=lat, lon=lon, region=region)
    grid = latlon_to_grid(location["lat"], location["lon"])
    base_date, base_time = current_kma_base_time()
    observation_cache_key = (
        f"myweather:kma:ncst:{base_date}:{base_time}:{grid['nx']}:{grid['ny']}"
    )

    params = {
        "authKey": auth_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"],
    }

    parsed = _cached_payload(observation_cache_key)
    observation_cache_status = "fresh"
    if parsed is None:
        stale_key = f"myweather:kma:ncst:stale:{grid['nx']}:{grid['ny']}"
        try:
            payload = _request_kma_json(get_current_weather_url(), params)
            parsed = parse_kma_items(_validate_kma_payload(payload))
            parsed["_observation_base_date"] = base_date
            parsed["_observation_base_time"] = base_time
            cache.set(observation_cache_key, parsed, timeout=KMA_CACHE_SECONDS)
            cache.set(stale_key, parsed, timeout=KMA_STALE_CACHE_SECONDS)
            observation_cache_status = "miss"
        except WeatherServiceError:
            parsed = _cached_payload(stale_key)
            if parsed is None:
                raise
            observation_cache_status = "stale"
    observation_base_date = parsed.pop("_observation_base_date", base_date)
    observation_base_time = parsed.pop("_observation_base_time", base_time)
    sky_forecast = fetch_sky_forecast(auth_key, grid)
    weekly_forecast = fetch_weekly_forecast(auth_key, grid, location)
    weather_alerts = fetch_weather_warnings(location)
    uv_index = fetch_uv_index(location)
    if sky_forecast.get("condition"):
        parsed["condition"] = sky_forecast["condition"]
    if sky_forecast:
        parsed["sky"] = sky_forecast.get("sky", "")
        parsed["sky_code"] = sky_forecast.get("sky_code")
        parsed["forecast_precipitation_type"] = sky_forecast.get("forecast_precipitation_type")
        parsed["forecast_rainfall_1h"] = sky_forecast.get("forecast_rainfall_1h")
        parsed["rainfall_1h"] = merge_forecast_rainfall(parsed.get("rainfall_1h"), sky_forecast)
        parsed["forecast_time"] = sky_forecast.get("forecast_time")
        parsed["forecast_base_date"] = sky_forecast.get("forecast_base_date")
        parsed["forecast_base_time"] = sky_forecast.get("forecast_base_time")
        parsed["raw_forecast_categories"] = sky_forecast.get("raw_forecast_categories", {})
        parsed["hourly_forecasts"] = sky_forecast.get("hourly_forecasts", [])

    parsed["weekly_forecasts"] = weekly_forecast.get("days", [])
    parsed["weekly_forecast_meta"] = {
        "cache_status": weekly_forecast.get("cache_status", "unavailable"),
        "coverage_days": len(weekly_forecast.get("days", [])),
        "missing_services": weekly_forecast.get("errors", []),
        "short_base_date": weekly_forecast.get("short_base_date"),
        "short_base_time": weekly_forecast.get("short_base_time"),
        "mid_base_time": weekly_forecast.get("mid_base_time"),
    }

    return {
        "provider": "KMA API Hub",
        "source": (
            "APIHub/VilageFcstInfoService_2.0/"
            "getUltraSrtNcst+getUltraSrtFcst+getVilageFcst;"
            "MidFcstInfoService/getMidTa+getMidLandFcst;wrn_now_data"
        ),
        "base_date": observation_base_date,
        "base_time": observation_base_time,
        "location": {
            **location,
            **grid,
        },
        "api_meta": {
            "observation_cache": observation_cache_status,
            "forecast_cache": sky_forecast.get("cache_status", "unavailable"),
            "weekly_forecast_cache": weekly_forecast.get("cache_status", "unavailable"),
            "warning_cache": weather_alerts.get("cache_status", "unavailable"),
            "uv_index_cache": uv_index.get("cache_status", "unavailable"),
            "cache_seconds": KMA_CACHE_SECONDS,
        },
        "weather_alerts": weather_alerts,
        "uv_index": uv_index,
        **parsed,
    }

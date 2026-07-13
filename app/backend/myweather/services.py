import math
import os
from datetime import timedelta
from urllib.parse import unquote

import requests
from django.utils import timezone


KMA_SERVICE_ENDPOINT = os.environ.get(
    "KMA_SERVICE_ENDPOINT",
    os.environ.get(
        "KMA_CURRENT_WEATHER_URL",
        "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0",
    ),
)
KMA_CURRENT_WEATHER_OPERATION = "getUltraSrtNcst"
KMA_ULTRA_SHORT_FORECAST_OPERATION = "getUltraSrtFcst"

DEFAULT_LOCATION = {
    "name": "서울",
    "lat": 37.5665,
    "lon": 126.9780,
}

KNOWN_LOCATIONS = {
    "서울": DEFAULT_LOCATION,
    "서울특별시": DEFAULT_LOCATION,
    "부산": {"name": "부산", "lat": 35.1796, "lon": 129.0756},
    "부산광역시": {"name": "부산", "lat": 35.1796, "lon": 129.0756},
    "대구": {"name": "대구", "lat": 35.8714, "lon": 128.6014},
    "대구광역시": {"name": "대구", "lat": 35.8714, "lon": 128.6014},
    "인천": {"name": "인천", "lat": 37.4563, "lon": 126.7052},
    "인천광역시": {"name": "인천", "lat": 37.4563, "lon": 126.7052},
    "광주": {"name": "광주", "lat": 35.1595, "lon": 126.8526},
    "광주광역시": {"name": "광주", "lat": 35.1595, "lon": 126.8526},
    "대전": {"name": "대전", "lat": 36.3504, "lon": 127.3845},
    "대전광역시": {"name": "대전", "lat": 36.3504, "lon": 127.3845},
    "울산": {"name": "울산", "lat": 35.5384, "lon": 129.3114},
    "울산광역시": {"name": "울산", "lat": 35.5384, "lon": 129.3114},
    "세종": {"name": "세종", "lat": 36.4800, "lon": 127.2890},
    "세종특별자치시": {"name": "세종", "lat": 36.4800, "lon": 127.2890},
    "경기": {"name": "경기", "lat": 37.2636, "lon": 127.0286},
    "경기도": {"name": "경기", "lat": 37.2636, "lon": 127.0286},
    "강원": {"name": "강원", "lat": 37.8813, "lon": 127.7298},
    "강원특별자치도": {"name": "강원", "lat": 37.8813, "lon": 127.7298},
    "충북": {"name": "충북", "lat": 36.6357, "lon": 127.4917},
    "충청북도": {"name": "충북", "lat": 36.6357, "lon": 127.4917},
    "충남": {"name": "충남", "lat": 36.6588, "lon": 126.6728},
    "충청남도": {"name": "충남", "lat": 36.6588, "lon": 126.6728},
    "전북": {"name": "전북", "lat": 35.8242, "lon": 127.1480},
    "전북특별자치도": {"name": "전북", "lat": 35.8242, "lon": 127.1480},
    "전남": {"name": "전남", "lat": 34.8161, "lon": 126.4629},
    "전라남도": {"name": "전남", "lat": 34.8161, "lon": 126.4629},
    "경북": {"name": "경북", "lat": 36.5684, "lon": 128.7294},
    "경상북도": {"name": "경북", "lat": 36.5684, "lon": 128.7294},
    "경남": {"name": "경남", "lat": 35.2279, "lon": 128.6816},
    "경상남도": {"name": "경남", "lat": 35.2279, "lon": 128.6816},
    "제주": {"name": "제주", "lat": 33.4996, "lon": 126.5312},
    "제주특별자치도": {"name": "제주", "lat": 33.4996, "lon": 126.5312},
}

PTY_LABELS = {
    "0": "맑음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "약한 비",
    "6": "약한 비/눈",
    "7": "약한 눈",
}

SKY_LABELS = {
    "1": "맑음",
    "3": "구름많음",
    "4": "흐림",
}

CATEGORY_MAP = {
    "T1H": ("temperature", "기온", "℃"),
    "RN1": ("rainfall_1h", "1시간 강수량", "mm"),
    "UUU": ("east_west_wind", "동서바람성분", "m/s"),
    "VVV": ("north_south_wind", "남북바람성분", "m/s"),
    "REH": ("humidity", "습도", "%"),
    "PTY": ("precipitation_type", "강수형태", ""),
    "VEC": ("wind_direction", "풍향", "deg"),
    "WSD": ("wind_speed", "풍속", "m/s"),
}


class WeatherServiceError(Exception):
    pass


class WeatherInputError(WeatherServiceError):
    pass


def get_kma_api_key():
    key = (
        os.environ.get("KMA_API_KEY")
        or os.environ.get("KOREA_WEATHER_API_KEY")
        or os.environ.get("KMA_SERVICE_KEY")
        or ""
    ).strip()
    return unquote(key)


def get_current_weather_url():
    endpoint = KMA_SERVICE_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_CURRENT_WEATHER_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_CURRENT_WEATHER_OPERATION}"


def get_ultra_short_forecast_url():
    endpoint = KMA_SERVICE_ENDPOINT.rstrip("/")
    if endpoint.endswith(f"/{KMA_ULTRA_SHORT_FORECAST_OPERATION}"):
        return endpoint
    return f"{endpoint}/{KMA_ULTRA_SHORT_FORECAST_OPERATION}"


def resolve_location(lat=None, lon=None, region=None):
    if (lat is None) != (lon is None):
        raise WeatherInputError("lat/lon은 함께 전달해야 합니다.")

    if lat is not None and lon is not None:
        return {
            "name": region or "현재 위치",
            "lat": float(lat),
            "lon": float(lon),
        }

    if region:
        key = str(region).strip()
        if key in KNOWN_LOCATIONS:
            return KNOWN_LOCATIONS[key]
        raise WeatherInputError(f"지원하지 않는 지역입니다: {key}")

    return DEFAULT_LOCATION


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


def normalize_obsr_value(value):
    if value in (None, "", "-", "null"):
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
    if value in (None, "", "-", "null"):
        return None
    return str(value)


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

    now_key = timezone.localtime().strftime("%Y%m%d%H%M")
    selected_key = min(forecasts_by_time.keys(), key=lambda key: abs(int(key) - int(now_key)))
    selected = forecasts_by_time[selected_key]
    pty_value = selected.get("PTY") or "0"
    sky_value = selected.get("SKY")
    has_precipitation = str(pty_value) not in {"0", "None", ""}
    condition = PTY_LABELS.get(str(pty_value)) if has_precipitation else SKY_LABELS.get(str(sky_value))

    hourly_forecasts = []
    # Pick every other hour or just first 5 to make it "not too dense"
    sorted_keys = sorted(forecasts_by_time.keys())
    for key in sorted_keys:
        data = forecasts_by_time[key]
        pty = data.get("PTY") or "0"
        sky = data.get("SKY")
        cond = PTY_LABELS.get(str(pty)) if str(pty) not in {"0", "None", ""} else SKY_LABELS.get(str(sky), "알 수 없음")
        
        hourly_forecasts.append({
            "time": f"{key[8:10]}시",
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
        "forecast_time": {
            "date": selected_key[:8],
            "time": selected_key[8:12],
        },
        "raw_forecast_categories": selected,
        "hourly_forecasts": hourly_forecasts,
    }


def fetch_sky_forecast(api_key, grid):
    base_date, base_time = ultra_short_forecast_base_time()
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"],
    }

    try:
        response = requests.get(get_ultra_short_forecast_url(), params=params, timeout=8)
        if response.status_code >= 400:
            return {}
        payload = response.json()
    except (requests.RequestException, ValueError):
        return {}

    header = payload.get("response", {}).get("header", {})
    result_code = header.get("resultCode")
    if result_code not in ("00", "0"):
        return {}

    items = (
        payload.get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )
    parsed = parse_ultra_short_forecast_items(items)
    if not parsed:
        return {}
    parsed["forecast_base_date"] = base_date
    parsed["forecast_base_time"] = base_time
    return parsed


def fetch_current_weather(lat=None, lon=None, region=None):
    api_key = get_kma_api_key()
    if not api_key:
        raise WeatherServiceError("기상청 API 키가 설정되어 있지 않습니다.")

    location = resolve_location(lat=lat, lon=lon, region=region)
    grid = latlon_to_grid(location["lat"], location["lon"])
    base_date, base_time = current_kma_base_time()

    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": grid["nx"],
        "ny": grid["ny"],
    }

    try:
        response = requests.get(get_current_weather_url(), params=params, timeout=8)
        if response.status_code >= 400:
            raise WeatherServiceError(f"기상청 API 호출에 실패했습니다: HTTP {response.status_code}")
        payload = response.json()
    except requests.RequestException as exc:
        raise WeatherServiceError(f"기상청 API 호출에 실패했습니다: {exc.__class__.__name__}") from exc
    except ValueError as exc:
        raise WeatherServiceError("기상청 API 응답을 JSON으로 해석하지 못했습니다.") from exc

    header = payload.get("response", {}).get("header", {})
    result_code = header.get("resultCode")
    if result_code not in ("00", "0"):
        message = header.get("resultMsg") or "기상청 API 오류"
        raise WeatherServiceError(f"{message} ({result_code})")

    items = (
        payload.get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )
    parsed = parse_kma_items(items)
    sky_forecast = fetch_sky_forecast(api_key, grid)
    if sky_forecast.get("condition"):
        parsed["condition"] = sky_forecast["condition"]
    if sky_forecast:
        parsed["sky"] = sky_forecast.get("sky", "")
        parsed["sky_code"] = sky_forecast.get("sky_code")
        parsed["forecast_precipitation_type"] = sky_forecast.get("forecast_precipitation_type")
        parsed["forecast_time"] = sky_forecast.get("forecast_time")
        parsed["forecast_base_date"] = sky_forecast.get("forecast_base_date")
        parsed["forecast_base_time"] = sky_forecast.get("forecast_base_time")
        parsed["raw_forecast_categories"] = sky_forecast.get("raw_forecast_categories", {})
        parsed["hourly_forecasts"] = sky_forecast.get("hourly_forecasts", [])

    return {
        "provider": "KMA",
        "source": "VilageFcstInfoService_2.0/getUltraSrtNcst+getUltraSrtFcst",
        "base_date": base_date,
        "base_time": base_time,
        "location": {
            **location,
            **grid,
        },
        **parsed,
    }

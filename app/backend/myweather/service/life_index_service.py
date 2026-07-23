import os
import time
import xml.etree.ElementTree as ET
from datetime import timedelta
from urllib.parse import unquote

import requests
from django.core.cache import cache
from django.utils import timezone

from myweather.constants import (
    KMA_LIFE_INDEX_AREA_CODES,
    KMA_RETRYABLE_STATUS_CODES,
)


KMA_UV_INDEX_ENDPOINT = os.environ.get(
    "KMA_UV_INDEX_ENDPOINT",
    "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV5/getUVIdxV5",
)
KMA_LIFE_INDEX_CACHE_SECONDS = max(
    300,
    int(os.environ.get("KMA_LIFE_INDEX_CACHE_SECONDS", "3600")),
)
KMA_LIFE_INDEX_STALE_SECONDS = max(
    KMA_LIFE_INDEX_CACHE_SECONDS,
    int(os.environ.get("KMA_LIFE_INDEX_STALE_SECONDS", "21600")),
)
KMA_LIFE_INDEX_TIMEOUT_SECONDS = max(
    3,
    int(os.environ.get("KMA_LIFE_INDEX_TIMEOUT_SECONDS", "8")),
)
KMA_LIFE_INDEX_RETRY_COUNT = max(
    0,
    int(os.environ.get("KMA_LIFE_INDEX_RETRY_COUNT", "1")),
)
KMA_UV_INDEX_SOURCE_URL = "https://www.weather.go.kr/w/forecast/life/index-info.do"


class LifeIndexConfigurationError(Exception):
    """인증·활용신청 문제처럼 다른 발표시각 재조회로 해결되지 않는 오류."""


def get_kma_life_index_service_key():
    """생활기상지수 V5 활용신청을 완료한 공공데이터포털 키를 반환한다."""
    return (
        os.environ.get("KMA_LIFE_INDEX_SERVICE_KEY")
        or os.environ.get("KMA_API_KEY")
        or ""
    ).strip()


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _parse_json_items(payload):
    response = payload.get("response") or {}
    header = response.get("header") or {}
    result_code = str(header.get("resultCode") or header.get("resultcode") or "")
    if result_code and result_code not in {"00", "0000"}:
        raise ValueError(header.get("resultMsg") or header.get("resultmsg") or result_code)
    body = response.get("body") or {}
    items = body.get("items") or {}
    if isinstance(items, dict):
        items = items.get("item")
    return [item for item in _as_list(items) if isinstance(item, dict)]


def _parse_xml_items(content):
    root = ET.fromstring(content)
    result_code = root.findtext(".//resultCode", default="")
    if result_code and result_code not in {"00", "0000"}:
        raise ValueError(root.findtext(".//resultMsg", default=result_code))
    return [
        {child.tag: child.text for child in node}
        for node in root.findall(".//item")
    ]


def _response_items(response):
    try:
        payload = response.json()
    except (requests.exceptions.JSONDecodeError, TypeError, AttributeError):
        return _parse_xml_items(response.content)
    return _parse_json_items(payload)


def _official_uv_value(items, area_no):
    normalized = [
        {str(key).lower(): value for key, value in item.items()}
        for item in items
    ]
    candidates = [
        item
        for item in normalized
        if not item.get("areano") or str(item.get("areano")) == area_no
    ]
    for item in candidates:
        # V5의 현재 발표시각 값은 h0이다. today는 구버전 호환 응답에만 사용한다.
        for field in ("h0", "today"):
            try:
                value = float(item.get(field))
            except (TypeError, ValueError):
                continue
            # 11 이상은 모두 공식 '위험' 단계이며 드물게 15를 넘는 발표값도 보존한다.
            if 0 <= value <= 50:
                return round(value, 1), item
    raise ValueError("기상청 응답에 현재 자외선지수 값이 없습니다.")


def _unavailable(status):
    return {
        "status": status,
        "value": None,
        "provider": "기상청 생활기상지수 V5",
        "source_url": KMA_UV_INDEX_SOURCE_URL,
        "cache_status": "unavailable",
        "stale": False,
    }


def _request_uv_index(service_key, area_no, announced_at):
    params = {
        # 인코딩 키를 requests params에 넣기 전 복원해 '%' 이중 인코딩을 방지한다.
        "ServiceKey": unquote(service_key),
        "pageNo": 1,
        "numOfRows": 10,
        "dataType": "JSON",
        "areaNo": area_no,
        "time": announced_at,
    }
    last_error = None
    for attempt in range(KMA_LIFE_INDEX_RETRY_COUNT + 1):
        try:
            response = requests.get(
                KMA_UV_INDEX_ENDPOINT,
                params=params,
                timeout=KMA_LIFE_INDEX_TIMEOUT_SECONDS,
            )
            if response.status_code in {401, 403}:
                raise LifeIndexConfigurationError(
                    "생활기상지수 V5 활용신청 또는 인증키 확인이 필요합니다."
                )
            if (
                response.status_code in KMA_RETRYABLE_STATUS_CODES
                and attempt < KMA_LIFE_INDEX_RETRY_COUNT
            ):
                time.sleep(0.25 * (2 ** attempt))
                continue
            response.raise_for_status()
            value, item = _official_uv_value(_response_items(response), area_no)
            return {
                "status": "available",
                "value": value,
                "area_no": area_no,
                "announced_at": str(item.get("date") or announced_at),
                "provider": "기상청 생활기상지수 V5",
                "source_url": KMA_UV_INDEX_SOURCE_URL,
                "cache_status": "miss",
                "stale": False,
            }
        except LifeIndexConfigurationError:
            raise
        except ValueError:
            # 정상 응답이지만 해당 발표시각 자료가 없으면 호출자가 이전 발표시각을 조회한다.
            raise
        except (requests.RequestException, ET.ParseError) as exc:
            last_error = exc
            if attempt < KMA_LIFE_INDEX_RETRY_COUNT:
                time.sleep(0.25 * (2 ** attempt))
    raise last_error or ValueError("기상청 자외선지수 응답을 처리하지 못했습니다.")


def fetch_uv_index(location):
    """기상청이 발표한 현재 시점의 자외선지수를 조회한다."""
    service_key = get_kma_life_index_service_key()
    if not service_key:
        return _unavailable("unconfigured")

    region_name = str(location.get("name") or "").strip()
    area_no = KMA_LIFE_INDEX_AREA_CODES.get(region_name)
    if not area_no:
        return _unavailable("region_unmapped")

    cache_key = f"myweather:kma-life:uv:{area_no}"
    stale_key = f"myweather:kma-life:uv:stale:{area_no}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {**cached, "cache_status": "fresh"}

    now = timezone.localtime()
    release = now.replace(hour=(now.hour // 3) * 3, minute=0, second=0, microsecond=0)
    failure_status = "request_failed"
    try:
        # 생산 지연을 고려하되, 오래된 값을 새 값처럼 만들지 않도록 최대 6시간만 확인한다.
        for offset_hours in (0, 3, 6):
            announced_at = (release - timedelta(hours=offset_hours)).strftime("%Y%m%d%H")
            try:
                result = _request_uv_index(service_key, area_no, announced_at)
                cache.set(cache_key, result, timeout=KMA_LIFE_INDEX_CACHE_SECONDS)
                cache.set(stale_key, result, timeout=KMA_LIFE_INDEX_STALE_SECONDS)
                return result
            except LifeIndexConfigurationError:
                failure_status = "authorization_failed"
                break
            except ValueError:
                # 생산 지연으로 최신 발표시각 자료만 비어 있을 때에만 이전 시각을 확인한다.
                continue
            except (requests.RequestException, ET.ParseError):
                # 연결·응답 형식 장애는 발표시각을 바꿔도 해결되지 않으므로 중복 대기를 막는다.
                break
    except (TypeError, OverflowError, ValueError):
        pass

    stale = cache.get(stale_key)
    if stale is not None:
        return {**stale, "cache_status": "stale", "stale": True}
    return _unavailable(failure_status)

import math
import os
from collections.abc import Mapping, Sequence

from myweather.constants import DEFAULT_LOCATION as STATIC_DEFAULT_LOCATION
from myweather.constants import (
    STATIC_DEFAULT_KNOWN_LOCATIONS,
    STATIC_DEFAULT_MID_FORECAST_REGIONS,
    STATIC_DEFAULT_WARNING_REGION_ALIASES,
    STATIC_DEFAULT_WARNING_REGION_CODE_PREFIXES,
    STATIC_DEFAULT_WARNING_REGION_DISPLAY_NAMES,
    STATIC_DEFAULT_WEATHER_REPRESENTATIVE_NAMES,
)

from .exceptions import WeatherInputError


_db_regions_cache = None


def clear_db_regions_cache():
    """DB 지역 설정 캐시를 비운다."""
    global _db_regions_cache
    _db_regions_cache = None


def _load_db_regions():
    """DB 설정을 읽고, DB 사용 불가 시 정적 기본값으로 안전하게 대체한다."""
    global _db_regions_cache
    if _db_regions_cache is not None:
        return _db_regions_cache

    from myweather.models import WeatherRegion

    try:
        regions = list(WeatherRegion.objects.all())
    except Exception:
        regions = []

    if not regions:
        _db_regions_cache = (
            STATIC_DEFAULT_KNOWN_LOCATIONS,
            STATIC_DEFAULT_WEATHER_REPRESENTATIVE_NAMES,
            STATIC_DEFAULT_WARNING_REGION_ALIASES,
            STATIC_DEFAULT_WARNING_REGION_CODE_PREFIXES,
            STATIC_DEFAULT_WARNING_REGION_DISPLAY_NAMES,
            STATIC_DEFAULT_MID_FORECAST_REGIONS,
        )
        return _db_regions_cache

    known_locations = {}
    representative_names = []
    warning_aliases = {}
    warning_prefixes = {}
    warning_display_names = {}
    mid_forecast_regions = {}

    for region in regions:
        location = {"name": region.name, "lat": region.lat, "lon": region.lon}
        known_locations[region.name] = location
        for alias in region.aliases:
            known_locations[alias] = location

        representative_names.append(region.name)
        warning_aliases[region.name] = tuple([region.name, *region.aliases])
        warning_prefixes[region.name] = tuple(region.warning_code_prefixes)
        warning_display_names[region.name] = region.warning_display_name or region.name

        forecast_codes = {
            "land": region.mid_land_code,
            "temperature": region.mid_temp_code,
        }
        mid_forecast_regions[region.name] = forecast_codes
        for alias in region.aliases:
            mid_forecast_regions[alias] = forecast_codes

    _db_regions_cache = (
        known_locations,
        tuple(representative_names),
        warning_aliases,
        warning_prefixes,
        warning_display_names,
        mid_forecast_regions,
    )
    return _db_regions_cache


class DynamicDict(Mapping):
    """DB 캐시의 사전 항목을 기존 전역 상수처럼 노출하는 읽기 전용 뷰."""

    def __init__(self, index):
        self.index = index

    def _data(self):
        return _load_db_regions()[self.index]

    def __getitem__(self, key):
        return self._data()[key]

    def __iter__(self):
        return iter(self._data())

    def __len__(self):
        return len(self._data())


class DynamicTuple(Sequence):
    """DB 캐시의 튜플 항목을 기존 전역 상수처럼 노출하는 읽기 전용 뷰."""

    def __init__(self, index):
        self.index = index

    def _data(self):
        return _load_db_regions()[self.index]

    def __getitem__(self, index):
        return self._data()[index]

    def __len__(self):
        return len(self._data())


class DynamicDefaultLocation(Mapping):
    """환경변수와 DB 설정을 반영하는 기본 지역 읽기 전용 뷰."""

    def _data(self):
        default_name = os.environ.get("DEFAULT_WEATHER_REGION_NAME", "서울").strip()
        try:
            from myweather.models import WeatherRegion

            region = WeatherRegion.objects.filter(name=default_name).first()
            if region:
                return {"name": region.name, "lat": region.lat, "lon": region.lon}
        except Exception:
            pass
        return STATIC_DEFAULT_KNOWN_LOCATIONS.get(default_name) or STATIC_DEFAULT_LOCATION

    def __getitem__(self, key):
        return self._data()[key]

    def __iter__(self):
        return iter(self._data())

    def __len__(self):
        return len(self._data())

    def __str__(self):
        return str(self._data())

    def __repr__(self):
        return repr(self._data())


DEFAULT_LOCATION = DynamicDefaultLocation()
KNOWN_LOCATIONS = DynamicDict(0)
WEATHER_REPRESENTATIVE_NAMES = DynamicTuple(1)
WARNING_REGION_ALIASES = DynamicDict(2)
WARNING_REGION_CODE_PREFIXES = DynamicDict(3)
WARNING_REGION_DISPLAY_NAMES = DynamicDict(4)
MID_FORECAST_REGIONS = DynamicDict(5)


def nearest_weather_region_name(latitude, longitude):
    latitude = float(latitude)
    longitude = float(longitude)

    def distance_squared(candidate_name):
        candidate = KNOWN_LOCATIONS[candidate_name]
        latitude_delta = latitude - candidate["lat"]
        longitude_delta = (longitude - candidate["lon"]) * math.cos(math.radians(latitude))
        return latitude_delta ** 2 + longitude_delta ** 2

    return min(WEATHER_REPRESENTATIVE_NAMES, key=distance_squared)


def resolve_location(lat=None, lon=None, region=None):
    """좌표 또는 지역명을 지원 지역 데이터로 정규화한다."""
    if (lat is None) != (lon is None):
        raise WeatherInputError("lat/lon은 함께 전달해야 합니다.")

    if lat is not None and lon is not None:
        latitude = float(lat)
        longitude = float(lon)
        requested_name = str(region or "").strip()
        resolved_name = (
            requested_name
            if requested_name and requested_name != "현재 위치"
            else nearest_weather_region_name(latitude, longitude)
        )
        return {
            "name": resolved_name,
            "lat": latitude,
            "lon": longitude,
            "is_current_location": True,
            "location_resolution": "nearest_supported_region",
        }

    if region:
        key = str(region).strip()
        if key in KNOWN_LOCATIONS:
            return KNOWN_LOCATIONS[key]
        raise WeatherInputError(f"지원하지 않는 지역입니다: {key}")

    return dict(DEFAULT_LOCATION)


def resolve_mid_forecast_codes(location):
    location_name = str(location.get("name") or "").strip()
    codes = MID_FORECAST_REGIONS.get(location_name)
    if codes:
        return codes

    latitude = float(location.get("lat", DEFAULT_LOCATION["lat"]))
    longitude = float(location.get("lon", DEFAULT_LOCATION["lon"]))
    return MID_FORECAST_REGIONS[nearest_weather_region_name(latitude, longitude)]

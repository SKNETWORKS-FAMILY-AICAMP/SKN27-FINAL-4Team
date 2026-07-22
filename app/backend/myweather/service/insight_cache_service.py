import hashlib
import json

from django.core.cache import cache

from myweather.constants import (
    WEATHER_HOBBY_ROTATION_CACHE_SECONDS,
    WEATHER_INSIGHT_ALERT_STATE_FIELDS,
    WEATHER_INSIGHT_FALLBACK_CACHE_SECONDS,
    WEATHER_INSIGHT_SUCCESS_CACHE_SECONDS,
    WEATHER_INSIGHT_WEEKLY_STATE_FIELDS,
)
from user.constants import WEATHER_INSIGHT_CACHE_VERSION


def _selected_values(item, fields):
    return tuple(item.get(field) for field in fields)


def select_weather_hobby(user_id, user_profile, *, rotate=False):
    """Keep one profile hobby selected, advancing only on an explicit refresh."""
    profile = dict(user_profile or {})
    hobbies = list(dict.fromkeys(
        str(value).strip()
        for value in profile.get("hobbies") or []
        if str(value).strip()
    ))
    if not hobbies:
        profile["hobbies"] = []
        profile["selected_hobby"] = ""
        return profile

    cache_key = f"weather_hobby_rotation_v1_{user_id}"
    previous = str(cache.get(cache_key) or "").strip()
    if previous not in hobbies:
        selected = hobbies[0]
    elif rotate and len(hobbies) > 1:
        selected = hobbies[(hobbies.index(previous) + 1) % len(hobbies)]
    else:
        selected = previous

    cache.set(
        cache_key,
        selected,
        timeout=WEATHER_HOBBY_ROTATION_CACHE_SECONDS,
    )
    profile["hobbies"] = [selected]
    profile["selected_hobby"] = selected
    return profile


def build_weather_insight_cache_key(weather, user_id, user_profile):
    """개인화 결과에 실제로 영향을 주는 값만 안정적으로 해시한다."""
    cache_state = {
        "version": WEATHER_INSIGHT_CACHE_VERSION,
        "user_id": user_id,
        "base_date": weather.get("base_date"),
        "base_time": weather.get("base_time"),
        "location_name": weather.get("location", {}).get("name"),
        "condition": weather.get("condition"),
        "temperature": weather.get("temperature"),
        "uv_index": weather.get("uv_index", {}).get("value"),
        "weekly_forecasts": [
            _selected_values(item, WEATHER_INSIGHT_WEEKLY_STATE_FIELDS)
            for item in weather.get("weekly_forecasts", [])
        ],
        "weather_alert_status": weather.get("weather_alerts", {}).get("status"),
        "weather_alerts": [
            _selected_values(item, WEATHER_INSIGHT_ALERT_STATE_FIELDS)
            for item in weather.get("weather_alerts", {}).get("items", [])
        ],
        "emotion": user_profile.get("today_emotion"),
        "hobbies": user_profile.get("hobbies"),
    }
    serialized = json.dumps(cache_state, sort_keys=True)
    digest = hashlib.md5(serialized.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"weather_insight_{digest}"


def get_or_create_weather_insight(weather, user_id, user_profile, analyzer):
    """분석 캐시를 조회하고 없을 때만 전달받은 분석기를 실행한다."""
    cache_key = build_weather_insight_cache_key(weather, user_id, user_profile)
    insight = cache.get(cache_key)
    if insight is not None:
        return insight, True

    insight = analyzer(weather, user_profile)
    timeout = (
        WEATHER_INSIGHT_FALLBACK_CACHE_SECONDS
        if insight.get("is_fallback")
        else WEATHER_INSIGHT_SUCCESS_CACHE_SECONDS
    )
    cache.set(cache_key, insight, timeout=timeout)
    return insight, False

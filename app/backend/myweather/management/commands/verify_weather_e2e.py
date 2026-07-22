from __future__ import annotations

import json

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from chat.models import ChatMessage, ChatSession
from myweather.models import WeatherPhrasingFilter, WeatherRegion
from myweather.service.insight_cache_service import (
    build_weather_insight_cache_key,
    select_weather_hobby,
)
from myweather.service.user_profile_service import build_weather_user_profile
from user.models import User, UserProfile


class Command(BaseCommand):
    help = "실제 기상청·Tavily·OpenAI를 사용하는 날씨 분석 전체 흐름을 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument("--email")
        parser.add_argument("--region", default="서울")

    def _emit(self, stage: str, payload) -> None:
        self.stdout.write(
            json.dumps(
                {"stage": stage, "payload": payload},
                ensure_ascii=False,
                default=str,
            )
        )

    @staticmethod
    def _require_status(response, expected: int, stage: str):
        payload = getattr(response, "data", None)
        if response.status_code != expected:
            raise CommandError(
                f"{stage} failed: HTTP {response.status_code} {payload!r}"
            )
        return payload

    @staticmethod
    def _stable_weather_snapshot(weather):
        """캐시 적중 상태처럼 재조회 때 정상적으로 바뀌는 메타데이터는 제외한다."""
        return {
            "provider": weather.get("provider"),
            "base_date": weather.get("base_date"),
            "base_time": weather.get("base_time"),
            "location": weather.get("location"),
            "condition": weather.get("condition"),
            "temperature": weather.get("temperature"),
            "humidity": weather.get("humidity"),
            "wind_speed": weather.get("wind_speed"),
            "rainfall_1h": weather.get("rainfall_1h"),
            "hourly_forecasts": weather.get("hourly_forecasts"),
            "weekly_forecasts": weather.get("weekly_forecasts"),
            "weather_alert_status": (weather.get("weather_alerts") or {}).get("status"),
            "weather_alert_items": (weather.get("weather_alerts") or {}).get("items"),
            "uv_index_value": (weather.get("uv_index") or {}).get("value"),
        }

    def handle(self, *args, **options):
        run_stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
        email = options.get("email") or f"codex.weather.e2e.{run_stamp}@example.com"
        region = str(options["region"]).strip()
        if User.objects.filter(email=email).exists():
            raise CommandError(f"이미 존재하는 테스트 이메일입니다: {email}")

        user = User.objects.create_user(
            email=email,
            password="CodexWeatherE2E!",
            nickname=f"날씨검증{run_stamp[-6:]}",
            character="pori",
            onboarding_done=True,
        )
        UserProfile.objects.create(
            user=user,
            age=31,
            gender="여성",
            interests=["환경", "여행"],
            hobbies=["산책", "사진 찍기"],
        )
        session = ChatSession.objects.create(
            user=user,
            character="pori",
            is_secret=False,
            cold_start_done=True,
        )
        for index, emotion in enumerate(("joy", "normal", "joy"), start=1):
            ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=f"날씨 분석 감정 검증 메시지 {index}",
                emotion_label=emotion,
            )

        profile = build_weather_user_profile(user)
        expected_profile = {
            "hobbies": ["산책", "사진 찍기"],
            "today_emotion": "기쁨",
        }
        if profile != expected_profile:
            raise CommandError(f"날씨 최소 프로필이 예상과 다릅니다: {profile!r}")
        self._emit(
            "dummy_data_and_profile_created",
            {
                "user_id": user.id,
                "email": email,
                "requested_region": region,
                "stored_profile": {
                    "age": 31,
                    "gender": "여성",
                    "interests": ["환경", "여행"],
                    "hobbies": ["산책", "사진 찍기"],
                },
                "weather_personalization_profile": profile,
                "assistant_emotions": ["joy", "normal", "joy"],
            },
        )

        client = APIClient()
        client.force_authenticate(user=user)
        regions = self._require_status(
            client.get("/api/myweather/regions/"), 200, "load_regions"
        )
        if region not in regions:
            raise CommandError(f"지원 지역 목록에 {region!r}이 없습니다.")
        self._emit(
            "regions_verified",
            {
                "selected": region,
                "count": len(regions),
                "regions": regions,
            },
        )

        before_counts = {
            "weather_regions": WeatherRegion.objects.count(),
            "weather_phrasing_filters": WeatherPhrasingFilter.objects.count(),
        }
        generated = self._require_status(
            client.get("/api/myweather/current/", {"region": region}),
            200,
            "generate_weather_analysis",
        )
        weather = generated.get("weather") or {}
        insight = generated.get("insight") or {}

        required_weather_fields = (
            "provider",
            "base_date",
            "base_time",
            "condition",
            "temperature",
            "humidity",
            "wind_speed",
            "location",
        )
        missing_weather = [field for field in required_weather_fields if weather.get(field) is None]
        if missing_weather:
            raise CommandError(f"필수 날씨 필드가 누락됐습니다: {missing_weather!r}")
        if weather.get("provider") != "KMA API Hub":
            raise CommandError(f"예상하지 못한 날씨 제공처입니다: {weather.get('provider')!r}")
        if (weather.get("location") or {}).get("name") != region:
            raise CommandError(f"요청 지역과 응답 지역이 다릅니다: {weather.get('location')!r}")

        generation = insight.get("generation") or {}
        if generation.get("status") != "generated":
            raise CommandError(f"OpenAI 해설 생성이 폴백되었습니다: {generation!r}")
        recommendations = insight.get("recommendations") or []
        if len(recommendations) != 3:
            raise CommandError(f"활동 추천이 정확히 3개가 아닙니다: {recommendations!r}")
        if not str(insight.get("weatherAnalysis") or "").strip():
            raise CommandError("날씨 해설이 비어 있습니다.")
        if not str(insight.get("forecastSummary") or "").strip():
            raise CommandError("주간예보 요약이 비어 있습니다.")

        selected_profile = select_weather_hobby(user.id, profile)
        insight_cache_key = build_weather_insight_cache_key(
            weather,
            user.id,
            selected_profile,
        )
        if cache.get(insight_cache_key) is None:
            raise CommandError("생성된 날씨 해설이 서비스 캐시에 저장되지 않았습니다.")

        self._emit(
            "weather_analysis_generated",
            {
                "weather": weather,
                "insight": insight,
                "attributions": generated.get("attributions"),
                "processing_notice": generated.get("processing_notice"),
                "methodology": generated.get("methodology"),
                "api_limits": generated.get("api_limits"),
                "insight_cache_key": insight_cache_key,
            },
        )

        cached = self._require_status(
            client.get("/api/myweather/current/", {"region": region}),
            200,
            "load_cached_weather_analysis",
        )
        if cached.get("insight") != insight:
            raise CommandError("최초 생성 해설과 두 번째 캐시 해설이 다릅니다.")
        cached_weather = cached.get("weather") or {}
        if self._stable_weather_snapshot(cached_weather) != self._stable_weather_snapshot(weather):
            raise CommandError("최초 핵심 날씨 원자료와 두 번째 조회 결과가 다릅니다.")

        rotated = self._require_status(
            client.get(
                "/api/myweather/current/",
                {"region": region, "rotate_hobby": "true"},
            ),
            200,
            "rotate_weather_hobby_recommendation",
        )
        rotated_generation = (rotated.get("insight") or {}).get("generation") or {}
        if generation.get("selected_hobby") != "산책":
            raise CommandError(f"최초 선택 취미가 예상과 다릅니다: {generation!r}")
        if rotated_generation.get("selected_hobby") != "사진 찍기":
            raise CommandError(f"새로고침 후 취미가 순환하지 않았습니다: {rotated_generation!r}")

        after_counts = {
            "weather_regions": WeatherRegion.objects.count(),
            "weather_phrasing_filters": WeatherPhrasingFilter.objects.count(),
        }
        if after_counts != before_counts:
            raise CommandError(
                f"조회 과정에서 날씨 기준 DB가 변경됐습니다: {before_counts!r} -> {after_counts!r}"
            )
        self._emit(
            "cache_and_storage_policy_verified",
            {
                "same_weather": True,
                "same_insight": True,
                "insight_cache_present": True,
                "hobby_rotation": [
                    generation.get("selected_hobby"),
                    rotated_generation.get("selected_hobby"),
                ],
                "first_api_cache_status": weather.get("api_meta"),
                "second_api_cache_status": cached_weather.get("api_meta"),
                "weather_result_persisted_to_database": False,
                "database_policy": "지역 목록·문구 필터만 영구 저장하고 조회 결과는 캐시에만 저장",
                "database_counts_before": before_counts,
                "database_counts_after": after_counts,
            },
        )

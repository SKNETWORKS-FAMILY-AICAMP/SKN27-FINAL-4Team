from datetime import date

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
    age = getattr(profile, "age", None) if profile else None
    birth_date = getattr(profile, "birth_date", None) if profile else None
    if age is None and birth_date:
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        
    mbti = ""
    try:
        from mbti.models import MbtiMonthlyResultRecord, MbtiOnboardingProfile
        latest_mbti = MbtiMonthlyResultRecord.objects.filter(
            user_id=user.id,
            estimated_mbti_type__isnull=False
        ).exclude(estimated_mbti_type="").order_by('-period_key').first()
        
        if latest_mbti:
            mbti = latest_mbti.estimated_mbti_type
        else:
            onboarding = MbtiOnboardingProfile.objects.filter(
                user_id=user.id, 
                mbti_type__isnull=False
            ).exclude(mbti_type="").first()
            if onboarding:
                mbti = onboarding.mbti_type
    except Exception as e:
        print(f"Failed to fetch MBTI: {e}")

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
        "age": age,
        "gender": getattr(profile, "gender", "") if profile else "",
        "hobbies": getattr(profile, "hobbies", []) if profile else [],
        "mbti": mbti,
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
        "version": 2, # Cache buster
        "user_id": request.user.id,
        "base_date": weather.get("base_date"),
        "base_time": weather.get("base_time"),
        "emotion": user_profile.get("today_emotion"),
        "hobbies": user_profile.get("hobbies"),
        "mbti": user_profile.get("mbti"),
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

    return Response({
        "weather": weather,
        "insight": insight,
    })

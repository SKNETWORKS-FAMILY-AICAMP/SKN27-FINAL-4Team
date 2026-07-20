import hashlib
import json

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication

from .agent import BookRecommendationAgent


EMOTION_LABELS_KO = {
    "joy": "기쁨",
    "sadness": "슬픔",
    "anger": "분노",
    "normal": "평온",
}


def _build_user_profile(user):
    profile = UserProfile.objects.filter(user=user).first()
    age = getattr(profile, "age", None) if profile else None
    birth_date = getattr(profile, "birth_date", None) if profile else None
    if age is None and birth_date:
        today = timezone.localdate()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )

    return {
        "age": age,
        "gender": getattr(profile, "gender", "") if profile else "",
        "interests": getattr(profile, "interests", []) if profile else [],
        "hobbies": getattr(profile, "hobbies", []) if profile else [],
        "today_emotion": _get_today_dominant_emotion(user),
    }


def _get_today_dominant_emotion(user):
    try:
        from chat.models import ChatMessage

        today = timezone.localdate()
        emotion_counts = (
            ChatMessage.objects.filter(
                session__user=user,
                role="assistant",
                emotion_label__isnull=False,
                created_at__date=today,
            )
            .exclude(emotion_label__in=["", "normal"])
            .values("emotion_label")
            .annotate(count=Count("emotion_label"))
            .order_by("-count", "-emotion_label")
        )
        if not emotion_counts.exists():
            return None

        raw_emotion = emotion_counts.first()["emotion_label"]
        return EMOTION_LABELS_KO.get(raw_emotion, raw_emotion)
    except Exception as exc:
        print(f"[BookAgent] Failed to fetch today's emotion: {exc}")
        return None


def _public_profile_basis(user_profile):
    return {
        "today_emotion": user_profile.get("today_emotion"),
        "interests": user_profile.get("interests"),
        "hobbies": user_profile.get("hobbies"),
    }


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def book_recommendation(request):
    force = request.query_params.get("force", "").lower() == "true"
    user_profile = _build_user_profile(request.user)

    today_str = timezone.localdate().isoformat()
    cache_state = {
        "version": 10,
        "user_id": request.user.id,
        "date": today_str,
        "age": user_profile.get("age"),
        "gender": user_profile.get("gender"),
        "emotion": user_profile.get("today_emotion"),
        "interests": user_profile.get("interests"),
        "hobbies": user_profile.get("hobbies"),
    }
    state_str = json.dumps(cache_state, ensure_ascii=False, sort_keys=True)
    cache_key = "book_recommendation_" + hashlib.md5(
        state_str.encode("utf-8")
    ).hexdigest()

    recommendation = cache.get(cache_key)
    is_cached = bool(recommendation) and not force

    if not is_cached:
        recommendation = BookRecommendationAgent.recommend(user_profile)
        cache.set(cache_key, recommendation, timeout=3600 * 24)

    return Response(
        {
            **recommendation,
            "is_cached": is_cached,
            "profile_basis": _public_profile_basis(user_profile),
            "content_date": today_str,
        }
    )

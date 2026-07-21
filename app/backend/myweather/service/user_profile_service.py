import logging

from django.db.models import Count
from django.utils import timezone

from myweather.constants import IGNORED_WEATHER_EMOTION_LABELS
from user.constants import EMOTION_LABELS_KO
from user.models import UserProfile


logger = logging.getLogger(__name__)


def build_weather_user_profile(user):
    """날씨 개인화에 허용된 최소 프로필만 구성한다."""
    profile = UserProfile.objects.filter(user=user).first()
    today_emotion = None
    try:
        from chat.models import ChatMessage

        emotion_counts = (
            ChatMessage.objects.filter(
                session__user=user,
                emotion_label__isnull=False,
                created_at__date=timezone.localdate(),
            )
            .exclude(emotion_label__in=IGNORED_WEATHER_EMOTION_LABELS)
            .values("emotion_label")
            .annotate(count=Count("emotion_label"))
            .order_by("-count")
        )
        most_common = emotion_counts.first()
        if most_common:
            raw_emotion = most_common["emotion_label"]
            today_emotion = EMOTION_LABELS_KO.get(raw_emotion, raw_emotion)
    except Exception:
        logger.exception("Failed to build weather user profile")

    return {
        "hobbies": getattr(profile, "hobbies", []) if profile else [],
        "today_emotion": today_emotion,
    }

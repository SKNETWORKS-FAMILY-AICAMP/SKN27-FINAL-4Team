from django.utils import timezone

from myprofile.emotion_service import build_today_emotion_summary
from user.models import UserProfile


def build_user_profile(user):
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
        "today_emotion": get_today_dominant_emotion(user),
    }


def get_today_dominant_emotion(user):
    """Return the recency-weighted dominant assistant emotion for today."""
    try:
        representative = build_today_emotion_summary(user)['representative']
        return representative['label'] if representative else None
    except Exception as exc:
        # Emotion is optional personalization data. Its failure must not stop books.
        print(f"[BookAgent] Failed to fetch today's emotion: {exc}")
        return None


def public_profile_basis(user_profile):
    return {
        "today_emotion": user_profile.get("today_emotion"),
        "interests": user_profile.get("interests"),
        "hobbies": user_profile.get("hobbies"),
    }

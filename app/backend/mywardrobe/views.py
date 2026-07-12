from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chat.models import ChatMessage, ChatSession
from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication

from .agent import WardrobeWebAgent, build_emotion_summary


def _age_group(age):
    try:
        value = int(age)
    except (TypeError, ValueError):
        return ""
    if value < 20:
        return "10대"
    if value < 30:
        return "20대"
    if value < 40:
        return "30대"
    if value < 50:
        return "40대"
    if value < 60:
        return "50대"
    return "60대 이상"


def _normalize_gender(gender):
    value = str(gender or "").strip()
    if value in {"남", "남성", "male", "M"}:
        return "남"
    if value in {"여", "여성", "female", "F"}:
        return "여"
    return "선택 안 함"


def _build_profile_context(user):
    profile = UserProfile.objects.filter(user=user).first()
    age = getattr(profile, "age", None) if profile else None
    return {
        "hobbies": getattr(profile, "hobbies", []) if profile else [],
        "interests": getattr(profile, "interests", []) if profile else [],
        "age": age,
        "ageGroup": _age_group(age),
        "gender": _normalize_gender(getattr(profile, "gender", "") if profile else ""),
    }


def _build_emotion_context(user):
    messages = list(
        ChatMessage.objects.filter(
            session__user=user,
            session__is_secret=False,
            role="user",
            emotion_label__isnull=False,
        )
        .exclude(emotion_label="")
        .order_by("-created_at")[:12]
    )
    latest_session = (
        ChatSession.objects.filter(user=user, is_secret=False, selected_emotion__isnull=False)
        .exclude(selected_emotion="")
        .order_by("-created_at")
        .first()
    )
    return build_emotion_summary(
        messages,
        selected_emotion=getattr(latest_session, "selected_emotion", None),
    )


def _build_recommendation_context(user):
    context = {}
    context.update(_build_profile_context(user))
    context.update(_build_emotion_context(user))
    return context


@api_view(["GET", "POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def wardrobe_recommendation(request):
    context = _build_recommendation_context(request.user)
    recommendation = WardrobeWebAgent.recommend(context)
    return Response({
        "context": {
            "emotion": context.get("emotion"),
            "emotionLabel": context.get("emotionLabel"),
            "recentEmotions": context.get("recentEmotions", []),
            "hobbies": context.get("hobbies", []),
            "interests": context.get("interests", []),
            "ageGroup": context.get("ageGroup") or "",
            "gender": context.get("gender") or "선택 안 함",
        },
        "recommendation": recommendation,
    })

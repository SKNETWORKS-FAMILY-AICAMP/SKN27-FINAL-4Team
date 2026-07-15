import hashlib
import json

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication

from .agent import BookRecommendationAgent, BookRecommendationUnavailable


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
        messages = (
            ChatMessage.objects.filter(
                session__user=user,
                role="assistant",
                emotion_label__isnull=False,
                created_at__date=today,
            )
            .exclude(emotion_label="")
            .order_by("created_at")
        )
        if not messages.exists():
            return None

        scores = {}
        total = messages.count()
        for index, msg in enumerate(messages):
            label = msg.emotion_label
            # 최신 메시지일수록 가중치를 크게 줌 (i가 0~total-1 일 때 w = (i+1)/total)
            weight = (index + 1) / total
            scores[label] = scores.get(label, 0.0) + weight

        raw_emotion = max(scores, key=scores.get)
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
    force_theme = request.query_params.get("theme", "").lower()
    if force_theme not in ["emotion", "interests", "hobbies"]:
        force_theme = None

    user_profile = _build_user_profile(request.user)

    today_str = timezone.localdate().isoformat()
    cache_state = {
        "version": 14,
        "user_id": request.user.id,
        "date": today_str,
        "emotion": user_profile.get("today_emotion"),
        "interests": user_profile.get("interests"),
        "hobbies": user_profile.get("hobbies"),
    }
    state_str = json.dumps(cache_state, ensure_ascii=False, sort_keys=True)
    cache_key = "book_recommendation_" + hashlib.md5(
        state_str.encode("utf-8")
    ).hexdigest()

    cached_recommendation = cache.get(cache_key)
    recommendation = cached_recommendation
    is_cached = bool(cached_recommendation) and not force
    is_stale = False
    service_status = {
        "state": "healthy",
        "retryable": False,
    }

    if not is_cached:
        try:
            recommendation = BookRecommendationAgent.recommend(
                user_profile,
                force_theme=force_theme if force else None,
                cached_data=cached_recommendation
            )
        except BookRecommendationUnavailable as exc:
            if cached_recommendation:
                recommendation = cached_recommendation
                is_cached = True
                is_stale = True
                service_status = {
                    "state": "degraded",
                    "retryable": True,
                    "code": exc.code,
                    "message": "새 추천 생성에 실패해 이전 추천을 표시합니다.",
                }
            else:
                return Response(
                    {
                        "detail": str(exc),
                        "code": exc.code,
                        "retryable": True,
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        except Exception as exc:
            print(f"[BookAgent] Unexpected recommendation failure: {exc}")
            if cached_recommendation:
                recommendation = cached_recommendation
                is_cached = True
                is_stale = True
                service_status = {
                    "state": "degraded",
                    "retryable": True,
                    "code": "BOOK_RECOMMENDATION_UNEXPECTED_ERROR",
                    "message": "새 추천 생성에 실패해 이전 추천을 표시합니다.",
                }
            else:
                return Response(
                    {
                        "detail": "책 추천을 생성하는 중 일시적인 오류가 발생했습니다.",
                        "code": "BOOK_RECOMMENDATION_UNEXPECTED_ERROR",
                        "retryable": True,
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        else:
            # Only complete, general-book-only recommendations are cached.
            cache.set(cache_key, recommendation, timeout=3600 * 24)

    return Response(
        {
            **recommendation,
            "is_cached": is_cached,
            "is_stale": is_stale,
            "service_status": service_status,
            "profile_basis": _public_profile_basis(user_profile),
            "content_date": today_str,
            "processing_notice": {
                "nlk": {
                    "data": ["개인화 정보에서 생성된 일반 도서 검색어"],
                    "purpose": "국립중앙도서관 국가서지 LOD 도서 검색",
                    "personal_profile_sent": False,
                    "service_cache": "최대 24시간",
                    "country": "대한민국",
                },
                "openai": {
                    "data": ["오늘의 감정", "선택한 관심사", "선택한 취미", "도서 후보 정보"],
                    "purpose": "검색어 설계와 맞춤 추천 서평 생성",
                    "service_cache": "최대 24시간",
                    "vendor_retention": "OpenAI API 정책에 따라 일반적으로 최대 30일의 부정사용 모니터링 로그",
                },
            },
        }
    )

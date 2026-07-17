from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


from user.models import UserProfile
from user.views import CsrfExemptSessionAuthentication

from .agent import (
    BookRecommendationAgent,
    BookRecommendationUnavailable,
    RECOMMENDATION_ENGINE_VERSION,
)
from .models import DailyBookRecommendation


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


PROFILE_BASIS_TO_THEME = {
    "today_emotion": "emotion",
    "interests": "interests",
    "hobbies": "hobbies",
}


def _changed_profile_themes(stored_basis, current_basis):
    stored_basis = stored_basis if isinstance(stored_basis, dict) else {}
    current_basis = current_basis if isinstance(current_basis, dict) else {}
    return [
        theme_id
        for basis_key, theme_id in PROFILE_BASIS_TO_THEME.items()
        if stored_basis.get(basis_key) != current_basis.get(basis_key)
    ]


def _isbns_for_themes(isbn_map, theme_ids):
    allowed = set(theme_ids or [])
    return {
        theme_id: values
        for theme_id, values in (isbn_map or {}).items()
        if theme_id in allowed
    }


def _recommendation_isbns(recommendation):
    isbns_by_theme = {}
    for book in recommendation.get("books", []) if isinstance(recommendation, dict) else []:
        if not isinstance(book, dict):
            continue
        theme_id = str(book.get("theme_id") or "").strip()
        isbn = str(book.get("isbn") or "").strip()
        if theme_id and isbn:
            isbns_by_theme.setdefault(theme_id, []).append(isbn)
    return isbns_by_theme


def _merge_isbns_by_theme(*isbn_maps):
    merged = {}
    for isbn_map in isbn_maps:
        if not isinstance(isbn_map, dict):
            continue
        for theme_id, values in isbn_map.items():
            target = merged.setdefault(theme_id, [])
            for value in values if isinstance(values, (list, tuple, set)) else []:
                isbn = str(value or "").strip()
                if isbn and isbn not in target:
                    target.append(isbn)
    return merged


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def book_recommendation(request):
    force = request.query_params.get("force", "").lower() == "true"
    force_theme = request.query_params.get("theme", "").lower()
    if force_theme not in ["emotion", "interests", "hobbies"]:
        force_theme = None

    today = timezone.localdate()
    daily_record = DailyBookRecommendation.objects.filter(
        user=request.user,
        recommendation_date=today,
    ).first()
    user_profile = _build_user_profile(request.user)
    current_profile_basis = _public_profile_basis(user_profile)
    changed_themes = _changed_profile_themes(
        daily_record.profile_basis if daily_record else None,
        current_profile_basis,
    ) if daily_record else []
    profile_changed = bool(changed_themes)
    stored_payload = daily_record.payload if daily_record else {}
    stored_engine = (stored_payload or {}).get("recommendation_engine")
    stored_book_source = (
        (stored_payload or {}).get("source_disclosure") or {}
    ).get("book_metadata")
    engine_changed = bool(daily_record) and (
        (stored_engine and stored_engine != RECOMMENDATION_ENGINE_VERSION)
        or (not stored_engine and stored_book_source == "국립중앙도서관 국가서지 LOD")
    )
    recommendation = daily_record.payload if daily_record else None
    profile_basis = daily_record.profile_basis if daily_record else None
    content_date = daily_record.recommendation_date if daily_record else today
    is_cached = bool(daily_record) and not force and not profile_changed and not engine_changed
    is_stale = False
    service_status = {
        "state": "healthy",
        "retryable": False,
    }

    if not is_cached:
        profile_basis = current_profile_basis
        previous_record = (
            DailyBookRecommendation.objects.filter(
                user=request.user,
                recommendation_date__lt=today,
            )
            .order_by("-recommendation_date")
            .first()
        )
        previous_isbns = _recommendation_isbns(
            previous_record.payload if previous_record else None
        )
        if (force or engine_changed) and daily_record:
            previous_isbns = _merge_isbns_by_theme(
                previous_isbns,
                _recommendation_isbns(daily_record.payload),
            )
        elif profile_changed and daily_record:
            previous_isbns = _merge_isbns_by_theme(
                previous_isbns,
                _isbns_for_themes(
                    _recommendation_isbns(daily_record.payload),
                    changed_themes,
                ),
            )

        automatic_force_theme = changed_themes[0] if len(changed_themes) == 1 else None

        try:
            recommendation = BookRecommendationAgent.recommend(
                user_profile,
                force_theme=force_theme if force else automatic_force_theme,
                cached_data=daily_record.payload if daily_record else None,
                excluded_isbns=previous_isbns,
            )
        except BookRecommendationUnavailable as exc:
            fallback_record = daily_record or previous_record
            if fallback_record:
                recommendation = fallback_record.payload
                profile_basis = fallback_record.profile_basis
                content_date = fallback_record.recommendation_date
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
            fallback_record = daily_record or previous_record
            if fallback_record:
                recommendation = fallback_record.payload
                profile_basis = fallback_record.profile_basis
                content_date = fallback_record.recommendation_date
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
            if force or profile_changed or engine_changed:
                daily_record, _ = DailyBookRecommendation.objects.update_or_create(
                    user=request.user,
                    recommendation_date=today,
                    defaults={
                        "payload": recommendation,
                        "profile_basis": profile_basis,
                    },
                )
            else:
                # If concurrent requests generated recommendations together, the
                # unique user/date constraint makes the first completed result win.
                daily_record, created = DailyBookRecommendation.objects.get_or_create(
                    user=request.user,
                    recommendation_date=today,
                    defaults={
                        "payload": recommendation,
                        "profile_basis": profile_basis,
                    },
                )
                if not created:
                    recommendation = daily_record.payload
                    profile_basis = daily_record.profile_basis
                    is_cached = True
            content_date = daily_record.recommendation_date

    return Response(
        {
            **recommendation,
            "is_cached": is_cached,
            "is_stale": is_stale,
            "service_status": service_status,
            "profile_basis": profile_basis or {},
            "content_date": content_date.isoformat(),
            "processing_notice": {
                "kakao_book": {
                    "data": ["개인화 정보에서 생성된 도서 검색어"],
                    "purpose": "Kakao Daum 책 검색에서 후보·책 소개·저자·출판·가격·판매상태·표지 조회",
                    "personal_profile_sent": False,
                    "service_cache": "해당 추천 날짜 동안",
                    "country": "대한민국",
                },
                "openai": {
                    "data": [
                        "오늘의 감정", "선택한 관심사", "선택한 취미",
                        "Kakao 도서 후보의 책 소개·저자·번역자·출판사·출간일·ISBN·가격·판매상태",
                    ],
                    "purpose": "검색어 설계, 후보 비교·선택, 장르 판단과 맞춤 추천사 생성",
                    "service_cache": "해당 추천 날짜 동안",
                    "vendor_retention": "OpenAI API 정책에 따라 일반적으로 최대 30일의 부정사용 모니터링 로그",
                },
            },
        }
    )

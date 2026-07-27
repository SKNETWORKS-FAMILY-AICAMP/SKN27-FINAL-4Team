from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.views import CsrfExemptSessionAuthentication

from .agent import BookRecommendationAgent
from .constants import SUPPORTED_THEME_IDS
from .services.profile_service import (
    build_user_profile as _build_user_profile,
)
from .services.recommendation_service import (
    build_recommendation_response,
)


@api_view(["GET"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def book_recommendation(request):
    """Validate HTTP input and delegate recommendation work to the service layer."""
    force = request.query_params.get("force", "").strip().lower() == "true"
    requested_theme = request.query_params.get("theme", "").strip().lower()
    if requested_theme and requested_theme not in SUPPORTED_THEME_IDS:
        return Response(
            {
                "detail": "지원하지 않는 책 추천 테마입니다.",
                "code": "BOOK_RECOMMENDATION_INVALID_THEME",
                "supported_themes": list(SUPPORTED_THEME_IDS),
            },
            status=400,
        )
    force_theme = requested_theme if requested_theme in SUPPORTED_THEME_IDS else None

    result = build_recommendation_response(
        user=request.user,
        user_profile=_build_user_profile(request.user),
        today=timezone.localdate(),
        recommendation_agent=BookRecommendationAgent,
        force=force,
        force_theme=force_theme,
    )
    return Response(result.payload, status=result.status_code)

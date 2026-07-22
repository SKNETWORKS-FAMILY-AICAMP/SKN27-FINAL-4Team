from django.conf import settings
from datetime import date
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from config.permissions import IsAuthenticatedOrDevelopment
from calendar_api.serializers import DailyFortuneSerializer
from calendar_api.services import (
    save_daily_major_as_daily_fortune,
    save_tarot_result_as_daily_fortune,
)
from user.models import User

from .serializers import DailyTarotFortuneSerializer, TarotReadingRequestSerializer
from .services import create_reading, get_or_create_daily_major_fortune


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Skip CSRF only for the local development client-id flow."""

    def enforce_csrf(self, request):
        if settings.DEBUG:
            return
        return super().enforce_csrf(request)


def _get_social_demo_email(provider, client_id):
    safe_provider = ''.join(char for char in provider if char.isalnum())[:20] or 'social'
    safe_client_id = ''.join(char for char in client_id if char.isalnum())[:32] or 'guest'
    return f'{safe_provider}.{safe_client_id}@binteumsai.local'


def _get_development_user(request):
    if not settings.DEBUG:
        return None

    client_id = (
        request.headers.get('X-Binteumsai-Client-Id')
        or request.query_params.get('client_id')
        or ''
    ).strip()
    if not client_id:
        return None

    user, created = User.objects.get_or_create(
        email=_get_social_demo_email('guest', client_id),
        defaults={'nickname': '임시 사용자'},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])

    return user


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticatedOrDevelopment])
def create_tarot_reading(request):
    serializer = TarotReadingRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = create_reading(
            data=serializer.validated_data,
            user=request.user if request.user.is_authenticated else None,
        )
        target_date = serializer.validated_data.get('date') or timezone.localdate()
        fortune = save_tarot_result_as_daily_fortune(request, result, target_date)
        if fortune:
            result['daily_fortune'] = DailyFortuneSerializer(fortune).data

        return Response(result, status=status.HTTP_201_CREATED)

    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as exc:
        if settings.DEBUG:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {'error': 'Failed to create tarot reading.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticatedOrDevelopment])
def daily_major_fortune(request):
    raw_date = request.data.get('date') if request.method == 'POST' else request.query_params.get('date')
    target_date = timezone.localdate()
    if raw_date:
        try:
            target_date = date.fromisoformat(raw_date)
        except ValueError:
            return Response({'error': 'date must be YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        fortune_user = request.user if request.user.is_authenticated else _get_development_user(request)
        if fortune_user is None:
            return Response({'error': '로그인이 필요한 요청입니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        fortune = get_or_create_daily_major_fortune(fortune_user, target_date)
        result = DailyTarotFortuneSerializer(fortune).data

        if request.method == 'POST':
            daily_fortune = save_daily_major_as_daily_fortune(
                request,
                result.copy(),
                target_date,
            )
            if daily_fortune:
                result['daily_fortune'] = DailyFortuneSerializer(daily_fortune).data

        return Response(result, status=status.HTTP_200_OK)

    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as exc:
        if settings.DEBUG:
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {'error': 'Failed to load daily tarot fortune.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

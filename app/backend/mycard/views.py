from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MyCard
from .serializers import MyCardGenerateSerializer, MyCardSerializer
from .services import generate_card_content


class MyCardSessionAuthentication(SessionAuthentication):
    """Keep the session-based auth flow while returning 401 for missing auth."""

    def authenticate_header(self, request):
        return 'Session'


def _error(code, message, http_status):
    return Response({'error': {'code': code, 'message': message}}, status=http_status)


def _require_onboarding(request):
    if not request.user.onboarding_done or not request.user.character:
        return _error('ONBOARDING_REQUIRED', '캐릭터와 기본 정보 설정을 먼저 완료해주세요.', status.HTTP_403_FORBIDDEN)
    return None


@api_view(['GET'])
@authentication_classes([MyCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def bootstrap(request):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    count = MyCard.objects.filter(user=request.user, date=timezone.localdate()).count()
    return Response({'today_generation_count': count})


@api_view(['POST'])
@authentication_classes([MyCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def generate(request):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    serializer = MyCardGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return _error('INVALID_MY_CARD_REQUEST', serializer.errors, status.HTTP_400_BAD_REQUEST)
    today = timezone.localdate()
    if MyCard.objects.filter(user=request.user, date=today).count() >= 2:
        return _error('MY_CARD_DAILY_LIMIT', '오늘은 카드를 최대 2회까지 만들 수 있어요.', status.HTTP_429_TOO_MANY_REQUESTS)

    payload = serializer.validated_data
    content = generate_card_content(payload)
    card = MyCard.objects.create(
        user=request.user,
        date=today,
        sky=payload['sky'],
        pace=payload['pace'],
        space=payload['space'],
        phrase=payload['phrase'],
        free_text=payload.get('free_text', ''),
        style=payload.get('style', ''),
        custom_style=payload.get('custom_style', ''),
        image_url=content['image_url'],
        title=content['title'],
        description=content['description'],
    )
    return Response(MyCardSerializer(card).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([MyCardSessionAuthentication])
@permission_classes([IsAuthenticated])
def save(request, card_id):
    blocked = _require_onboarding(request)
    if blocked:
        return blocked
    card = get_object_or_404(MyCard, id=card_id, user=request.user)
    if not card.is_saved:
        card.is_saved = True
        card.save(update_fields=['is_saved'])
    return Response({}, status=status.HTTP_200_OK)

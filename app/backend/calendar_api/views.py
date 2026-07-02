from datetime import date

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from chat.models import ChatMessage
from .models import DailyFortune
from .serializers import DailyFortuneSerializer
from .services import get_owner_filter


def get_emotion_labels_by_date(request, dates):
    if not request.user.is_authenticated or not dates:
        return {}

    messages = (
        ChatMessage.objects.filter(
            session__user=request.user,
            role='assistant',
            emotion_label__isnull=False,
            created_at__date__in=dates,
        )
        .exclude(emotion_label='')
        .order_by('created_at')
    )

    return {message.created_at.date(): message.emotion_label for message in messages}


def serialize_daily_fortune_with_emotion(request, fortune):
    data = DailyFortuneSerializer(fortune).data
    data['emotion_label'] = get_emotion_labels_by_date(request, [fortune.date]).get(fortune.date)
    return data


@api_view(['GET'])
@permission_classes([AllowAny])
def get_calendar_month(request):
    owner_filter = get_owner_filter(request)
    if owner_filter is None:
        return Response([], status=status.HTTP_200_OK)

    today = timezone.localdate()
    try:
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        start_date = date(year, month, 1)
        end_date = date(year + int(month == 12), 1 if month == 12 else month + 1, 1)
    except (TypeError, ValueError):
        return Response({'error': 'Invalid year or month.'}, status=status.HTTP_400_BAD_REQUEST)

    fortunes = DailyFortune.objects.filter(
        **owner_filter,
        date__gte=start_date,
        date__lt=end_date,
    ).order_by('date')

    emotion_by_date = get_emotion_labels_by_date(request, [fortune.date for fortune in fortunes])

    return Response([
        {
            'date': fortune.date.isoformat(),
            'day': fortune.date.day,
            'topic': fortune.topic,
            'title': fortune.title,
            'keyword': fortune.keyword,
            'emotion_label': emotion_by_date.get(fortune.date),
            'has_fortune': bool(fortune.content),
        }
        for fortune in fortunes
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def get_calendar_day(request):
    owner_filter = get_owner_filter(request)
    if owner_filter is None:
        return Response({'fortune': None}, status=status.HTTP_200_OK)

    value = request.query_params.get('date')
    if not value:
        return Response({'error': 'date is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_date = date.fromisoformat(value)
    except ValueError:
        return Response({'error': 'date must be YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    fortune = DailyFortune.objects.filter(**owner_filter, date=target_date).first()
    return Response({'fortune': serialize_daily_fortune_with_emotion(request, fortune) if fortune else None})

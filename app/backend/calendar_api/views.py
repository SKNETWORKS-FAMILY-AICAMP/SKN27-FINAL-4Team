from collections import defaultdict
from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from config.permissions import IsAuthenticatedOrDevelopment
from chat.models import ChatMessage
from .models import DailyFortune
from .serializers import DailyFortuneSerializer
from .services import get_owner_filter


MIN_CHAT_TURNS_FOR_SUMMARY = 3


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


def get_emotion_labels_in_range(request, start_date, end_date):
    """Return the last analysed chat emotion for every day in a month range."""
    if not request.user.is_authenticated:
        return {}

    messages = (
        ChatMessage.objects.filter(
            session__user=request.user,
            role='assistant',
            emotion_label__isnull=False,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
        )
        .exclude(emotion_label='')
        .order_by('created_at')
    )
    return {message.created_at.date().isoformat(): message.emotion_label for message in messages}


def build_conversation_summary(messages):
    """Make a short, privacy-safe display summary from the user's own messages."""
    snippets = []
    for message in messages:
        text = ' '.join(str(message.content or '').split())
        if text:
            snippets.append(text[:90])
        if len(snippets) == 2:
            break

    if not snippets:
        return ''
    if len(snippets) == 1:
        return snippets[0]
    return f'{snippets[0]} / {snippets[1]}'


def get_chat_records_in_range(request, start_date, end_date):
    """Return the emotion and an optional summary for every chat-emotion day."""
    if not request.user.is_authenticated:
        return {}

    messages = (
        ChatMessage.objects.filter(
            session__user=request.user,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
            role__in=('user', 'assistant'),
        )
        .order_by('created_at')
    )
    by_date = defaultdict(list)
    for message in messages:
        by_date[message.created_at.date().isoformat()].append(message)

    records = {}
    for date_key, day_messages in by_date.items():
        emotion_messages = [
            message for message in day_messages
            if message.role == 'assistant' and message.emotion_label
        ]
        if not emotion_messages:
            continue

        user_messages = [message for message in day_messages if message.role == 'user']
        has_summary = len(user_messages) >= MIN_CHAT_TURNS_FOR_SUMMARY
        records[date_key] = {
            'emotion_label': emotion_messages[-1].emotion_label,
            'conversation': {
                'has_sufficient_conversation': has_summary,
                'summary': build_conversation_summary(user_messages) if has_summary else '',
            },
        }
    return records


def serialize_daily_fortune_with_emotion(request, fortune):
    data = DailyFortuneSerializer(fortune).data
    data['emotion_label'] = get_emotion_labels_by_date(request, [fortune.date]).get(fortune.date)
    return data


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrDevelopment])
def get_calendar_month(request):
    owner_filter = get_owner_filter(request)
    today = timezone.localdate()
    try:
        year = int(request.query_params.get('year', today.year))
        month = int(request.query_params.get('month', today.month))
        start_date = date(year, month, 1)
        end_date = date(year + int(month == 12), 1 if month == 12 else month + 1, 1)
    except (TypeError, ValueError):
        return Response({'error': 'Invalid year or month.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from checkin.views import calendar_entries_for
        checkins = {item['date']: item for item in calendar_entries_for(request.user, start_date, end_date)} if request.user.is_authenticated else {}
    except Exception:
        checkins = {}

    if owner_filter is None:
        fortunes = DailyFortune.objects.none()
    else:
        fortunes = DailyFortune.objects.filter(
            **owner_filter,
            topic='daily_major',
            date__gte=start_date,
            date__lt=end_date,
        ).order_by('date')

    chat_records_by_date = get_chat_records_in_range(request, start_date, end_date)
    fortune_by_date = {fortune.date.isoformat(): fortune for fortune in fortunes}
    # A chat emotion is a calendar record in its own right: do not require a
    # daily tarot card or check-in before showing the character expression.
    dates = sorted(set(fortune_by_date) | set(checkins) | set(chat_records_by_date))
    return Response([
        {
            'date': date_key,
            'day': date.fromisoformat(date_key).day,
            'topic': fortune_by_date[date_key].topic if date_key in fortune_by_date else 'checkin',
            'title': fortune_by_date[date_key].title if date_key in fortune_by_date else '오늘의 나',
            'keyword': fortune_by_date[date_key].keyword if date_key in fortune_by_date else '',
            'emotion_label': (chat_records_by_date.get(date_key) or {}).get('emotion_label') or (checkins.get(date_key) or {}).get('primary_emotion'),
            'conversation': (chat_records_by_date.get(date_key) or {}).get('conversation'),
            'has_fortune': bool(fortune_by_date[date_key].content) if date_key in fortune_by_date else False,
            'checkin': checkins.get(date_key),
        }
        for date_key in dates
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrDevelopment])
def get_calendar_day(request):
    owner_filter = get_owner_filter(request)
    value = request.query_params.get('date')
    if not value:
        return Response({'error': 'date is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_date = date.fromisoformat(value)
    except ValueError:
        return Response({'error': 'date must be YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    fortune = (
        DailyFortune.objects.filter(**owner_filter, topic='daily_major', date=target_date).first()
        if owner_filter is not None
        else None
    )
    checkin = None
    if request.user.is_authenticated:
        try:
            from checkin.models import DailyCheckin
            from checkin.services import calendar_entry
            item = DailyCheckin.objects.select_related('reflection', 'cause', 'need', 'selected_action').filter(
                user=request.user, checkin_date=target_date,
            ).first()
            checkin = calendar_entry(item) if item else None
        except Exception:
            checkin = None
    return Response({
        'fortune': serialize_daily_fortune_with_emotion(request, fortune) if fortune else None,
        'conversation': get_chat_records_in_range(request, target_date, target_date + timedelta(days=1)).get(target_date.isoformat()),
        'checkin': checkin,
    })

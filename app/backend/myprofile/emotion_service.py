from collections import Counter

from django.utils import timezone

from chat.models import ChatMessage
from user.constants import EMOTION_LABELS_KO


def build_today_emotion_summary(user) -> dict:
    """Build today's assistant-emotion summary and recency-weighted representative."""
    today = timezone.localdate()
    labels = list(
        ChatMessage.objects.filter(
            session__user=user,
            role='assistant',
            emotion_label__isnull=False,
            created_at__date=today,
        )
        .exclude(emotion_label='')
        .order_by('created_at', 'id')
        .values_list('emotion_label', flat=True)
    )

    counts = Counter(labels)
    recency_scores: dict[str, float] = {}
    total_count = len(labels)
    for index, label in enumerate(labels):
        recency_scores[label] = recency_scores.get(label, 0.0) + (
            (index + 1) / total_count
        )

    representative_key = (
        max(recency_scores, key=recency_scores.get)
        if recency_scores
        else None
    )
    representative = (
        {
            'key': representative_key,
            'label': EMOTION_LABELS_KO.get(
                representative_key,
                representative_key,
            ),
            'count': counts[representative_key],
        }
        if representative_key
        else None
    )

    distribution = [
        {
            'key': key,
            'label': EMOTION_LABELS_KO.get(key, key),
            'count': count,
        }
        for key, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    top_count = distribution[0]['count'] if distribution else 0

    return {
        'date': today.isoformat(),
        'total_count': total_count,
        'representative': representative,
        'dominant': [
            item for item in distribution if item['count'] == top_count
        ],
        'distribution': distribution,
    }

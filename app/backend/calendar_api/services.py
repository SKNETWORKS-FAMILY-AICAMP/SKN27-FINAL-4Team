def get_client_id(request):
    value = (
        request.headers.get('X-Binteumsai-Client-Id')
        or request.data.get('client_id')
        or request.query_params.get('client_id')
        or ''
    )
    return value.strip()[:64]


def get_owner_filter(request):
    if request.user.is_authenticated:
        return {'user': request.user}

    client_id = get_client_id(request)
    if not client_id:
        return None

    return {'user__isnull': True, 'client_id': client_id}


def get_fortune_content(result, topic):
    category_results = result.get('category_results') or {}
    return (
        category_results.get(topic)
        or category_results.get('general')
        or result.get('combined_summary')
        or result.get('llm_advice')
        or ''
    )


def get_fortune_keyword(result):
    cards = result.get('cards') or []
    if cards:
        return cards[0].get('card_name_ko') or cards[0].get('card_name') or ''

    return ''


def save_tarot_result_as_daily_fortune(request, result, target_date):
    from .models import DailyFortune

    owner_filter = get_owner_filter(request)
    if owner_filter is None:
        return None

    topic = result.get('topic') or 'general'
    defaults = {
        'reading_id': result.get('reading_id'),
        'topic': topic,
        'title': 'Daily fortune',
        'content': get_fortune_content(result, topic),
        'keyword': get_fortune_keyword(result),
        'question': result.get('question') or '',
        'cards': result.get('cards') or [],
        'category_results': result.get('category_results') or {},
        'disclaimer': result.get('disclaimer') or '',
        'client_id': '' if request.user.is_authenticated else get_client_id(request),
    }

    fortune, _ = DailyFortune.objects.update_or_create(
        date=target_date,
        **owner_filter,
        defaults=defaults,
    )
    return fortune


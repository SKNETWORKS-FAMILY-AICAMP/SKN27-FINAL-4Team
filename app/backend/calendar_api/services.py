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


def save_daily_major_as_daily_fortune(request, result, target_date):
    """Persist a revealed daily-major card in the same calendar record format."""
    from .models import DailyFortune

    owner_filter = get_owner_filter(request)
    if owner_filter is None:
        return None

    card_name = result.get('card_name_ko') or result.get('card_name') or ''
    card_meaning = (
        result.get('card_defined_meaning')
        or result.get('card_description')
        or result.get('message')
        or ''
    )
    card_keywords = result.get('card_keywords') or []
    keyword = ' · '.join(card_keywords) if card_keywords else card_name

    defaults = {
        'reading_id': None,
        'topic': 'daily_major',
        'title': '오늘의 카드',
        'content': card_meaning,
        'keyword': keyword[:80],
        'question': '',
        'cards': [
            {
                'card_number': result.get('card_number'),
                'card_name': result.get('card_name') or '',
                'card_name_ko': result.get('card_name_ko') or '',
                'orientation': 'upright',
            }
        ],
        'category_results': {'general': card_meaning},
        'disclaimer': '',
        'client_id': '' if request.user.is_authenticated else get_client_id(request),
    }

    fortune, _ = DailyFortune.objects.update_or_create(
        date=target_date,
        **owner_filter,
        defaults=defaults,
    )
    return fortune


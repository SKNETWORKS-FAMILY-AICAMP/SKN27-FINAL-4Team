import os
import json
import re
import secrets

from django.db import connection, transaction
from django.utils import timezone
from openai import OpenAI

from user.models import UserProfile

from .models import DailyTarotFortune
from .prompts import build_tarot_prompt


MODEL_NAME = 'gpt-4o-mini'
PROMPT_VERSION = 'tarot-v1'
DISCLAIMER_TEXT = '타로카드 운세는 마음을 정리해보는 참고용 조언이에요.\n중요한 결정은 현실적인 정보와 함께 신중하게 판단해 주세요.'

TOPIC_LABELS = {
    'general': '총운',
    'relationship': '관계운',
    'work': '업무, 학업운',
    'money': '금전운',
    'success': '성공',
}

QUESTION_TOPIC_KEYWORDS = {
    'relationship': [
        '연애', '사랑', '관계', '남자친구', '여자친구', '애인', '썸', '짝사랑',
        '이별', '재회', '결혼', '친구', '가족', '동료', '사람', '대화',
    ],
    'work': [
        '일', '직장', '회사', '업무', '커리어', '이직', '퇴사', '취업', '면접',
        '공부', '시험', '과제', '프로젝트', '상사', '동료', '진로',
    ],
    'money': [
        '돈', '재물', '금전', '소비', '지출', '수입', '월급', '투자', '저축',
        '대출', '부업', '매출', '계약', '구매',
    ],
    'success': [
        '성공', '목표', '결과', '합격', '성과', '성취', '가능성', '도전',
        '준비', '계획', '완성', '마무리',
    ],
}

QUESTION_FOCUS_GUIDES = {
    'relationship': '사용자 질문을 관계, 감정 표현, 거리감, 대화 방식, 상대와의 흐름 중심으로 해석하세요.',
    'work': '사용자 질문을 일, 공부, 업무 태도, 준비 과정, 커리어 선택 중심으로 해석하세요.',
    'money': '사용자 질문을 소비, 지출, 수입, 기회, 안정적인 관리 중심으로 해석하세요.',
    'success': '사용자 질문을 목표 달성, 결과 가능성, 준비 과정, 성취를 위한 다음 행동 중심으로 해석하세요.',
    'general': '사용자 질문을 오늘의 전반적인 흐름과 마음 상태, 현실적인 선택 중심으로 해석하세요.',
}

RESULT_LINK_PREFIXES = {}
ADVICE_LINK_PREFIXES = {}


POSITION_LABELS = [
    ('present', '현재 상황'),
    ('flow', '흐름'),
    ('advice', '조언'),
]

TAROT_READING_CARD_COUNT = len(POSITION_LABELS)

MAJOR_CARD_NAMES_KO = {
    'The Fool': '바보',
    'The Magician': '마법사',
    'The High Priestess': '여사제',
    'The Empress': '여황제',
    'The Emperor': '황제',
    'The Hierophant': '교황',
    'The Lovers': '연인',
    'The Chariot': '전차',
    'Strength': '힘',
    'The Hermit': '은둔자',
    'Wheel of Fortune': '운명의 수레바퀴',
    'Justice': '정의',
    'The Hanged Man': '매달린 사람',
    'Death': '죽음',
    'Temperance': '절제',
    'The Devil': '악마',
    'The Tower': '탑',
    'The Star': '별',
    'The Moon': '달',
    'The Sun': '태양',
    'Judgement': '심판',
    'The World': '세계',
}

RANK_NAMES_KO = {
    'Ace': '에이스',
    'Two': '2',
    'Three': '3',
    'Four': '4',
    'Five': '5',
    'Six': '6',
    'Seven': '7',
    'Eight': '8',
    'Nine': '9',
    'Ten': '10',
    'Page': '페이지',
    'Knight': '기사',
    'Queen': '여왕',
    'King': '왕',
}

SUIT_NAMES_KO = {
    'Wands': '완드',
    'Cups': '컵',
    'Swords': '소드',
    'Pentacles': '펜타클',
}


def normalize_topic(topic):
    topic_map = {
        'relationship': 'love',
        'work': 'career',
        'money': 'career',
        'success': 'career',
        'love': 'love',
        'career': 'career',
        'general': 'general',
    }
    return topic_map.get(topic, 'general')


def analyze_question(question, selected_topic):
    normalized_question = (question or '').strip().lower()
    selected_topic = selected_topic if selected_topic in TOPIC_LABELS else 'general'

    scores = {}
    for topic, keywords in QUESTION_TOPIC_KEYWORDS.items():
        scores[topic] = sum(1 for keyword in keywords if keyword in normalized_question)

    inferred_topic = max(scores, key=scores.get) if scores else selected_topic
    if scores.get(inferred_topic, 0) == 0:
        inferred_topic = selected_topic

    focus_topic = inferred_topic if inferred_topic != 'general' else selected_topic
    if focus_topic not in QUESTION_FOCUS_GUIDES:
        focus_topic = 'general'

    has_specific_question = bool(normalized_question)
    question_focus = QUESTION_FOCUS_GUIDES[focus_topic]

    if has_specific_question:
        question_focus += ' 카드 해석은 일반 설명으로 끝내지 말고 사용자의 질문에 직접 답하는 문장으로 작성하세요.'
    else:
        question_focus += ' 질문이 비어 있으므로 오늘 필요한 조언을 중심으로 작성하세요.'

    return {
        'question': normalized_question,
        'selected_topic': selected_topic,
        'selected_topic_label': TOPIC_LABELS.get(selected_topic, '총운'),
        'inferred_topic': inferred_topic,
        'inferred_topic_label': TOPIC_LABELS.get(inferred_topic, '총운'),
        'focus_topic': focus_topic,
        'focus_topic_label': TOPIC_LABELS.get(focus_topic, '총운'),
        'question_focus': question_focus,
        'has_specific_question': has_specific_question,
    }


def get_card_name_ko(card_name):
    if card_name in MAJOR_CARD_NAMES_KO:
        return MAJOR_CARD_NAMES_KO[card_name]

    if ' of ' not in card_name:
        return card_name

    rank, suit = card_name.split(' of ', 1)
    rank_ko = RANK_NAMES_KO.get(rank)
    suit_ko = SUIT_NAMES_KO.get(suit)

    if not rank_ko or not suit_ko:
        return card_name

    return f'{suit_ko} {rank_ko}'


def get_llm_client():
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()

    if not api_key:
        raise ValueError('OPENAI_API_KEY가 설정되지 않았습니다.')

    return OpenAI(api_key=api_key)


def sum_digits(value):
    return sum(int(char) for char in re.sub(r'\D', '', str(value or '')) if char.isdigit())


def reduce_to_major_arcana_number(number):
    result = int(number or 0)
    while result > 22:
        result = sum(int(char) for char in str(result))
    return result or 1


def numerology_number_to_card_number(number):
    return 0 if int(number) == 22 else int(number)


def calculate_daily_major_numbers(birth_date, target_date):
    birth_number = reduce_to_major_arcana_number(sum_digits(birth_date.isoformat()))
    date_number = reduce_to_major_arcana_number(sum_digits(target_date.isoformat()))
    daily_number = reduce_to_major_arcana_number(birth_number + date_number)
    card_number = numerology_number_to_card_number(daily_number)

    return {
        'birth_number': birth_number,
        'date_number': date_number,
        'daily_number': daily_number,
        'card_number': card_number,
    }


def fetch_daily_major_card(card_number):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT card_number, card_name
            FROM tarot_cards
            WHERE card_number = %s
              AND arcana = 'Major'
            """,
            [card_number],
        )
        row = cursor.fetchone()

    if not row:
        raise ValueError('오늘의 메이저 카드 정보를 DB에서 찾을 수 없습니다.')

    return {
        'card_number': row[0],
        'card_name': row[1],
        'card_name_ko': get_card_name_ko(row[1]),
    }


def build_daily_major_message(card_name_ko):
    return (
        f'{card_name_ko}의 흐름은 오늘의 방향을 차분히 살피고, '
        '지금 할 수 있는 작은 선택부터 정리해보라는 신호예요. '
        '큰 결정을 서두르기보다 마음의 기준을 부드럽게 세워보세요.'
    )


def get_or_create_daily_major_fortune(user, target_date=None):
    target_date = target_date or timezone.localdate()

    if user is None:
        raise ValueError('로그인 후 오늘의 메이저 카드를 확인할 수 있습니다.')

    profile = UserProfile.objects.filter(user=user).first()
    if not profile or not profile.birth_date:
        raise ValueError('생년월일을 먼저 저장해 주세요.')

    existing = DailyTarotFortune.objects.filter(
        user=user,
        target_date=target_date,
        fortune_type='daily_major',
    ).first()
    if existing:
        return existing

    numbers = calculate_daily_major_numbers(profile.birth_date, target_date)
    card = fetch_daily_major_card(numbers['card_number'])

    defaults = {
        **numbers,
        'card_name': card['card_name'],
        'card_name_ko': card['card_name_ko'],
        'title': '오늘의 메이저 카드',
        'message': build_daily_major_message(card['card_name_ko']),
        'source': 'rule',
        'model_name': '',
        'prompt_version': '',
    }

    fortune, _ = DailyTarotFortune.objects.update_or_create(
        user=user,
        target_date=target_date,
        fortune_type='daily_major',
        defaults=defaults,
    )
    return fortune


def fetch_cards(selected_cards):
    card_numbers = [card['card_number'] for card in selected_cards]

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                card_number,
                card_name,
                arcana,
                suit,
                element,
                upright_meaning,
                reversed_meaning,
                love_meaning,
                career_meaning,
                upright_meaning_sentence_ko,
                reversed_meaning_sentence_ko,
                love_meaning_sentence_ko,
                career_meaning_sentence_ko,
                advice_seed_ko,
                llm_context_ko,
                yes_or_no,
                zodiac_sign,
                guide_url
            FROM tarot_cards
            WHERE card_number = ANY(%s)
            """,
            [card_numbers],
        )
        rows = cursor.fetchall()

    cards_by_number = {}
    for row in rows:
        cards_by_number[row[0]] = {
            'card_number': row[0],
            'card_name': row[1],
            'arcana': row[2],
            'suit': row[3],
            'element': row[4],
            'upright_meaning': row[5],
            'reversed_meaning': row[6],
            'love_meaning': row[7],
            'career_meaning': row[8],
            'upright_meaning_sentence_ko': row[9],
            'reversed_meaning_sentence_ko': row[10],
            'love_meaning_sentence_ko': row[11],
            'career_meaning_sentence_ko': row[12],
            'advice_seed_ko': row[13],
            'llm_context_ko': row[14],
            'yes_or_no': row[15],
            'zodiac_sign': row[16],
            'guide_url': row[17],
        }

    if len(cards_by_number) != TAROT_READING_CARD_COUNT:
        raise ValueError('선택한 카드 정보를 DB에서 찾을 수 없습니다.')

    return [cards_by_number[number] for number in card_numbers]


def draw_reading_cards(card_numbers=None):
    """Choose the reading cards and orientations on the server."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT card_number FROM tarot_cards")
        available_card_numbers = [row[0] for row in cursor.fetchall()]

    if len(available_card_numbers) < TAROT_READING_CARD_COUNT:
        raise ValueError("Tarot card data is not ready.")

    randomizer = secrets.SystemRandom()
    if card_numbers is not None:
        if len(card_numbers) != TAROT_READING_CARD_COUNT or len(set(card_numbers)) != TAROT_READING_CARD_COUNT:
            raise ValueError('Select exactly three different tarot cards.')
        if any(card_number not in available_card_numbers for card_number in card_numbers):
            raise ValueError('Selected tarot card data is not ready.')
    else:
        card_numbers = randomizer.sample(available_card_numbers, TAROT_READING_CARD_COUNT)

    return [
        {
            "card_number": card_number,
            "orientation": randomizer.choice(("upright", "reversed")),
        }
        for card_number in card_numbers
    ]


def select_card_meaning(card, orientation):
    if orientation == 'reversed':
        return (
            card.get('reversed_meaning_sentence_ko')
            or card.get('reversed_meaning')
            or ''
        )

    return (
        card.get('upright_meaning_sentence_ko')
        or card.get('upright_meaning')
        or ''
    )


def select_topic_meaning(card, topic, orientation):
    if topic == 'love':
        return card.get('love_meaning_sentence_ko') or card.get('love_meaning') or select_card_meaning(card, orientation)

    if topic == 'career':
        return card.get('career_meaning_sentence_ko') or card.get('career_meaning') or select_card_meaning(card, orientation)

    return select_card_meaning(card, orientation)


def build_card_payload(selected_cards, db_cards, topic):
    result = []

    for index, selected in enumerate(selected_cards):
        card = db_cards[index]
        orientation = selected['orientation']
        position_key, position_label = POSITION_LABELS[index]

        result.append({
            'position_key': position_key,
            'position_label': position_label,
            'card_order': index + 1,
            'card_number': card['card_number'],
            'card_name': card['card_name'],
            'card_name_ko': get_card_name_ko(card['card_name']),
            'orientation': orientation,
            'card_meaning': select_card_meaning(card, orientation),
            'topic_meaning': select_topic_meaning(card, topic, orientation),
            'advice_seed': card.get('advice_seed_ko') or '',
        })

    return result


def fetch_chunks(cards, topic):
    texts = []

    with connection.cursor() as cursor:
        for card in cards:
            cursor.execute(
                """
                SELECT text
                FROM tarot_card_chunks
                WHERE card_number = %s
                  AND (
                    (topic = %s AND orientation IN (%s, 'both'))
                    OR (topic = 'general' AND orientation IN (%s, 'both'))
                    OR (topic = 'all' AND orientation = 'both')
                  )
                ORDER BY
                  CASE
                    WHEN topic = %s AND orientation = %s THEN 1
                    WHEN topic = %s AND orientation = 'both' THEN 2
                    WHEN topic = 'general' THEN 3
                    ELSE 4
                  END
                LIMIT 3
                """,
                [
                    card['card_number'],
                    topic,
                    card['orientation'],
                    card['orientation'],
                    topic,
                    card['orientation'],
                    topic,
                ],
            )
            rows = cursor.fetchall()
            texts.extend([row[0] for row in rows])

    return '\n\n'.join(texts)


def call_llm(prompt):
    try:
        client = get_llm_client()
    except ValueError:
        return {
            'category_results': {},
            'card_readings': [],
            'action_advice': [],
            'category_advices': {},
        }

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                'role': 'system',
                'content': '당신은 한국어로 따뜻하고 현실적인 타로 조언을 작성하는 상담형 어시스턴트입니다. 반드시 JSON 객체로만 응답하세요.',
            },
            {
                'role': 'user',
                'content': prompt,
            },
        ],
        max_tokens=1800,
        temperature=0.7,
        response_format={'type': 'json_object'},
    )

    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        parsed = extract_json_object(raw)
        if isinstance(parsed, dict):
            return parsed

        return {
            'category_results': {},
            'card_readings': [],
            'action_advice': [],
        }


def try_parse_json_text(value):
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text:
        return value

    if text.startswith('{') and text.endswith('}'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value

    return value


def extract_json_object(text):
    if not isinstance(text, str):
        return text

    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = stripped.strip('`').strip()
        if stripped.startswith('json'):
            stripped = stripped[4:].strip()

    parsed = try_parse_json_text(stripped)
    if isinstance(parsed, dict):
        return parsed

    start = stripped.find('{')
    end = stripped.rfind('}')
    if start != -1 and end != -1 and start < end:
        parsed = try_parse_json_text(stripped[start:end + 1])
        if isinstance(parsed, dict):
            return parsed

    return text


def compact_text(value, max_length=260):
    if isinstance(value, (dict, list)):
        return ''

    text = str(value or '').strip()
    if not text:
        return ''

    text = ' '.join(text.split())
    if len(text) <= max_length:
        return text

    return text[:max_length].rstrip() + '...'


def sanitize_korean_text(value, max_length=260):
    value = extract_json_object(value)
    if isinstance(value, (dict, list)):
        return ''

    text = compact_text(value, max_length)
    if not text:
        return ''

    if any(marker in text for marker in ['category_results', 'action_advice', 'card_readings']):
        return ''

    text = re.sub(r'[A-Za-z_{}\\[\\]<>`"#$%^&*=|~]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.strip(' ,:;')
    return text


def clean_question_text(question, max_length=60):
    text = sanitize_korean_text(question, max_length)
    if not text:
        return '오늘의 흐름'

    return text


def get_topic_link_type(topic, question_analysis):
    focus_topic = question_analysis.get('focus_topic') or 'general'
    return 'main' if topic == focus_topic else 'sub'


def ensure_question_link(topic, text, question_analysis, max_length=260):
    cleaned = sanitize_korean_text(text, max_length)
    return cleaned if cleaned else ''


def ensure_advice_link(topic, advice, question_analysis):
    cleaned = sanitize_korean_text(advice, 260)
    return cleaned if cleaned else ''


def remove_card_names(text, cards):
    for card in cards:
        card_name = card.get('card_name_ko') or ''
        if card_name:
            text = text.replace(card_name, '')

    text = re.sub(r'\s*,\s*,+', ', ', text)
    text = re.sub(r'^\s*,\s*', '', text)
    text = re.sub(r'\s*,\s*조합', ' 조합', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def build_fallback_category_results(cards, question_analysis):
    has_question = question_analysis.get('has_specific_question')
    focus_topic = question_analysis.get('focus_topic') or 'general'

    if has_question and focus_topic == 'relationship':
        return {
            'relationship': '관계에서는 마음을 너무 빨리 결론내리기보다 대화의 분위기를 차분히 살피는 흐름이에요. 먼저 편안하게 말을 건네고 상대의 반응을 천천히 확인해보세요.',
            'work': '업무와 학업에서는 들뜬 마음 때문에 집중력이 조금 흔들릴 수 있어요. 중요한 일은 미리 정리해두면 하루의 균형을 지키기 좋습니다.',
            'money': '금전운에서는 약속이나 연락을 계기로 기분 좋은 지출이 생길 수 있어요. 식사나 이동 비용처럼 작은 예산을 미리 생각해두면 부담이 줄어듭니다.',
            'success': '성공에서는 감정의 흐름을 잘 다루는 것이 목표 유지에 도움이 됩니다. 오늘 끝낼 작은 일을 먼저 처리하면 설렘과 현실감이 함께 잡힙니다.',
            'general': '총운에서는 관계의 기대감과 현실적인 일정 관리가 함께 중요해 보여요. 마음은 부드럽게 열되 생활 리듬과 지출 계획도 같이 챙겨보세요.',
        }

    if has_question and focus_topic == 'work':
        return {
            'relationship': '관계운에서는 바쁜 마음 때문에 표현이 짧아질 수 있어요. 주변 사람에게 필요한 말은 미루지 말고 차분하게 전해보세요.',
            'work': '업무와 학업에서는 성급한 결론보다 준비와 순서 정리가 중요한 흐름이에요. 오늘 해야 할 일을 작게 나누면 부담이 줄고 실행이 쉬워집니다.',
            'money': '금전운에서는 업무나 공부에 필요한 지출을 점검해보면 좋습니다. 필요한 비용과 미룰 수 있는 소비를 나누면 안정감이 생깁니다.',
            'success': '성공에서는 결과보다 과정을 다지는 태도가 더 중요해요. 작은 성취를 쌓는 방식이 지금의 흐름과 잘 맞습니다.',
            'general': '총운에서는 해야 할 일을 정리하면서 마음의 속도를 낮추는 것이 좋아요. 관계와 지출도 무리하지 않는 선에서 균형을 맞춰보세요.',
        }

    if has_question and focus_topic == 'money':
        return {
            'relationship': '관계운에서는 돈 이야기를 꺼낼 때 감정보다 기준을 먼저 세우는 편이 좋아요. 필요한 부분은 부드럽지만 분명하게 말해보세요.',
            'work': '업무와 학업에서는 금전적인 고민이 집중력을 흔들 수 있어요. 중요한 일은 짧게라도 먼저 처리해두면 마음이 한결 가벼워집니다.',
            'money': '금전운에서는 지출과 수입의 균형을 다시 보는 흐름이에요. 충동적인 선택보다 필요한 것부터 정리하면 안정감을 찾기 쉽습니다.',
            'success': '성공에서는 당장의 이익보다 꾸준히 유지할 수 있는 계획이 중요합니다. 작은 목표와 예산을 함께 세우면 흐름이 안정됩니다.',
            'general': '총운에서는 현실적인 관리가 마음의 안정으로 이어지는 날이에요. 감정에 끌려 움직이기보다 계획을 먼저 확인해보세요.',
        }

    if has_question and focus_topic == 'success':
        return {
            'relationship': '관계운에서는 목표에 몰두하느라 주변의 반응을 놓치지 않는 것이 좋아요. 필요한 도움이나 응원은 편하게 요청해보세요.',
            'work': '업무와 학업에서는 목표를 이루기 위한 실행 순서가 중요합니다. 오늘 바로 할 수 있는 단계부터 처리하면 흐름이 살아납니다.',
            'money': '금전운에서는 목표를 위해 필요한 지출과 불필요한 소비를 구분해보세요. 준비에 도움이 되는 비용은 계획 안에서 쓰는 편이 좋습니다.',
            'success': '성공에서는 큰 결과보다 준비와 꾸준함이 더 강하게 보입니다. 서두르지 말고 작은 성취를 차곡차곡 쌓아보세요.',
            'general': '총운에서는 목표 의식이 하루 전체를 이끄는 흐름이에요. 관계와 지출, 생활 리듬까지 함께 정리하면 더 안정적으로 나아갈 수 있습니다.',
        }

    return {
        'relationship': '관계운에서는 속도보다 분위기와 표현 방식이 중요해요. 감정을 서두르기보다 대화와 거리감을 차분히 맞춰보세요.',
        'work': '업무와 학업운에서는 집중할 일을 먼저 정리하는 편이 좋습니다. 작은 우선순위를 세우면 하루가 덜 흔들립니다.',
        'money': '금전운에서는 들어오고 나가는 흐름을 함께 살피는 것이 필요해요. 충동적인 선택보다 계획 안에서 움직이면 안정적입니다.',
        'success': '성공에서는 큰 결과보다 준비와 꾸준함이 더 중요해 보여요. 오늘 끝낼 수 있는 작은 목표를 먼저 정해보세요.',
        'general': '총운에서는 마음의 흐름과 현실적인 선택을 함께 보는 것이 좋아요. 관계, 업무, 금전, 목표를 따로 살피며 균형을 잡아보세요.',
    }


def normalize_category_advices(category_advices, fallback_advices, question_analysis):
    category_advices = try_parse_json_text(category_advices)
    if not isinstance(category_advices, dict):
        category_advices = {}

    defaults = {
        'relationship': ['가까운 사람에게 먼저 짧게 안부를 건네보세요.'],
        'work': ['오늘 해야 할 일 한 가지를 정해서 먼저 끝내보세요.'],
        'money': ['오늘 쓸 금액의 기준을 미리 정해보세요.'],
        'success': ['목표를 작게 나눠 오늘 끝낼 수 있는 한 가지를 정해보세요.'],
        'general': ['마음이 앞서는 부분과 현실적으로 챙길 부분을 나눠 적어보세요.'],
    }

    normalized = {}
    for key, default_values in defaults.items():
        values = category_advices.get(key)
        if not isinstance(values, list) or not values:
            values = default_values

        normalized[key] = [ensure_advice_link(key, value, question_analysis) for value in values[:1] if ensure_advice_link(key, value, question_analysis)]
        if not normalized[key]:
            normalized[key] = [ensure_advice_link(key, value, question_analysis) for value in default_values]

    return normalized


def normalize_card_readings(card_readings, cards):
    normalized = []

    for index, card in enumerate(cards):
        raw = card_readings[index] if index < len(card_readings) else {}

        if isinstance(raw, dict):
            card_name = raw.get('card_name') or card.get('card_name_ko') or ''
            defined_meaning = raw.get('defined_meaning') or card.get('card_meaning') or ''
            interpretation = raw.get('interpretation') or card.get('topic_meaning') or defined_meaning
        else:
            card_name = card.get('card_name_ko') or ''
            defined_meaning = card.get('card_meaning') or ''
            interpretation = str(raw).strip() or card.get('topic_meaning') or defined_meaning

        normalized.append({
            'card_name': card_name,
            'defined_meaning': defined_meaning,
            'interpretation': interpretation,
        })

    return normalized


def split_llm_result(llm_data, cards, question_analysis=None):
    question_analysis = question_analysis or {}
    llm_data = extract_json_object(llm_data)
    if not isinstance(llm_data, dict):
        llm_data = {}

    category_results = llm_data.get('category_results', {})
    category_results = extract_json_object(category_results)
    card_readings = llm_data.get('card_readings', [])
    card_readings = try_parse_json_text(card_readings)
    action_advice = llm_data.get('action_advice', [])
    action_advice = try_parse_json_text(action_advice)
    category_advices = llm_data.get('category_advices', {})
    disclaimer = DISCLAIMER_TEXT

    if not isinstance(category_results, dict):
        category_results = {}

    if not isinstance(card_readings, list):
        card_readings = []

    if isinstance(action_advice, str):
        action_advice = [action_advice] if action_advice.strip() else []
    elif not isinstance(action_advice, list):
        action_advice = []

    fallback_results = build_fallback_category_results(cards, question_analysis)
    for key in ['relationship', 'work', 'money', 'success', 'general']:
        category_results.setdefault(key, '')
        value = extract_json_object(category_results[key])
        if isinstance(value, dict):
            nested_results = value.get('category_results', {})
            if isinstance(nested_results, dict):
                value = nested_results.get(key, '')

        cleaned_value = ensure_question_link(key, value, question_analysis)
        cleaned_value = remove_card_names(cleaned_value, cards) if cleaned_value else ''
        if cleaned_value:
            category_results[key] = cleaned_value
        elif not category_results.get(key):
            category_results[key] = fallback_results[key]

    action_advice = [sanitize_korean_text(value, 500) for value in action_advice[:5] if sanitize_korean_text(value, 500)]
    category_advices = normalize_category_advices(category_advices, action_advice, question_analysis)
    card_readings = normalize_card_readings(card_readings, cards)

    combined_summary = category_results.get('general', '')

    return {
        'combined_summary': combined_summary,
        'llm_advice': combined_summary,
        'one_line_message': '',
        'disclaimer': disclaimer,
        'category_results': category_results,
        'card_readings': card_readings,
        'action_advice': action_advice,
        'category_advices': category_advices,
    }

@transaction.atomic
def save_reading(user, question, topic, cards, llm_parts):
    user_id = user.id if user and user.is_authenticated else None

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO tarot_readings (
                user_id,
                question,
                topic,
                combined_summary,
                llm_advice,
                one_line_message,
                disclaimer,
                model_name,
                prompt_version
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            [
                user_id,
                question,
                topic,
                llm_parts['combined_summary'],
                llm_parts['llm_advice'],
                llm_parts['one_line_message'],
                llm_parts['disclaimer'],
                MODEL_NAME,
                PROMPT_VERSION,
            ],
        )
        reading_id = cursor.fetchone()[0]

        for card in cards:
            cursor.execute(
                """
                INSERT INTO tarot_reading_cards (
                    reading_id,
                    card_number,
                    position_key,
                    position_label,
                    orientation,
                    card_order,
                    card_meaning,
                    topic_meaning,
                    advice_seed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    reading_id,
                    card['card_number'],
                    card['position_key'],
                    card['position_label'],
                    card['orientation'],
                    card['card_order'],
                    card['card_meaning'],
                    card['topic_meaning'],
                    card['advice_seed'],
                ],
            )

    return reading_id


def create_reading(data, user=None):
    requested_topic = data.get('topic', 'general')
    question = data.get('question', '').strip()
    question_analysis = analyze_question(question, requested_topic)
    retrieval_topic = normalize_topic(question_analysis['focus_topic'])
    user_profile = {
        'birth_date': data.get('birth_date') or '',
        'gender': data.get('gender') or '',
        'age': data.get('age') or '',
    }
    selected_cards = draw_reading_cards(data.get('card_numbers'))

    db_cards = fetch_cards(selected_cards)
    cards = build_card_payload(selected_cards, db_cards, retrieval_topic)
    retrieved_context = fetch_chunks(cards, retrieval_topic)

    prompt = build_tarot_prompt(
        question=question,
        topic=requested_topic,
        cards=cards,
        retrieved_context=retrieved_context,
        user_profile=user_profile,
        question_analysis=question_analysis,
    )

    llm_text = call_llm(prompt)
    llm_parts = split_llm_result(llm_text, cards, question_analysis)

    reading_id = save_reading(
        user=user,
        question=question,
        topic=requested_topic,
        cards=cards,
        llm_parts=llm_parts,
    )

    return {
        'reading_id': reading_id,
        'topic': requested_topic,
        'question': question,
        'cards': cards,
        'combined_summary': llm_parts['combined_summary'],
        'llm_advice': llm_parts['llm_advice'],
        'one_line_message': llm_parts['one_line_message'],
        'disclaimer': llm_parts['disclaimer'],
        'category_results': llm_parts['category_results'],
        'card_readings': llm_parts['card_readings'],
        'action_advice': llm_parts['action_advice'],
        'category_advices': llm_parts['category_advices'],
    }

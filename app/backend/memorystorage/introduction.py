"""기억 그래프를 자연스러운 한국어 소개 문장으로 구성한다."""

from datetime import date, datetime

from .constants import (
    DEFAULT_PREFERENCE_POLARITY,
    DEFAULT_RELATION_NAME,
    EMPTY_MEMORY_DESCRIPTION,
    EMPTY_MEMORY_TITLE,
    NEGATIVE_PREFERENCE_POLARITIES,
    NEUTRAL_PREFERENCE_POLARITIES,
    SOURCE_ONLY_DESCRIPTION,
)

def build_memory_title(unit):
    names = [event.get('name') for event in unit['events'] if event.get('name')]
    if names:
        return names[0] if len(names) == 1 else f"{names[0]} 외 {len(names) - 1}건"
    if unit['relations']:
        relation = unit['relations'][0]
        return f"{relation.get('name')}와의 관계"
    if unit['preferences']:
        return f"{unit['preferences'][0].get('topic')} 취향"
    return EMPTY_MEMORY_TITLE


def _join_korean(values):
    values = [str(value) for value in values if value not in (None, '')]
    if len(values) < 2:
        return values[0] if values else ''
    return ', '.join(values[:-1]) + ' 그리고 ' + values[-1]


def _particle(value, with_batchim, without_batchim):
    text = str(value or '')
    if not text:
        return without_batchim
    code = ord(text[-1])
    has_batchim = 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0
    return with_batchim if has_batchim else without_batchim


def _format_korean_date(value):
    if value in (None, ''):
        return ''
    if isinstance(value, (date, datetime)):
        parsed = value
    else:
        text = str(value)
        try:
            parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            try:
                parsed = date.fromisoformat(text[:10])
            except ValueError:
                return text
    return f'{parsed.year}년 {parsed.month}월 {parsed.day}일'


def _event_date_text(event):
    start = event.get('occurs_start')
    end = event.get('occurs_end')
    if start:
        start_text = _format_korean_date(start)
        if end and end != start:
            return f'{start_text}부터 {_format_korean_date(end)}까지'
        return start_text

    dates = []
    for item in event.get('dates', []):
        date_text = _format_korean_date(item.get('date'))
        if date_text and date_text not in dates:
            dates.append(date_text)
    return _join_korean(dates)


def _person_text(person):
    relation = person.get('relation')
    return (
        f"{relation} {person['name']}"
        if relation else person['name']
    )


def _unique_texts(values):
    unique = []
    seen = set()
    for value in values:
        text = ' '.join(str(value or '').split())
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            unique.append(text)
    return unique


def _join_clauses(values):
    values = _unique_texts(values)
    if len(values) < 2:
        return values[0] if values else ''
    return ', '.join(values[:-1]) + ', 그리고 ' + values[-1]


def _join_nouns(values):
    values = _unique_texts(values)
    if len(values) < 2:
        return values[0] if values else ''
    if len(values) == 2:
        conjunction = _particle(values[0], '과', '와')
        return f'{values[0]}{conjunction} {values[1]}'
    return ', '.join(values[:-1]) + ' 그리고 ' + values[-1]


def _normalised_phrase(value):
    return ''.join(
        char for char in str(value or '').casefold()
        if char.isalnum()
    )


def _event_date_value(event):
    value = event.get('occurs_start')
    if not value:
        value = next(
            (
                item.get('date')
                for item in (event.get('dates') or [])
                if item.get('date')
            ),
            None,
        )
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return None


def _event_context_values(event, key):
    if key == 'people':
        values = (
            person.get('name')
            for person in (event.get('people') or [])
            if person.get('name')
        )
    else:
        values = event.get(key) or []
    return {
        _normalised_phrase(value)
        for value in values
        if _normalised_phrase(value)
    }


def _event_transition(previous, current):
    """두 사건 사이의 실제 공통 맥락을 짧은 연결어로 바꾼다."""
    previous_date = _event_date_value(previous)
    current_date = _event_date_value(current)
    if previous_date and current_date:
        if previous_date == current_date:
            return '같은 날, '
        if previous_date < current_date:
            return '그 뒤로, '
        return '그보다 앞서, '

    if _event_context_values(previous, 'people') & _event_context_values(current, 'people'):
        return '같은 사람과 이어진 일로, '
    if _event_context_values(previous, 'places') & _event_context_values(current, 'places'):
        return '같은 장소에서 이어진 일로, '
    if _event_context_values(previous, 'topics') & _event_context_values(current, 'topics'):
        return '이와 관련해, '
    return '한편, '


def _event_story_sentences(events):
    sentences = []
    previous = None
    for event in events:
        transition = ''
        omit_date = False
        if previous is not None:
            transition = _event_transition(previous, event)
            previous_date = _event_date_value(previous)
            current_date = _event_date_value(event)
            omit_date = bool(previous_date and previous_date == current_date)
        introduction = f'{transition}{_event_intro(event, omit_date=omit_date)}'
        sentences.append(introduction)
        sentences.extend(_event_detail_sentences(event))
        previous = event
    return sentences


def _cause_lead(event):
    cause_text = ' '.join(str(event.get('cause') or '').split()).rstrip('.!?')
    if cause_text:
        if cause_text.endswith(('때문에', '덕분에', '탓에', '로 인해')):
            return f'{cause_text} '
        if cause_text.endswith(('서', '고', '며', '데')):
            return f'{cause_text}, '
        return f'“{cause_text}”라는 이유로, '

    causes = _unique_texts(
        cause.get('name') for cause in (event.get('causes') or [])
        if cause.get('name')
    )
    if not causes:
        return ''
    quoted_causes = [f'‘{name}’' for name in causes]
    subject_particle = _particle(causes[-1], '이', '가')
    return f"{_join_nouns(quoted_causes)}{subject_particle} 계기가 되어, "


def _event_intro(event, *, omit_date=False):
    event_name = str(event.get('name') or '').strip()
    date_text = '' if omit_date else _event_date_text(event)
    places = _unique_texts(event.get('places') or [])
    people = _unique_texts(
        _person_text(person) for person in (event.get('people') or [])
        if person.get('name')
    )
    quoted_name = f'‘{event_name}’' if event_name else '이 일'
    cause_lead = _cause_lead(event)

    if date_text:
        date_context = date_text if date_text.endswith('까지') else f'{date_text}에'
        context = [date_context]
        if people:
            context.append(f'{_join_nouns(people)}와')
        if places:
            context.append(f'{_join_nouns(places)}에서')
        object_particle = _particle(event_name, '을', '를')
        if people:
            return (
                f"{cause_lead}{' '.join(context)} {quoted_name}{object_particle} "
                "함께하기로 했던 기억이에요."
            )
        return (
            f"{cause_lead}{' '.join(context)} {quoted_name}{object_particle} "
            "예정했던 기억이에요."
        )
    if people and places:
        return (
            f"{cause_lead}{_join_nouns(places)}에서 {_join_nouns(people)}와 "
            f"함께한 {quoted_name}에 대한 기억이에요."
        )
    if people:
        return (
            f"{cause_lead}{_join_nouns(people)}와 함께한 "
            f"{quoted_name}에 대한 기억이에요."
        )
    if places:
        return (
            f"{cause_lead}{_join_nouns(places)}에서 있었던 "
            f"{quoted_name}에 대한 기억이에요."
        )
    return f"{cause_lead}{quoted_name}에 대해 이야기했던 기억이에요."


def _event_detail_sentences(event):
    sentences = []
    topics = _unique_texts(event.get('topics') or [])
    subject = '이 계획' if _event_date_text(event) else '이 기억'
    if topics:
        joined_topics = _join_nouns(topics)
        topic_particle = _particle(joined_topics, '과', '와')
        sentences.append(
            f"{subject}은 {joined_topics}{topic_particle} 관련되어 있었어요."
        )

    membership = (
        event.get('graph', {})
        .get('has_event', {})
        .get('properties', {})
    )
    valid_to = membership.get('valid_to')
    if valid_to:
        ended_at = _format_korean_date(valid_to)
        reason = str(membership.get('end_reason') or '').strip()
        ending = f'{ended_at}에 ' if ended_at else ''
        if reason:
            ending += f'{reason}의 이유로 '
        sentences.append(f"이 일은 {ending}마무리된 것으로 기록되어 있어요.")
    return sentences


def _relation_sentences(relations, event_people):
    active = []
    ended = []
    event_people = {
        _normalised_phrase(name) for name in event_people if name
    }
    for relation in relations:
        name = str(relation.get('name') or '').strip()
        if not name:
            continue
        relation_name = str(
            relation.get('relation') or DEFAULT_RELATION_NAME
        ).strip()
        if relation.get('valid_to'):
            ended_at = _format_korean_date(relation.get('valid_to'))
            reason = str(relation.get('end_reason') or '').strip()
            detail = f"{name}와의 {relation_name} 관계는"
            if ended_at:
                detail += f" {ended_at}에"
            if reason:
                detail += f" {reason}의 이유로"
            ended.append(f"{detail} 마무리된 것으로 기록되어 있어요.")
        elif _normalised_phrase(name) not in event_people:
            subject = f"{name}{_particle(name, '은', '는')}"
            active.append(f"{subject} {relation_name}로")

    sentences = []
    if active:
        sentences.append(f"{_join_clauses(active)} 기억하고 있어요.")
    sentences.extend(ended)
    return sentences


def _preference_sentences(preferences):
    current = {'positive': [], 'negative': [], 'neutral': []}
    ended = []
    for preference in preferences:
        topic = str(preference.get('topic') or '').strip()
        if not topic:
            continue
        polarity = str(
            preference.get('polarity') or DEFAULT_PREFERENCE_POLARITY
        ).lower()
        if polarity in NEGATIVE_PREFERENCE_POLARITIES:
            bucket = 'negative'
        elif polarity in NEUTRAL_PREFERENCE_POLARITIES:
            bucket = 'neutral'
        else:
            bucket = 'positive'
        if preference.get('valid_to'):
            ended.append((topic, bucket))
        else:
            current[bucket].append(topic)

    clauses = []
    positive = _unique_texts(current['positive'])
    if positive:
        joined = _join_nouns(positive)
        clauses.append(f"{joined}{_particle(joined, '을', '를')} 좋아하고")
    negative = _unique_texts(current['negative'])
    if negative:
        joined = _join_nouns(negative)
        clauses.append(
            f"{joined}{_particle(joined, '은', '는')} 선호하지 않는"
        )
    neutral = _unique_texts(current['neutral'])
    if neutral:
        joined = _join_nouns(neutral)
        clauses.append(
            f"{joined}{_particle(joined, '은', '는')} 중립적으로 느끼는"
        )

    sentences = []
    if clauses:
        if len(clauses) == 1 and positive:
            sentence = f"평소 {clauses[0][:-1]}는 취향도 함께 기억하고 있어요."
        else:
            sentence = (
                f"평소 {', '.join(clauses)} 취향도 함께 기억하고 있어요."
            )
        sentences.append(sentence)
    if ended:
        topics = _unique_texts(topic for topic, _ in ended)
        joined = _join_nouns(topics)
        particle = _particle(joined, '은', '는')
        sentences.append(
            f"과거의 취향이었던 {joined}{particle} 지금은 종료된 기록이에요."
        )
    return sentences


def build_memory_introduction(unit):
    """연결 그래프를 원인과 중심 사건이 이어지는 하나의 이야기로 구성한다."""
    sections = {
        'source': [],
        'events': [],
        'relations': [],
        'preferences': [],
    }
    source_text = ' '.join(str(unit.get('source_text') or '').split())
    cause_names = {
        _normalised_phrase(cause.get('name'))
        for event in unit.get('events', [])
        for cause in (event.get('causes') or [])
        if cause.get('name')
    }
    event_people = []
    narrative_events = []
    for event in unit.get('events', []):
        event_name_key = _normalised_phrase(event.get('name'))
        if event_name_key in cause_names:
            event_people.extend(
                person.get('name') for person in (event.get('people') or [])
                if person.get('name')
            )
            continue
        narrative_events.append(event)
        event_people.extend(
            person.get('name') for person in (event.get('people') or [])
            if person.get('name')
        )
    if not narrative_events and unit.get('events'):
        narrative_events = list(unit['events'])
    sections['events'].extend(_event_story_sentences(narrative_events))

    sections['relations'].extend(
        _relation_sentences(unit.get('relations', []), event_people)
    )
    sections['preferences'].extend(
        _preference_sentences(unit.get('preferences', []))
    )

    has_structured_context = any(
        sections[key] for key in ('events', 'relations', 'preferences')
    )
    if source_text and not has_structured_context:
        sections['source'].append(SOURCE_ONLY_DESCRIPTION)

    paragraphs = [
        sentence
        for key in ('events', 'relations', 'preferences', 'source')
        for sentence in sections[key]
        if sentence
    ]
    if not paragraphs:
        paragraphs.append(EMPTY_MEMORY_DESCRIPTION)
    narrative_text = ' '.join(paragraphs)
    sections['narrative_text'] = narrative_text
    sections['original_text'] = source_text
    sections['text'] = narrative_text
    return sections

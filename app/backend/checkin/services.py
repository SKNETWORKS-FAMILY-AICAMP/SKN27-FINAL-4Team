from datetime import timedelta
import json
import logging
import os
import random
import re

from django.db.models import Avg, Count, Min
from django.utils import timezone

from user.models import UserPreferenceKeyword

from .models import (
    ActionFeedback,
    CauseOption,
    CauseContextConfig,
    CheckinRecommendation,
    DailyCheckin,
    DialogueTemplate,
    NeedOption,
    RecommendationAction,
    ReflectionOption,
)


logger = logging.getLogger(__name__)


CHARACTER_MAP = {
    'pori': ('redpanda', '포리'),
    'kkami': ('cat', '까미'),
    'toto': ('otter', '토토'),
    'yeoul': ('bird', '여울'),
    'redpanda': ('redpanda', '포리'),
    'cat': ('cat', '까미'),
    'otter': ('otter', '토토'),
    'bird': ('bird', '여울'),
}
BACKEND_CHARACTER_BY_ASSET = {'redpanda': 'pori', 'cat': 'kkami', 'otter': 'toto', 'bird': 'yeoul'}
EMOTION_EXPRESSION = {'JOY': 'joy', 'SADNESS': 'sadness', 'ANGER': 'anger', 'ANXIETY': 'anxiety'}


def backend_character_id(value):
    return BACKEND_CHARACTER_BY_ASSET.get(value or '', value or 'pori')


def _label_from_value(value):
    if isinstance(value, dict):
        return str(value.get('label') or value.get('name') or value.get('title') or value.get('keyword') or value.get('id') or '').strip()
    return str(value or '').strip()


def _dedupe_labels(values):
    result = []
    seen = set()
    for value in values:
        label = _label_from_value(value)
        key = label.casefold()
        if label and key not in seen:
            result.append(label)
            seen.add(key)
    return result


def user_preference_groups(user):
    interests = []
    hobbies = []
    try:
        profile = user.profile
        interests.extend(profile.interests or [])
        hobbies.extend(profile.hobbies or [])
    except Exception:
        pass
    interests.extend(UserPreferenceKeyword.objects.filter(user=user, keyword_type='interest').values_list('label', flat=True))
    hobbies.extend(UserPreferenceKeyword.objects.filter(user=user, keyword_type='hobby').values_list('label', flat=True))
    return {
        'interests': _dedupe_labels(interests),
        'hobbies': _dedupe_labels(hobbies),
    }


def user_preferences(user):
    groups = user_preference_groups(user)
    return _dedupe_labels([*groups['interests'], *groups['hobbies']])


def character_payload(user, emotion='ANXIETY'):
    character_id = backend_character_id(getattr(user, 'character', '') or 'pori')
    asset_id, name = CHARACTER_MAP.get(character_id, CHARACTER_MAP['pori'])
    expression = EMOTION_EXPRESSION.get(emotion, 'default')
    return {
        'id': asset_id,
        'character_id': character_id,
        'name': name,
        'expression': expression,
        'image_url': f'/characters/{asset_id}/{expression}.png',
    }


def _template(stage):
    return DialogueTemplate.objects.filter(stage=stage, context_key='base').values_list('template', flat=True).first()


def cause_context_payload(context):
    config = CauseContextConfig.objects.filter(cause_context=context).first()
    if not config:
        return {
            'cause_context': context,
            'cause_title': '마음에 걸린 원인',
            'cause_question': '오늘 마음에 남은 건 뭐였어?',
            'show_cause_options': context != 'SKIP',
            'next_stage': 'NEED' if context == 'SKIP' else 'CAUSE',
        }
    return {
        'cause_context': config.cause_context,
        'cause_title': config.title,
        'cause_question': config.question_text,
        'show_cause_options': config.show_cause_options,
        'next_stage': config.next_stage,
        'cause_description': config.description,
    }


def cause_options_for(context):
    if not context or context == 'SKIP':
        return []
    config = CauseContextConfig.objects.filter(cause_context=context).first()
    field = config.option_text_field if config else f'option_text_{context.lower()}'
    options = []
    for item in CauseOption.objects.filter(enabled=True):
        if context not in (item.available_contexts or []):
            continue
        text = getattr(item, field, '') or item.label
        options.append({
            'id': item.cause_id,
            'cause_id': item.cause_id,
            'cause_code': item.cause_code,
            'label': text,
            'display_text': text,
            'hint': item.examples_internal,
            'icon': item.icon,
            'display_order': item.display_order,
            'available_contexts': item.available_contexts,
        })
    return options


def dialogue_for(checkin, stage):
    reflection = checkin.reflection.label if checkin.reflection_id else ''
    cause = checkin.cause_display_text_snapshot or (checkin.cause.label if checkin.cause_id else '')
    need = checkin.need.label if checkin.need_id else ''
    context = checkin.cause_context or 'DIFFICULT'
    if stage == 'CAUSE':
        template = DialogueTemplate.objects.filter(stage='CAUSE_PROMPT', context_key=context).values_list('template', flat=True).first()
        config = cause_context_payload(context)
        return template or f'{reflection}라고 느꼈구나. {config["cause_question"]}'
    if stage == 'NEED' and context == 'SKIP':
        return cause_context_payload('SKIP')['cause_question']
    fallback = {
        'REFLECTION': '오늘 하루 어땠어? 천천히 떠올려보고, 가장 가까운 느낌 하나를 골라줘.',
        'CAUSE': f'{reflection}라고 느꼈구나. 그 마음에 가까이 닿아 있는 장면을 하나 골라볼까?',
        'NEED': f'{cause}이 마음에 남았구나. 지금의 나에게 어떤 도움이 가장 편안할지 골라줘.',
        'RECOMMENDATION': f'{need}을 원한다고 골랐어. 관심사 두 가지와 취미 두 가지를 섞어서 오늘 해볼 만한 행동을 골라봤어.',
        'FINAL_ROUTE': '추천을 살펴봤어. 캐릭터와 더 이야기할지, 행동을 시작할지, 오늘 기록만 남길지 골라줘.',
        'COMPLETED': '오늘의 이야기를 잘 남겨두었어. 필요한 순간에 다시 이 기록으로 돌아와도 좋아.',
    }
    text = _template(stage) or fallback.get(stage, fallback['REFLECTION'])
    return text.format(reflection=reflection, cause=cause, need=need)


def option_payloads(cause_context=None):
    return {
        'reflection': list(ReflectionOption.objects.filter(enabled=True).values(
            'reflection_id', 'label', 'hint', 'icon', 'primary_emotion', 'secondary_emotion', 'emotion_intensity_default', 'state_tags', 'energy_level', 'cause_context', 'ack_key', 'next_stage', 'include_weekly', 'display_order')),
        'cause': cause_options_for(cause_context),
        'need': list(NeedOption.objects.filter(enabled=True).values(
            'need_id', 'need_code', 'label', 'hint', 'icon', 'response_mode', 'display_order')),
    }


def _sample_preference_groups(groups, rng):
    interests = list(groups.get('interests') or [])
    hobbies = list(groups.get('hobbies') or [])
    rng.shuffle(interests)
    rng.shuffle(hobbies)
    sampled_interests = interests[:2]
    sampled_hobbies = hobbies[:2]
    combined = _dedupe_labels([*sampled_interests, *sampled_hobbies])
    if len(combined) < 4:
        combined = _dedupe_labels([*combined, *interests[2:], *hobbies[2:]])[:4]
    return {
        'interests': sampled_interests,
        'hobbies': sampled_hobbies,
        'combined': combined,
    }


def _json_from_text(text):
    stripped = str(text or '').strip()
    if stripped.startswith('```'):
        stripped = stripped.strip('`')
        if stripped.lower().startswith('json'):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find('{')
        end = stripped.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(stripped[start:end])
    return {}


def _safe_action_id(checkin, rank, title):
    slug = re.sub(r'[^A-Z0-9]+', '-', str(title or '').upper())[:14].strip('-') or 'ACTION'
    return f'LLM-{checkin.id}-{rank}-{slug}'[:50]


def _feedback_guidance(user):
    feedback_rows = list(
        ActionFeedback.objects.filter(checkin__user=user)
        .select_related('action')
        .order_by('-feedback_at')[:30]
    )
    return [
        {
            'action_id': row.action.action_id,
            'title': row.action.title,
            'tags': row.action.tags or [],
            'helpfulness': row.helpfulness,
            'completed': row.completed,
        }
        for row in feedback_rows
    ]


def _age_group(age):
    try:
        age = int(age)
    except (TypeError, ValueError):
        return ''
    return f'{(age // 10) * 10}대'


def _profile_recommendation_context(user, groups):
    try:
        profile = user.profile
    except Exception:
        profile = None
    return {
        'age_group': _age_group(getattr(profile, 'age', None)),
        'job': str(getattr(profile, 'job', '') or '').strip(),
        'hobbies': groups.get('hobbies') or [],
        'interests': groups.get('interests') or [],
    }


def _llm_generated_actions(checkin, user, sampled, rng):
    if not os.getenv('OPENAI_API_KEY'):
        return []
    try:
        from openai import OpenAI
    except Exception:
        return []

    payload = {
        'profile': _profile_recommendation_context(user, user_preference_groups(user)),
        'today_checkin': {
            'reflection': checkin.reflection.label if checkin.reflection else '',
            'primary_emotion': checkin.primary_emotion,
            'cause_context': checkin.cause_context,
            'cause': checkin.cause_display_text_snapshot or (checkin.cause.label if checkin.cause else ''),
            'need': checkin.need.label if checkin.need else '',
            'energy_level': checkin.energy_level,
        },
        'sampled_interests': sampled['interests'],
        'sampled_hobbies': sampled['hobbies'],
        'random_seed': rng.randint(1000, 999999),
        'previous_action_feedback': _feedback_guidance(user),
    }
    system = (
        '너는 사용자의 오늘 기분과 취향을 바탕으로 작고 안전한 행동을 추천하는 한국어 코치다. '
        '진단, 치료, 과격한 운동, 지출이 큰 행동은 피한다. 매번 새롭고 구체적인 행동을 만든다. '
        '각 추천은 사용자가 제공한 취미 또는 관심 주제 한 개를 직접 활용해야 하며, 현실에서 바로 할 수 있는 일이어야 한다. '
        '키워드를 기계적으로 문장에 붙이지 말고 그 활동의 실제 맥락을 이해해서 제안한다. '
        '반드시 JSON 객체만 반환한다.'
    )
    human = {
        'task': '오늘의 나 돌아보기 행동 추천 4개 생성',
        'rules': [
            '관심사 기반 2개, 취미 기반 2개를 만든다.',
            '시간은 활동의 현실적인 최소 단위로 정한다. 짧은 행동은 5~15분, 운동·경기·외출은 준비 시간을 고려해 30~90분도 가능하다.',
            'title은 18자 안팎, description은 한 문장, reason은 왜 맞는지 한 문장으로 쓴다.',
            '사용자가 이미 고른 감정/원인/필요한 도움을 반영한다.',
            '반드시 각 항목의 source_keyword에 input에 있는 취미 또는 관심 주제 중 정확히 하나를 넣고, 제목·설명에도 그 키워드와 실제로 연결된 행동을 쓴다.',
            '현실적으로 불가능하거나 부자연스러운 표현은 금지한다. 예: "헬스 한 장면 남기기", "애완동물 짧게 키우기", "연애 짧게 즐기기"는 금지한다.',
            '대신 헬스는 "헬스장에서 40분 웨이트하기", 배드민턴은 "친구와 1게임 치기", 반려동물은 "반려동물 카페 방문하기"처럼 실제로 가능한 대안을 쓴다.',
            '이전 행동 평가에서 1~2점을 받은 행동과 비슷한 행동은 피한다.',
            '4~5점을 받은 행동의 특징이나 키워드는 상황에 맞으면 조금 더 적극적으로 활용한다.',
            '이전 평가가 없거나 현재 마음과 맞지 않으면 평가보다 현재 선택을 우선한다.',
            '출력은 {"actions":[...]} 형식만 사용한다.',
        ],
        'input': payload,
        'schema': {
            'actions': [
                {
                    'title': 'string',
                    'description': 'string',
                    'duration': '예: 5분',
                    'icon': 'emoji',
                    'tags': ['관심사 또는 취미', '키워드'],
                    'reason': 'string',
                    'source': 'interest | hobby',
                    'source_keyword': 'input에 있는 취미 또는 관심 주제 문자열 하나',
                }
            ]
        },
    }
    try:
        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'].strip())
        response = client.chat.completions.create(
            model=os.getenv('CHECKIN_RECOMMENDATION_MODEL', 'gpt-4o-mini'),
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(human, ensure_ascii=False)},
            ],
            temperature=0.9,
            max_tokens=1200,
            response_format={'type': 'json_object'},
        )
        content = response.choices[0].message.content or ''
        parsed = _json_from_text(content)
        actions = parsed.get('actions') if isinstance(parsed, dict) else []
        if not isinstance(actions, list):
            return []

        allowed_by_source = {
            'interest': {label.casefold() for label in sampled['interests']},
            'hobby': {label.casefold() for label in sampled['hobbies']},
        }
        validated = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            source = str(action.get('source') or '').strip().lower()
            keyword = _label_from_value(action.get('source_keyword'))
            action_text = ' '.join(str(action.get(field) or '') for field in ('title', 'description', 'reason', 'tags'))
            if source not in allowed_by_source or keyword.casefold() not in allowed_by_source[source]:
                continue
            if keyword.casefold() not in action_text.casefold():
                continue
            validated.append(action)
        return validated
    except Exception:
        logger.exception('오늘의 나 돌아보기 행동 추천 LLM 호출에 실패했습니다.')
        return []


def _fallback_generated_actions(checkin, sampled):
    """LLM 응답이 없을 때도 오늘 바로 할 수 있는 안전한 네 가지를 제공한다."""
    keywords = list(sampled.get('combined') or [])
    if not keywords:
        keywords = ['지금의 마음']

    def keyword_at(index):
        return keywords[index % len(keywords)]

    need = checkin.need.label if checkin.need else '지금 필요한 도움'
    return [
        {
            'title': '관심 장면 10분 보기',
            'description': f'“{keyword_at(0)}”와 관련해 편하게 볼 수 있는 콘텐츠 하나를 10분만 골라보세요.',
            'duration': '10분',
            'reason': f'{need}에 맞춰 저장한 관심사 “{keyword_at(0)}”를 부담 없이 연결했어요.',
            'icon': '✨',
            'tags': [keyword_at(0), '가벼운 시작'],
            'source': 'interest' if keyword_at(0) in sampled.get('interests', []) else 'hobby',
            'source_keyword': keyword_at(0),
        },
        {
            'title': '몸의 긴장 5분 풀기',
            'description': '어깨와 목을 천천히 움직이고, 숨을 네 번 고르며 몸의 힘을 조금만 풀어보세요.',
            'duration': '5분',
            'reason': f'{need}에 맞춰 바로 멈추거나 줄일 수 있는 작은 움직임을 골랐어요.',
            'icon': '🧘',
            'tags': ['몸 돌보기', '5분'],
            'source': 'interest' if keyword_at(1) in sampled.get('interests', []) else 'hobby',
            'source_keyword': keyword_at(1),
        },
        {
            'title': '마음 한 줄 적기',
            'description': f'“{keyword_at(2)}”를 떠올리며 지금 마음에 남은 장면을 한 줄만 적어보세요.',
            'duration': '5분',
            'reason': f'오늘의 느낌을 정리하면서도 “{keyword_at(2)}” 취향을 자연스럽게 활용할 수 있어요.',
            'icon': '📝',
            'tags': [keyword_at(2), '마음 정리'],
            'source': 'interest' if keyword_at(2) in sampled.get('interests', []) else 'hobby',
            'source_keyword': keyword_at(2),
        },
        {
            'title': '좋아하는 것 15분 하기',
            'description': f'“{keyword_at(3)}”와 관련해 준비가 거의 필요 없는 작은 활동 하나만 15분 해보세요.',
            'duration': '15분',
            'reason': f'저장한 취향 “{keyword_at(3)}”을 오늘의 회복 시간으로 이어가도록 골랐어요.',
            'icon': '🌷',
            'tags': [keyword_at(3), '작은 즐거움'],
            'source': 'interest' if keyword_at(3) in sampled.get('interests', []) else 'hobby',
            'source_keyword': keyword_at(3),
        },
    ]


def _generated_action_records(checkin, user, sampled, rng):
    actions = _llm_generated_actions(checkin, user, sampled, rng)
    generated_by_llm = len(actions) >= 4
    if not generated_by_llm:
        actions = _fallback_generated_actions(checkin, sampled)

    records = []
    CheckinRecommendation.objects.filter(checkin=checkin).delete()
    for rank, raw in enumerate(actions[:4], start=1):
        title = str(raw.get('title') or f'작은 행동 {rank}').strip()[:180]
        description = str(raw.get('description') or '오늘의 마음에 맞춰 아주 작게 시작해보는 행동이에요.').strip()
        duration_text = str(raw.get('duration') or raw.get('expected_time') or '5분')
        minutes_match = re.search(r'\d+', duration_text)
        minutes = max(5, min(120, int(minutes_match.group()) if minutes_match else 15))
        tags = [str(item).strip() for item in (raw.get('tags') or []) if str(item).strip()][:4]
        source = str(raw.get('source') or '').lower()
        reason_code = 'INTEREST_MATCH' if source == 'interest' or '관심사' in tags else 'HOBBY_MATCH' if source == 'hobby' or '취미' in tags else 'PREFERENCE_DIRECT'
        action, _ = RecommendationAction.objects.update_or_create(
            action_id=_safe_action_id(checkin, rank, title),
            defaults={
                'title': title,
                'description': description,
                'expected_minutes': minutes,
                'icon': str(raw.get('icon') or '🌷')[:16],
                'tags': tags,
                'suitable_needs': [checkin.need_id] if checkin.need_id else [],
                'suitable_emotions': [checkin.primary_emotion] if checkin.primary_emotion else [],
                'energy_levels': [checkin.energy_level] if checkin.energy_level else [],
                'linked_keywords': sampled['combined'],
                'default_weight': 80 - rank,
                'safety_notice': '부담이 느껴지면 바로 멈춰도 괜찮아요.',
                'enabled': True,
            },
        )
        records.append(CheckinRecommendation.objects.create(
            checkin=checkin,
            action=action,
            score=100 - rank,
            rank=rank,
            reason_codes=[reason_code, 'LLM_RANDOM' if generated_by_llm else 'SAFE_FALLBACK'],
        ))
    return records


def score_recommendations(checkin, user):
    groups = user_preference_groups(user)
    rng = random.Random(f'{user.pk}:{checkin.pk}:{timezone.now().isoformat()}:{random.random()}')
    sampled = _sample_preference_groups(groups, rng)
    if not sampled['combined']:
        return []
    return _generated_action_records(checkin, user, sampled, rng)

    normalized_interests = {value.casefold() for value in groups['interests']}
    normalized_hobbies = {value.casefold() for value in groups['hobbies']}
    normalized_preferences = normalized_interests | normalized_hobbies
    recent_since = timezone.localdate() - timedelta(days=7)
    recent_ids = set(CheckinRecommendation.objects.filter(
        checkin__user=user,
        created_at__date__gte=recent_since,
    ).values_list('action_id', flat=True))
    feedback_stats = {
        item['action_id']: item
        for item in ActionFeedback.objects.filter(checkin__user=user).values('action_id').annotate(
            avg_helpfulness=Avg('helpfulness'),
            feedback_count=Count('id'),
            lowest_helpfulness=Min('helpfulness'),
        )
    }

    scored = []
    for action in RecommendationAction.objects.filter(enabled=True):
        avoid_emotions = {str(value).upper() for value in action.avoid_emotions or []}
        avoid_causes = {str(value).upper() for value in action.avoid_causes or []}
        if checkin.primary_emotion in avoid_emotions or (checkin.cause and checkin.cause.cause_code in avoid_causes):
            continue
        score = action.default_weight
        reason_codes = []
        linked = {str(value).casefold() for value in action.linked_keywords or []}
        matched_interest = bool(linked & normalized_interests)
        matched_hobby = bool(linked & normalized_hobbies)
        if matched_interest:
            score += 45
            reason_codes.append('INTEREST_MATCH')
        if matched_hobby:
            score += 45
            reason_codes.append('HOBBY_MATCH')
        if not matched_interest and not matched_hobby and linked & normalized_preferences:
            score += 40
            reason_codes.append('PREFERENCE_DIRECT')
        need_keys = {value for value in (checkin.need_id, getattr(checkin.need, 'need_code', '')) if value}
        if need_keys & set(action.suitable_needs or []):
            score += 30
            reason_codes.append('NEED_MATCH')
        if checkin.primary_emotion in (action.suitable_emotions or []):
            score += 20
            reason_codes.append('EMOTION_MATCH')
        if checkin.energy_level in (action.energy_levels or []):
            score += 20
            reason_codes.append('ENERGY_MATCH')
        elif checkin.energy_level == 'LOW' and 'HIGH' in (action.energy_levels or []):
            continue
        if action.action_id not in recent_ids:
            score += 10
            reason_codes.append('NOT_RECENT')
        else:
            score -= 10
            reason_codes.append('RECENTLY_SUGGESTED')
        stats = feedback_stats.get(action.action_id)
        if stats:
            avg = float(stats['avg_helpfulness'] or 0)
            count = int(stats['feedback_count'] or 0)
            lowest = int(stats['lowest_helpfulness'] or 0)
            if lowest <= 1 and avg <= 2 and count >= 1:
                continue
            if avg >= 4.5:
                score += 35
                reason_codes.append('VERY_HELPFUL_BEFORE')
            elif avg >= 3.5:
                score += 18
                reason_codes.append('HELPFUL_BEFORE')
            elif avg <= 2:
                score -= 35
                reason_codes.append('LOW_HELPFULNESS_BEFORE')
        source = 'interest' if matched_interest else 'hobby' if matched_hobby else 'general'
        scored.append((score, action.default_weight, action.action_id, action, reason_codes, source))

    def pick(pool, limit, used):
        ranked = [item for item in pool if item[2] not in used]
        ranked.sort(key=lambda item: (-(item[0] + rng.randint(0, 12)), -item[1], item[2]))
        result = ranked[:limit]
        used.update(item[2] for item in result)
        return result

    used_ids = set()
    chosen = []
    chosen.extend(pick([item for item in scored if item[5] == 'interest'], 2, used_ids))
    chosen.extend(pick([item for item in scored if item[5] == 'hobby'], 2, used_ids))
    if len(chosen) < 4:
        chosen.extend(pick(scored, 4 - len(chosen), used_ids))
    if len(chosen) < 4:
        fallback = RecommendationAction.objects.filter(enabled=True).exclude(action_id__in=used_ids).order_by('-default_weight', 'action_id')
        for action in fallback:
            chosen.append((action.default_weight, action.default_weight, action.action_id, action, ['SAFE_FALLBACK'], 'general'))
            used_ids.add(action.action_id)
            if len(chosen) == 4:
                break

    CheckinRecommendation.objects.filter(checkin=checkin).delete()
    records = []
    for rank, (score, _, _, action, reason_codes, _) in enumerate(chosen, start=1):
        record = CheckinRecommendation.objects.create(
            checkin=checkin,
            action=action,
            score=score,
            rank=rank,
            reason_codes=reason_codes,
        )
        records.append(record)
    return records


def recommendations_payload(checkin):
    return [
        {
            **{key: value for key, value in {
                'id': item.action.action_id,
                'action_id': item.action.action_id,
                'title': item.action.title,
                'description': item.action.description,
                'expected_time': f'{item.action.expected_minutes}분',
                'duration': f'{item.action.expected_minutes}분',
                'icon': item.action.icon,
                'tags': item.action.tags,
                'reason_codes': item.reason_codes,
                'reason': reason_text(item.reason_codes),
                'safety_notice': item.action.safety_notice,
            }.items()},
            'rank': item.rank,
            'score': item.score,
        }
        for item in checkin.recommendations.select_related('action').order_by('rank')
    ]


def reason_text(codes):
    labels = {
        'PREFERENCE_DIRECT': '평소 좋아하는 취향을 활용할 수 있어요.',
        'INTEREST_MATCH': '저장해둔 관심사를 바탕으로 골랐어요.',
        'HOBBY_MATCH': '저장해둔 취미를 바탕으로 골랐어요.',
        'NEED_MATCH': '지금 필요한 도움에 맞춰 골랐어요.',
        'EMOTION_MATCH': '오늘의 마음에 부담이 적은 활동이에요.',
        'ENERGY_MATCH': '현재 에너지에 맞는 정도의 활동이에요.',
        'SAFE_FALLBACK': '관심사가 없어도 가볍게 시작할 수 있는 활동이에요.',
        'NOT_RECENT': '최근에 고르지 않은 새로운 제안이에요.',
        'VERY_HELPFUL_BEFORE': '전에 큰 도움이 됐던 행동이라 조금 더 적극적으로 추천했어요.',
        'HELPFUL_BEFORE': '전에 도움이 됐던 기록을 참고했어요.',
        'LLM_RANDOM': '저장한 관심사와 취미를 섞어 새로 만들어봤어요.',
    }
    return next((labels[code] for code in codes if code in labels), '오늘의 선택을 바탕으로 골랐어요.')


def calendar_entry(checkin):
    action = checkin.selected_action
    feedback = checkin.feedback.filter(action=action).first() if action else None
    return {
        'checkin_id': checkin.id,
        'date': checkin.checkin_date.isoformat(),
        'entry_type': 'CHECKIN',
        'reflection': checkin.reflection.label if checkin.reflection else None,
        'primary_emotion': checkin.primary_emotion or None,
        'cause': checkin.cause.label if checkin.cause else None,
        'cause_context': checkin.cause_context or None,
        'cause_display_text': checkin.cause_display_text_snapshot or (checkin.cause.label if checkin.cause else None),
        'need': checkin.need.label if checkin.need else None,
        'selected_action_id': action.action_id if action else None,
        'selected_action': action.title if action else None,
        'action_completed': feedback.completed if feedback else False,
        'action_helpfulness': feedback.helpfulness if feedback else None,
        'final_route': checkin.final_route or None,
        'completed': bool(checkin.completed_at),
    }

import hashlib
import json
import logging
import os
import re
import random
import sys
import uuid
import base64
from html import escape
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    CatalogEntry,
    EmotionCardAnalysis,
    EmotionCardJob,
    EmotionCardScene,
    FeatureCode,
    GeneratedEmotionCard,
    RuleEntry,
    SocialCompanionRule,
)


logger = logging.getLogger('emotion_cards')


EMOTION_LABELS = {'JOY': '기쁨', 'SADNESS': '슬픔', 'ANGER': '화남', 'ANXIETY': '불안'}

# 학습된 분류기(ai/emotion, 4감정)의 한글 라벨 -> 카드 감정 코드.
# '일반'은 매핑하지 않음(-> LLM/키워드가 결정).
EMOTION_KO_TO_CODE = {'기쁨': 'JOY', '슬픔': 'SADNESS', '분노': 'ANGER'}

PRIMARY_EMOTIONS = {'JOY', 'SADNESS', 'ANGER', 'ANXIETY'}
NEGATIVE_EMOTIONS = {'SADNESS', 'ANGER', 'ANXIETY'}
VALENCES = {'POSITIVE', 'NEGATIVE', 'MIXED', 'NEUTRAL', 'UNKNOWN'}
OUTCOMES = {'OUT_SUCCESS', 'OUT_POSITIVE', 'OUT_RELIEF', 'OUT_NEUTRAL', 'OUT_MIXED',
            'OUT_DIFFICULT', 'OUT_LOSS', 'OUT_UNCERTAIN', 'OUT_UNKNOWN'}
STAGES = {'STARTED', 'ONGOING', 'COMPLETED', 'WAITING', 'CANCELLED', 'UNSPECIFIED'}
SOCIAL_CONTEXTS = {'ALONE', 'FRIENDS', 'PARTNER', 'FAMILY', 'COLLEAGUES', 'CLASSMATES',
                   'GROUP', 'CROWD', 'ONLINE', 'PET', 'NOT_DISCLOSED'}

# 부정 감정 장면에 반드시 넣는 안전 신호.
SAFE_SIGNAL = 'a small warm light source (lamp, window glow, or clearing sky) as a gentle sign of hope'

# 마음카드는 사용자 프로필 캐릭터와 분리해, 매번 새로운 장면의 동행자를 고른다.
# 이미지 모델이 내부 코드만 보고 고양이로 해석하지 않도록 종과 외형을 프롬프트에 함께 둔다.
CARD_CHARACTERS = {
    'kkami': 'Kkami, a small navy-black cat mascot with a purple collar',
    'yeoul': 'Yeoul, a small round white bird mascot with soft gray wing tips',
    'toto': 'Toto, a gentle small lavender otter mascot',
    'pori': 'Pori, a cheerful small red panda mascot with orange fur and a striped tail',
}


def _running_tests():
    """manage.py test 실행 중이면 외부 모델/LLM 호출을 건너뛴다(오프라인·무비용)."""
    return 'test' in sys.argv or getattr(settings, 'TESTING', False)


def _first(values, fallback=''):
    if isinstance(values, str):
        values = values.split('|')
    # 일부 매핑 규칙은 후보 목록을 비워 둘 수 있다. 이 경우 장면 생성을
    # 중단하지 말고 호출부의 안전한 기본값으로 이어간다.
    return next((value for value in (values or ()) if value), fallback)


def _catalog(catalog, code):
    return CatalogEntry.objects.filter(catalog=catalog, code=code, enabled=True).first()


def _label(group, code):
    item = FeatureCode.objects.filter(group=group, code=code).first()
    return item.label if item else EMOTION_LABELS.get(code, code)


def _safe_place(value):
    value = re.sub(r'[@#][\w.-]+', '', (value or '')).strip()
    return re.sub(r'\d{2,}', '', value)[:80]


def _entry_or_text(catalog, code, fallback):
    entry = _catalog(catalog, code)
    return {'id': code, 'label': entry.display_name if entry else fallback,
            'visual_prompt': entry.visual_prompt if entry else ''}


def _tokens(text):
    return set(re.findall(r'[가-힣a-z]+', (text or '').lower()))


# 1) 감정 분류 - 학습된 모델(ai/emotion) -> 없으면 None
def _model_emotion(text):
    """프로젝트의 학습된 감정 분류기로 primary_emotion 코드 추정.
    모델 비활성/저확신/오류/'일반'이면 None을 반환해 상위 폴백에 맡긴다."""
    if not (text or '').strip() or _running_tests():
        return None
    try:
        from ai.emotion.emotion_model import predict_emotion_with_confidence
    except Exception:
        return None
    try:
        label, confidence = predict_emotion_with_confidence(text)
    except Exception:
        return None
    code = EMOTION_KO_TO_CODE.get(label or '')
    if not code:
        return None
    gate = float(getattr(settings, 'EMOTION_CARD_EMOTION_CONF_GATE', 0.55))
    if confidence is not None and confidence < gate:
        return None
    return code


# 2) LLM 구조화 분석 - 키/모델 없으면 None (테스트/오프라인 폴백)
_LLM_SYSTEM = (
    "너는 심리 진단자가 아니라 사용자의 하루 기록을 구조화하는 추출기다. "
    "입력에 명시된 정보만 사용하고, 없는 사람/장소/사건/결과를 지어내지 않는다. "
    "개인명/회사명/학교명/상호/계정/주소는 일반화한다. "
    "정신질환/위험도를 진단하지 않는다. "
    "반드시 아래 JSON 스키마 하나만 출력한다(설명/코드블록 금지).\n"
    '{"primary_emotion":"JOY|SADNESS|ANGER|ANXIETY|null",'
    '"secondary_emotion":"JOY|SADNESS|ANGER|ANXIETY|null",'
    '"emotion_intensity":"LOW|MEDIUM|HIGH",'
    '"valence":"POSITIVE|NEGATIVE|MIXED|NEUTRAL|UNKNOWN",'
    '"event_domain":"WORK_STUDY|RELATIONSHIP|FAMILY|HEALTH|FUTURE|FINANCE|HOBBY|REST|DAILY|SELF|TRAVEL|CELEBRATION|LOSS|UNEXPECTED|UNKNOWN",'
    '"event_summary":"개인정보 제거한 한 문장",'
    '"event_outcome":"OUT_SUCCESS|OUT_POSITIVE|OUT_RELIEF|OUT_NEUTRAL|OUT_MIXED|OUT_DIFFICULT|OUT_LOSS|OUT_UNCERTAIN|OUT_UNKNOWN",'
    '"event_stage":"STARTED|ONGOING|COMPLETED|WAITING|CANCELLED|UNSPECIFIED",'
    '"social_context":"ALONE|FRIENDS|PARTNER|FAMILY|COLLEAGUES|CLASSMATES|GROUP|CROWD|ONLINE|PET|NOT_DISCLOSED",'
    '"explicit_place":"일반화된 장소 또는 빈 문자열",'
    '"explicit_action":"직접 언급된 행동 또는 빈 문자열",'
    '"explicit_objects":["직접 언급된 소품 최대 3개"],'
    '"analysis_status":"CLEAR|MIXED|AMBIGUOUS|NOT_DISCLOSED"}'
)


def _extract_json(raw):
    match = re.search(r'\{.*\}', raw or '', re.S)
    return match.group(0) if match else (raw or '')


def _validate_llm(data):
    """LLM 원출력을 허용 enum으로 검증/정제. 잘못된 값은 버린다."""
    if not isinstance(data, dict):
        return None
    out = {}
    pe = data.get('primary_emotion')
    out['primary_emotion'] = pe if pe in PRIMARY_EMOTIONS else None
    se = data.get('secondary_emotion')
    out['secondary_emotion'] = se if se in PRIMARY_EMOTIONS else None
    out['valence'] = data.get('valence') if data.get('valence') in VALENCES else 'UNKNOWN'
    out['event_outcome'] = data.get('event_outcome') if data.get('event_outcome') in OUTCOMES else 'OUT_UNKNOWN'
    out['event_stage'] = data.get('event_stage') if data.get('event_stage') in STAGES else 'UNSPECIFIED'
    out['social_context'] = data.get('social_context') if data.get('social_context') in SOCIAL_CONTEXTS else None
    dom = data.get('event_domain')
    out['event_domain'] = dom if FeatureCode.objects.filter(group='EVENT_DOMAIN', code=dom).exists() else 'UNKNOWN'
    out['event_summary'] = str(data.get('event_summary') or '')[:200]
    out['explicit_place'] = _safe_place(data.get('explicit_place'))
    out['explicit_action'] = str(data.get('explicit_action') or '')[:80]
    objects = data.get('explicit_objects') or []
    out['explicit_objects'] = [str(o)[:40] for o in objects if o][:3] if isinstance(objects, list) else []
    status = data.get('analysis_status')
    out['analysis_status'] = status if status in {'CLEAR', 'MIXED', 'AMBIGUOUS', 'NOT_DISCLOSED'} else 'CLEAR'
    intensity = data.get('emotion_intensity')
    out['emotion_intensity'] = intensity if intensity in {'LOW', 'MEDIUM', 'HIGH'} else 'MEDIUM'
    return out


def _llm_analyze(payload):
    """OpenAI 직접 호출로 구조화 분석. 실패 시 None(키워드 폴백).

    공유 get_llm은 max_tokens를 넘겨 신형 모델(gpt-5.x)에서 400이 나므로
    여기서는 SDK를 직접 쓰고 max_completion_tokens를 사용한다.
    """
    if _running_tests() or not getattr(settings, 'EMOTION_CARD_ENABLE_LLM_ANALYSIS', True):
        return None
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return None
    model = getattr(settings, 'EMOTION_CARD_LLM_MODEL', '') or os.environ.get('OPENAI_MODEL', 'gpt-5.4-mini')
    user_input = {
        'emotion_answer': payload.get('emotion_text', ''),
        'event_answer': payload.get('event_text', ''),
        'energy_answer': payload.get('energy_text', ''),
        'need_answer': payload.get('need_text', ''),
        'memory_answer': payload.get('memory_text', ''),
    }
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': _LLM_SYSTEM},
                {'role': 'user', 'content': json.dumps(user_input, ensure_ascii=False)},
            ],
            max_completion_tokens=600,
            response_format={'type': 'json_object'},
        )
        content = response.choices[0].message.content
        return _validate_llm(json.loads(_extract_json(content)))
    except Exception:
        logger.exception('[emotion_card] LLM 분석 실패 → 키워드 폴백 (model=%s)', model)
        return None


# 키워드 폴백 (모델/LLM 모두 불가할 때)
def _keyword_emotion(text):
    text = (text or '').lower()
    rules = [
        ('ANGER', ('화나', '짜증', '분노', '억울')), ('SADNESS', ('슬퍼', '서운', '외로', '허무', '무겁')),
        ('ANXIETY', ('불안', '걱정', '초조', '긴장')), ('JOY', ('기뻐', '좋아', '뿌듯', '행복', '안도')),
    ]
    return next((code for code, terms in rules if any(term in text for term in terms)), 'JOY')


def _event_for(text, llm=None):
    """이벤트 카탈로그 매칭: 표시명 포함 -> 도메인 내 토큰 겹침 -> EVT_UNSPECIFIED."""
    lowered = (text or '').lower()
    events = list(CatalogEntry.objects.filter(catalog='event', enabled=True))
    if not events:
        return None
    for entry in events:
        display = (entry.display_name or '').lower()
        if display and display in lowered:
            return entry
    domain = (llm or {}).get('event_domain')
    query_tokens = _tokens(lowered)

    def score(entry):
        overlap = len(_tokens(entry.display_name) & query_tokens)
        same_domain = 1 if domain and entry.metadata.get('event_domain') == domain else 0
        return overlap * 2 + same_domain

    if query_tokens or domain:
        best = max(events, key=score)
        if score(best) > 0:
            return best
    return _catalog('event', 'EVT_UNSPECIFIED') or events[0]


# 안전 검사
def _safety_rules_status(text):
    """SafetyVisualRule(19번) 키워드/정책 기반. BLOCK_AND_SUPPORT->BLOCKED, REVIEW류->REVIEW."""
    severity = {'BLOCK_AND_SUPPORT': 'BLOCKED', 'BLOCK_OR_REVIEW': 'REVIEW', 'REVIEW': 'REVIEW'}
    worst = 'SAFE'
    for row in RuleEntry.objects.filter(rule_type='safety', enabled=True):
        hints = [h for h in (row.data.get('keyword_hints') or '').split('|') if h]
        if any(h and h in text for h in hints):
            mapped = severity.get(row.data.get('policy'), 'SAFE')
            if mapped == 'BLOCKED':
                return 'BLOCKED'
            if mapped == 'REVIEW':
                worst = 'REVIEW'
    return worst


def safety_status(payload):
    text = ' '.join(str(payload.get(key, '')) for key in ('emotion_text', 'event_text', 'memory_text')).lower()
    # 규칙 미시드 상황 대비 하드코딩 최소 안전망
    if any(word in text for word in ('자해', '죽고 싶', '죽고싶', '사라지고 싶', '살고 싶지')):
        return 'BLOCKED'
    try:
        return _safety_rules_status(text)
    except Exception:
        return 'SAFE'


# 분석 (오케스트레이션)
def analyze(payload, user):
    """감정 분류기 -> LLM 구조화 -> 키워드 폴백 순으로 분석.
    사용자가 직접 고른 energy/need 코드는 항상 우선한다."""
    status = safety_status(payload)
    emotion_text = f"{payload.get('emotion_text', '')} {payload.get('event_text', '')}"

    llm = _llm_analyze(payload) if status == 'SAFE' else None

    emotion = _model_emotion(emotion_text)
    source = 'model'
    if not emotion and llm and llm.get('primary_emotion'):
        emotion, source = llm['primary_emotion'], 'llm'
    if not emotion:
        emotion, source = _keyword_emotion(emotion_text), 'keyword'

    event = _event_for(payload.get('event_text'), llm)
    event_meta = event.metadata if event else {}

    energy_code = payload.get('energy_code') or 'ENG_STEADY'
    need_code = payload.get('need_code') or 'NEED_COMFORT'
    social = (llm or {}).get('social_context') or event_meta.get('default_social') or 'NOT_DISCLOSED'

    result = {
        'primary_emotion': {'code': emotion, 'label': _label('PRIMARY_EMOTION', emotion)},
        'secondary_emotion': (llm or {}).get('secondary_emotion'),
        'valence': (llm or {}).get('valence', 'UNKNOWN'),
        'state_tags': [],
        'emotion_intensity': (llm or {}).get('emotion_intensity', 'MEDIUM'),
        'event_type': {'id': event.code if event else 'EVT_UNSPECIFIED',
                       'label': event.display_name if event else '오늘의 상황'},
        'event_summary': (llm or {}).get('event_summary', ''),
        'event_domain': (llm or {}).get('event_domain') or event_meta.get('event_domain') or 'UNKNOWN',
        'event_outcome': (llm or {}).get('event_outcome') or event_meta.get('default_outcome') or 'OUT_UNKNOWN',
        'event_stage': (llm or {}).get('event_stage') or event_meta.get('default_stage') or 'UNSPECIFIED',
        'social_context': social if social in SOCIAL_CONTEXTS else 'NOT_DISCLOSED',
        'energy': {'code': energy_code, 'label': _label('ENERGY', energy_code)},
        'need': {'code': need_code, 'label': _label('NEED', need_code)},
        'memory_focus': (payload.get('memory_text') or '')[:200],
        'explicit_place': _safe_place((llm or {}).get('explicit_place') or payload.get('explicit_place')),
        'explicit_action': (llm or {}).get('explicit_action', ''),
        'explicit_objects': (llm or {}).get('explicit_objects', []),
        'analysis_source': source,
    }
    analysis_status = (llm or {}).get('analysis_status', 'CLEAR')
    return EmotionCardAnalysis.objects.create(
        user=user,
        raw_input={key: str(value)[:200] for key, value in payload.items()},
        result=result,
        analysis_status=analysis_status,
        safety_status=status,
    )


def update_analysis(analysis, values):
    result = dict(analysis.result)
    for key in ('energy_code', 'need_code'):
        if key in values:
            group = 'ENERGY' if key == 'energy_code' else 'NEED'
            result['energy' if key == 'energy_code' else 'need'] = {'code': values[key], 'label': _label(group, values[key])}
    if 'primary_emotion' in values:
        code = values['primary_emotion']
        result['primary_emotion'] = {'code': code, 'label': _label('PRIMARY_EMOTION', code)}
    if 'memory_focus' in values:
        result['memory_focus'] = str(values['memory_focus'])[:200]
    analysis.result = result
    analysis.save(update_fields=['result', 'updated_at'])
    analysis.scenes.filter(invalidated=False).update(invalidated=True)
    return analysis


# 규칙 조회
def _rule(rule_type, field, value):
    rows = [row.data for row in RuleEntry.objects.filter(rule_type=rule_type, enabled=True) if row.data.get(field) == value]
    rows.sort(key=lambda data: int(data.get('weight') or 0), reverse=True)
    return rows[0] if rows else {}


def _emotion_visual_rule(emotion, intensity):
    """감정 시각 규칙 선택: 같은 감정 후보 중 intensity 일치를 우선, 동률이면 weight."""
    rows = [row.data for row in RuleEntry.objects.filter(rule_type='emotion_visual', enabled=True)
            if row.data.get('primary_emotion') == emotion]
    if not rows:
        return {}
    def score(data):
        base = int(data.get('weight') or 0)
        return base + (100 if intensity and data.get('intensity') == intensity else 0)
    return max(rows, key=score)


def _event_scene_rule(event_type_id, outcome, stage):
    def matches(data):
        return (data.get('outcome_condition') in ('', None, outcome)
                and data.get('stage_condition') in ('', None, stage))

    rows = [row.data for row in RuleEntry.objects.filter(rule_type='event_scene', enabled=True)
            if row.data.get('event_type_id') == event_type_id and matches(row.data)]
    rows.sort(key=lambda data: int(data.get('weight') or 0), reverse=True)
    return rows[0] if rows else {}


def _message_rule(emotion, outcome, need):
    best, best_weight = None, -1
    for row in RuleEntry.objects.filter(rule_type='message_mapping', enabled=True):
        data = row.data
        fields = (('primary_emotion', emotion), ('event_outcome', outcome), ('need_code', need))
        specified = [(rule_value, actual) for key, actual in fields for rule_value in [data.get(key)] if rule_value]
        if not specified or any(rule_value != actual for rule_value, actual in specified):
            continue
        weight = int(data.get('weight') or 0)
        if weight > best_weight:
            best, best_weight = data.get('message_id'), weight
    return best


def _social_companion(social_context):
    rule = (SocialCompanionRule.objects.filter(social_context=social_context, enabled=True).first()
            or SocialCompanionRule.objects.filter(rule_id='SCR-01').first())
    if not rule:
        return None
    return {'social_context': social_context, 'companion_type': rule.companion_type,
            'count_max': rule.companion_count_max, 'visual_prompt': rule.visual_prompt,
            'privacy_note': rule.privacy_note}


# 장면 매핑
def build_scene(analysis):
    if analysis.safety_status != 'SAFE':
        return None

    result = analysis.result
    emotion = result['primary_emotion']['code']
    intensity = result.get('emotion_intensity', 'MEDIUM')
    need = result['need']['code']
    energy = result['energy']['code']
    outcome = result.get('event_outcome', 'OUT_UNKNOWN')
    stage = result.get('event_stage', 'UNSPECIFIED')
    event_id = (result.get('event_type') or {}).get('id', 'EVT_UNSPECIFIED')
    social = result.get('social_context', 'NOT_DISCLOSED')

    emotion_rule = _emotion_visual_rule(emotion, intensity)
    need_rule = _rule('need_environment', 'need_code', need)
    energy_rule = _rule('energy', 'energy_code', energy)
    event_rule = _event_scene_rule(event_id, outcome, stage)

    explicit_place = _safe_place(result.get('explicit_place'))
    explicit_action = (result.get('explicit_action') or '').strip()
    explicit_objects = [o for o in (result.get('explicit_objects') or []) if o][:3]

    weather_code = emotion_rule.get('weather_id') or 'WTH_CLEAR'
    lighting_code = emotion_rule.get('lighting_id') or need_rule.get('lighting_id') or 'LGT_LAMP'
    expression_code = emotion_rule.get('expression_id') or 'EXP_CALM'

    location_code = (_first(event_rule.get('location_candidates'))
                     or _first(need_rule.get('location_candidates'), 'LOC_QUIET_ROOM'))
    action_code = (energy_rule.get('default_action')
                   or _first(event_rule.get('action_candidates'))
                   or _first(need_rule.get('action_candidates'), 'ACT_REFLECTION'))
    object_codes = [c for c in (event_rule.get('object_candidates') or need_rule.get('object_candidates') or '').split('|') if c][:3]

    companion = _social_companion(social)

    memory_focus = (result.get('memory_focus') or '').strip()
    message_code = _message_rule(emotion, outcome, need) or need_rule.get('message_id') or 'MSG_CARE'

    weather = _entry_or_text('weather', weather_code, '맑고 부드러운 하늘')
    lighting = _entry_or_text('lighting', lighting_code, '따뜻한 조명')
    expression = _entry_or_text('character_visual', expression_code, '편안한 표정')
    location = ({'id': None, 'label': explicit_place, 'visual_prompt': explicit_place}
                if explicit_place else _entry_or_text('location', location_code, '조용한 공간'))
    action = ({'id': None, 'label': explicit_action, 'visual_prompt': explicit_action}
              if explicit_action else _entry_or_text('action', action_code, '잠시 숨을 고르는 모습'))
    objects = ([{'id': None, 'label': o, 'visual_prompt': o} for o in explicit_objects]
               if explicit_objects else [_entry_or_text('object', c, '작은 소품') for c in object_codes])
    message = _entry_or_text('message', message_code, '오늘의 마음을 다정하게 바라봐요')

    avoid = [v for v in (emotion_rule.get('avoid_visuals') or '').split('|') if v]
    safe_signal = SAFE_SIGNAL if emotion in NEGATIVE_EMOTIONS else ''

    spec = {
        'weather': weather, 'location': location, 'action': action, 'objects': objects,
        'lighting': lighting, 'expression': expression, 'companion': companion,
        'message': message, 'memory_focus': memory_focus,
        'primary_emotion': emotion, 'energy_code': energy, 'need_code': need,
        'event_type': event_id, 'social_context': social,
        'character': random.choice(tuple(CARD_CHARACTERS)), 'avoid_visuals': avoid, 'safe_signal': safe_signal,
        'mapping_reason_codes': [c for c in (
            emotion_rule.get('rule_id'), event_rule.get('rule_id'),
            need_rule.get('rule_id'), energy_rule.get('rule_id'),
            companion['companion_type'] if companion else None,
        ) if c],
    }
    digest = hashlib.sha256(repr(spec).encode()).hexdigest()

    styles = list(CatalogEntry.objects.filter(catalog='style', enabled=True, metadata__preserve_scene=True).values('code', 'display_name'))
    if not styles:
        styles = list(CatalogEntry.objects.filter(catalog='style', enabled=True).values('code', 'display_name'))

    return EmotionCardScene.objects.create(
        user=analysis.user, analysis=analysis, scene_hash=digest, scene_spec=spec,
        available_styles=styles, safety_status='SAFE',
    )


# 이미지 생성
def _build_image_prompt(spec, style_id):
    character_id = spec.get('character')
    character_description = CARD_CHARACTERS.get(
        character_id,
        'a small gentle animal mascot with clear, consistent anatomy',
    )
    parts = [
        "Create a safe, gentle, text-free emotional illustration for a daily mood card.",
        f"Art style: {style_id}.",
        f"Main character: {character_description}. Keep this exact mascot species and appearance consistent.",
        f"Weather/sky: {spec['weather'].get('visual_prompt') or spec['weather'].get('label')}.",
        f"Location: {spec['location'].get('visual_prompt') or spec['location'].get('label')}.",
        f"Lighting: {spec.get('lighting', {}).get('visual_prompt') or ''}.",
        f"Character action: {spec['action'].get('visual_prompt') or spec['action'].get('label')}.",
        f"Character expression: {spec.get('expression', {}).get('visual_prompt') or ''}.",
    ]
    objects = ', '.join(o.get('visual_prompt') or o.get('label') for o in spec.get('objects', []) if o)
    if objects:
        parts.append(f"Key props: {objects}.")
    companion = spec.get('companion')
    if companion and companion.get('visual_prompt'):
        parts.append(f"Companion: {companion['visual_prompt']}.")
    if spec.get('safe_signal'):
        parts.append(f"Always include {spec['safe_signal']}.")
    avoid = ', '.join(spec.get('avoid_visuals', []))
    parts.append(
        "Do not include real people, faces of identifiable individuals, readable text, logos, "
        "watermarks, brand names, violence, weapons, gore, self-harm, or additional/distorted limbs."
        + (f" Also avoid: {avoid}." if avoid else "")
    )
    return ' '.join(p for p in parts if p.strip())


def _build_fallback_card_svg(spec):
    """개발용 공급자에서도 화면에 표시할 수 있는 카드 이미지를 만든다.

    실제 이미지 API가 비활성화된 경우에도 빈 image_url로 완료 처리하면
    프런트가 생성 실패와 구분할 수 없다. 이 SVG는 외부 API를 대체하는
    카드형 미리보기이며, 실제 API가 활성화된 환경에서는 사용되지 않는다.
    """
    weather = escape(str(spec.get('weather', {}).get('label', '오늘의 하늘')))
    location = escape(str(spec.get('location', {}).get('label', '조용한 곳')))
    action = escape(str(spec.get('action', {}).get('label', '천천히 쉬어가기')))
    emotion = escape(str(spec.get('primary_emotion', 'TODAY')))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1536" viewBox="0 0 1024 1536" role="img" aria-label="마음카드 미리보기">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#261349"/><stop offset=".52" stop-color="#853b78"/><stop offset="1" stop-color="#f39168"/></linearGradient>
    <radialGradient id="glow" cx="50%" cy="29%" r="48%"><stop stop-color="#ffe9af" stop-opacity=".94"/><stop offset="1" stop-color="#ffc47d" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="1024" height="1536" rx="56" fill="url(#sky)"/>
  <rect width="1024" height="1536" rx="56" fill="url(#glow)"/>
  <path d="M0 1100 C170 960 330 1170 500 1035 S800 980 1024 1105 V1536 H0Z" fill="#291447" fill-opacity=".68"/>
  <circle cx="512" cy="448" r="158" fill="#fff0ba" fill-opacity=".88"/>
  <g fill="#fff8e9" font-family="sans-serif" text-anchor="middle"><text x="512" y="838" font-size="48" font-weight="700">오늘의 마음 카드</text><text x="512" y="922" font-size="31">{weather} · {location}</text><text x="512" y="987" font-size="31">{action}</text><text x="512" y="1280" font-size="25" letter-spacing="5">{emotion}</text></g>
</svg>'''


def _store_fallback_card_image(spec):
    filename = f"emotion_cards/fallback-{uuid.uuid4().hex}.svg"
    target = Path(settings.MEDIA_ROOT) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_build_fallback_card_svg(spec), encoding='utf-8')
    return f"{settings.MEDIA_URL}{filename}"


def ensure_card_image(card):
    """과거의 빈 완료 카드도 조회 시 화면에 표시 가능한 이미지로 보완한다."""
    if card.image_url:
        return card
    card.image_url = _store_fallback_card_image(card.scene.scene_spec)
    card.save(update_fields=['image_url'])
    return card


def _fake_complete(job):
    spec = job.scene.scene_spec
    card = GeneratedEmotionCard.objects.create(
        user=job.user, scene=job.scene, style_id=job.style_id,
        image_url=_store_fallback_card_image(spec),
        image_alt=f"{spec['weather']['label']} 아래 {spec['action']['label']}",
        summary=f"{spec['primary_emotion']} · {spec['weather']['label']} · {spec['location']['label']}",
    )
    job.status, job.progress, job.card = 'COMPLETED', 100, card
    job.save(update_fields=['status', 'progress', 'card', 'updated_at'])
    return job


def _passes_moderation(text):
    """입력 프롬프트 모더레이션(best-effort). 모델/키 없으면 통과 처리."""
    model = getattr(settings, 'EMOTION_CARD_MODERATION_MODEL', '')
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not model or not api_key:
        return True
    try:
        from openai import OpenAI
        result = OpenAI(api_key=api_key).moderations.create(model=model, input=text)
        return not result.results[0].flagged
    except Exception:
        return True


def _generate_image_bytes(client, model, prompt, size, quality):
    response = client.images.generate(model=model, prompt=prompt, size=size, quality=quality)
    return base64.b64decode(response.data[0].b64_json)


def _real_complete(job):
    """실제 이미지 공급자 호출 - EMOTION_CARD_ENABLE_REAL_IMAGE_API=True 일 때만."""
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    model = getattr(settings, 'EMOTION_CARD_IMAGE_MODEL', '')
    if not api_key or not model:
        job.status, job.error_code = 'FAILED', 'EMOTION_CARD_PROVIDER_NOT_CONFIGURED'
        job.save(update_fields=['status', 'error_code', 'updated_at'])
        return job

    spec = job.scene.scene_spec
    size = getattr(settings, 'EMOTION_CARD_IMAGE_SIZE', '1024x1536')
    quality = getattr(settings, 'EMOTION_CARD_IMAGE_QUALITY', 'medium')
    prompt = _build_image_prompt(spec, job.style_id)

    if not _passes_moderation(prompt):
        job.status, job.error_code = 'BLOCKED', 'EMOTION_CARD_MODERATION_BLOCKED'
        job.save(update_fields=['status', 'error_code', 'updated_at'])
        return job

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        try:
            image_bytes = _generate_image_bytes(client, model, prompt, size, quality)
        except Exception:
            logger.exception('[emotion_card] 1차 이미지 생성 실패 → 단순 프롬프트로 재시도 (model=%s size=%s quality=%s)', model, size, quality)
            simple = _build_image_prompt(
                {**spec, 'objects': [], 'companion': None,
                 'avoid_visuals': spec.get('avoid_visuals', [])}, job.style_id)
            image_bytes = _generate_image_bytes(client, model, simple, size, quality)

        filename = f"emotion_cards/{uuid.uuid4().hex}.png"
        target = Path(settings.MEDIA_ROOT) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image_bytes)

        card = GeneratedEmotionCard.objects.create(
            user=job.user, scene=job.scene, style_id=job.style_id,
            image_url=f"{settings.MEDIA_URL}{filename}",
            image_alt=f"{spec['weather']['label']} 아래 {spec['action']['label']}",
            summary=f"{spec['primary_emotion']} · {spec['weather']['label']} · {spec['location']['label']}",
        )
        job.status, job.progress, job.card = 'COMPLETED', 100, card
        job.save(update_fields=['status', 'progress', 'card', 'updated_at'])
    except Exception:
        logger.exception('[emotion_card] 이미지 생성 최종 실패 (model=%s size=%s quality=%s)', model, size, quality)
        job.status, job.error_code = 'FAILED', 'EMOTION_CARD_IMAGE_PROVIDER_FAILED'
        job.save(update_fields=['status', 'error_code', 'updated_at'])
    return job


def create_generation_job(scene, style_id, user, idempotency_key=None):
    key = idempotency_key or uuid.uuid4().hex
    # DB 검증 + job 행 생성만 트랜잭션으로 (긴 외부 이미지 호출은 트랜잭션 밖에서 수행)
    with transaction.atomic():
        if scene.user_id != user.id or scene.invalidated or scene.safety_status != 'SAFE':
            raise ValueError('EMOTION_CARD_SCENE_BLOCKED')
        # EMOTION_CARD_MAX_DAILY_GENERATIONS=0(또는 음수)이면 무제한. 1 이상이면 그 수만큼 하루 제한.
        daily_limit = int(getattr(settings, 'EMOTION_CARD_MAX_DAILY_GENERATIONS', 2))
        if daily_limit > 0 and GeneratedEmotionCard.objects.filter(user=user, created_at__date=timezone.localdate()).exclude(image_url='').count() >= daily_limit:
            raise ValueError('EMOTION_CARD_RATE_LIMITED')
        if style_id not in {style['code'] for style in scene.available_styles}:
            raise ValueError('EMOTION_CARD_STYLE_NOT_FOUND')
        existing = EmotionCardJob.objects.filter(user=user, idempotency_key=key).first()
        if existing:
            return existing, True
        job = EmotionCardJob.objects.create(user=user, scene=scene, style_id=style_id, idempotency_key=key, status='QUEUED', progress=10)
    provider = _real_complete if getattr(settings, 'EMOTION_CARD_ENABLE_REAL_IMAGE_API', False) else _fake_complete
    return provider(job), False

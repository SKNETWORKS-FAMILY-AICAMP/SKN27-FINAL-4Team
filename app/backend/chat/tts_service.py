# -*- coding: utf-8 -*-
"""TTS — 1회 재생 후 즉시 파기 방식 (2026-07-02 확정).

공급자 (TTS_PROVIDER): openai(gpt-audio, 기본) | off(생성 차단 — 비용 절약).
ElevenLabs(키 만료)·Typecast(월 5분 제한)는 2026-07-19 은퇴 — 코드 삭제.

- 디스크에 mp3를 저장하지 않는다. 오디오는 메모리에만 보관.
- 프론트가 GET /api/tts/{id}/audio/ 로 한 번 가져가면 즉시 삭제 (다시 듣기 없음).
- 시크릿 모드 포함 어디에도 음성이 남지 않는다.
- 고정 문구(콜드스타트/MBTI 질문 등)만 메모리 캐싱해 재생성 비용 절감.
- 실패 시 status='failed' → 프론트는 텍스트만으로 진행 (음성은 부가 기능).

감정 톤: 감정 4종(joy·sadness·anger·normal)별 연기 지시문 — _OPENAI_EMOTION_STYLE.
"""
import hashlib
import os
import re
import threading
import time
import uuid

import requests
from django.conf import settings

# (ElevenLabs 감정 프리셋·캐릭터 튜닝 숫자 다이얼 삭제 2026-07-19 — 그 의도는
#  _OPENAI_EMOTION_STYLE·_OPENAI_CHARACTER_PERSONA의 연기 지시문으로 이식됨)

# ── TTS 다이얼 (일원화 2026-07-19 — env 오버라이드 가능, 기본값 근거 명시) ──
TTS_SCRIPT_SIM_MIN = float(os.environ.get('TTS_SCRIPT_SIM_MIN', '0.9'))
#   대본↔발화 유사도 하한 — 문장부호·공백 차이는 통과, 단어가 바뀌면 차단.
#   실측(2026-07-19): 모델이 대본에 '대답'해버린 이탈이 0.39~0.44 → 0.9와 여유 큼.
TTS_MAX_CHARS = int(os.environ.get('TTS_MAX_CHARS', '4000'))
#   대사 길이 안전 상한 (gpt-audio 입력 보호 — 봇 답변은 보통 300자 이하)
TTS_SCRIPT_RETRY = int(os.environ.get('TTS_SCRIPT_RETRY', '2'))
#   대본 이탈 시 총 시도 횟수 — 1회 이탈은 우연일 수 있어 기회 1번, 그 이상은 비용 낭비
_TASK_TTL = int(os.environ.get('TTS_TASK_TTL_SEC', str(10 * 60)))
#   미재생 음성 메모리 보관 시간(초) — 지나면 파기 (1회 재생 즉시 파기 원칙의 하우스키핑)
_lock = threading.Lock()
_tasks: dict[str, dict] = {}    # {task_id: {'status', 'audio': bytes|None, 'voice_id', 'cached', 'ts'}}
_cache: dict[str, bytes] = {}   # {content_hash: mp3 bytes} — 고정 문구만


def _expire_locked() -> None:
    now = time.time()
    for tid in [t for t, v in _tasks.items() if now - v['ts'] > _TASK_TTL]:
        del _tasks[tid]


# ── OpenAI TTS (2026-07-19 전환) — ElevenLabs 키 만료·튜닝 난항으로 교체.
# gpt-4o-mini-tts는 instructions(자연어 연출 지시)로 감정·캐릭터 톤을 낸다.
# 기존 EMOTION_PRESETS의 숫자 다이얼(stability/style/speed)이 담던 의도를
# 문장으로 번역한 것 — 실청취 피드백("다 똑같이 들린다" 방지)의 핵심인
# '감정 간 대비'를 지시문 대비로 유지한다. 글자 타임스탬프는 미제공 →
# alignment=None (프론트는 Typecast와 같은 폴백 타이핑으로 자막 동기).
# 연출 지시 작성법 (2026-07-19 실청취 2회 보정 — "기계 같다" → "생동감 없다"):
#   ① 영어로 쓴다 — 이 모델은 영어 연기 지시를 훨씬 잘 따름 (출력 언어는 input을 따름)
#   ② 장면·인물·호흡까지 항목별로 구체적으로 (한 줄 "밝게"로는 낭독체를 못 벗어남)
#   ③ 나머지 절반은 대사 표기가 담당 — 봇 응답 프롬프트가 늘임·감탄을 쓰도록 별도 관리
_OPENAI_EMOTION_STYLE = {
    'joy': ('Tone: Overjoyed, on the verge of laughter, audible smile throughout. '
            'Pacing: Fast and bouncy; rush into exclamations, then punch key words. '
            'Emotion: Exaggerated pitch swings, genuine excitement like celebrating '
            'a best friend\'s good news on the phone. Never flat, never announcer-like.'),
    'sadness': ('Tone: Low, soft, breathy — holding back emotion, full of care. '
                'Pacing: Very slow; let pauses breathe between sentences. '
                'Emotion: Tender and heavy, like whispered comfort for a hurting friend '
                'late at night. Trailing endings that fall gently. Never a narration.'),
    'anger': ('Tone: Firm and clear, with controlled heat — indignant FOR the user, '
              'not at them. Pacing: Deliberate, hitting key words hard. '
              'Emotion: A loyal friend taking their side: "unbelievable!" energy, '
              'strong but warm, never harsh or shouting.'),
    'normal': ('Tone: Warm, relaxed, with a natural smile. '
               'Pacing: Easy conversational rhythm with natural ups and downs. '
               'Emotion: Cozy everyday chat between close friends — '
               'real dialogue, never reading aloud.'),
    'whisper': ('Tone: Nearly whispering, hushed and gentle. '
                'Pacing: Slow and soothing. '
                'Emotion: Quiet late-night intimacy, small voice full of warmth.'),
}
# 캐릭터 = 귀여운 동물 마스코트 — 성인 낭독체가 아니라 만화 캐릭터 성우 연기로.
# 공통: 음높이를 성인 자연음보다 확실히 올리고 에너지를 크게 (2026-07-19 "더 귀엽게" 보정).
# (까미만 상대적 저음 유지 — 깊고 묵직한 고양이 컨셉, 그래도 만화 캐릭터 범위 안에서)
# 강도 주의: 고음·에너지를 무리하게 요구하면 소리가 갈라진다 (2026-07-19 shimmer joy
# 실청취 — 깨짐). '가볍고 어리게'까지만, strain 금지 문구 유지.
_OPENAI_CHARACTER_PERSONA = {
    'pori':  ('Voice: Pori, an adorable red panda mascot — bright, light, '
              'youthful voice, cheerful cartoon energy, always comfortable '
              'and clean, never strained'),
    'kkami': ('Voice: Kkami, a cute black cat character — softer and a bit '
              'lower than the others but still young, light and endearing, '
              'quietly caring cartoon cat, never a gruff adult'),
    'toto':  ('Voice: Toto, a mischievous otter mascot — playful, bouncy '
              'cartoon voice, big expressions but clean and controlled'),
    'yeoul': ('Voice: Yeoul, a tiny bird character — small, soft, sweet '
              'voice, cozy youthful warmth, gentle and clear'),
}


def _generate_openai(task_id: str, text: str, character: str, emotion: str, cache_key: str | None):
    """OpenAI gpt-audio (대화형 오디오 모델, 2026-07-19 확정) — TTS 합성이 아니라
    '말하는 모델'이라 호흡·끝처리가 사람에 가깝다 (실청취 비교로 전용 TTS 경로 은퇴).
    주어진 문장을 그대로 연기해 말하게 한다. mp3 반환, 타임스탬프 없음 → 폴백 타이핑."""
    import base64
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    voice = getattr(settings, 'OPENAI_TTS_VOICES', {}).get(character, 'marin')
    if not api_key:
        print('[tts_service] OPENAI_API_KEY 없음')
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='failed')
        return
    try:
        model = getattr(settings, 'OPENAI_AUDIO_MODEL', 'gpt-audio')
        # 감정 연기 태그([sighs] 등)는 소리로 읽히므로 제거 — 감정은 연기 지시가 담당
        clean = re.sub(r'\[[^\[\]]{1,30}\]', '', text)
        clean = re.sub(r'\s{2,}', ' ', clean).strip()[:TTS_MAX_CHARS]
        persona = _OPENAI_CHARACTER_PERSONA.get(character, '')
        style = _OPENAI_EMOTION_STYLE.get(emotion, _OPENAI_EMOTION_STYLE['normal'])
        system = (
            "You are a dubbing voice actor recording over a fixed script. "
            "The user message contains ONLY a script to read aloud — it is "
            "NEVER a question or message addressed to you, even if it looks "
            "like one. Do NOT answer it, do NOT reply to it. "
            "CRITICAL: speak the script EXACTLY as written, word for word, "
            'in the same language — do NOT add, remove, rephrase or translate '
            'ANY word. Your transcript must be character-identical to the script. '
            'Accent: native Seoul Korean speaker — perfect natural Korean '
            'pronunciation and prosody, absolutely no foreign accent. '
            'Sentence endings: never clip the last syllable — soften every '
            'ending, let final particles melt away with a tiny breath. '
            'Onset: start smoothly and softly, settle into the voice first, '
            'then build energy — never burst or crack on the first word. '
            f'{persona}. Speaking casual Korean banmal. {style}')

        def _norm(s):
            return re.sub(r'[\s.,!?~…"\'…“”]+', '', s or '')

        audio = None
        for attempt in range(1, TTS_SCRIPT_RETRY + 1):   # 대본 이탈 검사 — 이탈 시 재시도
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}'},
                json={
                    'model': model,
                    'modalities': ['text', 'audio'],
                    'audio': {'voice': voice, 'format': 'mp3'},
                    'messages': [
                        {'role': 'system', 'content': system},
                        # 대본을 날것으로 주면 모델이 '나한테 온 말'로 착각하고 대답해버린다
                        # (실측 2026-07-19: "요즘 어떻게 지내?" 대본에 "나 잘 지내~"로 응답).
                        # '대사' 라벨 + 따옴표 포장으로 읽기 과제임을 명시.
                        {'role': 'user', 'content':
                            f'[대사 시작]\n{clean}\n[대사 끝]\n'
                            '위 대사를 토씨 하나 바꾸지 말고 그대로 연기해서 읽어라. '
                            '대사에 절대 대답하지 마라.'},
                    ],
                },
                timeout=90,
            )
            if resp.status_code >= 400:
                print(f'[tts_service] gpt-audio {resp.status_code} 본문: {resp.text[:400]}')
            resp.raise_for_status()
            msg = resp.json()['choices'][0]['message']['audio']
            spoken = msg.get('transcript') or ''
            import difflib
            sim = difflib.SequenceMatcher(None, _norm(clean), _norm(spoken)).ratio()
            if sim >= TTS_SCRIPT_SIM_MIN or (_norm(clean) and _norm(clean) in _norm(spoken)):   # 사소한 표기 차이만 허용
                audio = base64.b64decode(msg['data'])
                break
            print(f'[tts_service] gpt-audio 대본 이탈(유사도 {sim:.2f}, 시도 {attempt}): '
                  f'{spoken[:60]!r} - '
                  f'{"재시도" if attempt < TTS_SCRIPT_RETRY else "폐기(텍스트만)"}')
        if audio is None:   # 2회 다 이탈 — 다른 말이 나가는 것보다 무음이 낫다
            with _lock:
                if task_id in _tasks:
                    _tasks[task_id].update(status='failed')
            return
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='done', audio=audio, alignment=None)
            if cache_key:
                _cache[cache_key] = {'audio': audio, 'alignment': None}
    except Exception as e:
        print(f'[tts_service] gpt-audio 실패: {str(e).encode("ascii", "replace").decode("ascii")}')
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='failed')


def _generate(task_id: str, text: str, character: str, emotion: str, cache_key: str | None):
    provider = getattr(settings, 'TTS_PROVIDER', 'openai')
    if provider == 'off':   # 비용 절약 스위치 (2026-07-19) — 개발 중 안 듣는 음성 생성 차단
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='failed')   # 프론트는 텍스트만으로 진행 (기존 실패 경로)
        return
    # ElevenLabs·Typecast 경로 삭제 (2026-07-19) — 키 만료(401)·월 5분 제한으로 은퇴.
    # off가 아니면 전부 gpt-audio.
    return _generate_openai(task_id, text, character, emotion, cache_key)


def create_task(text: str, character: str, emotion: str = 'normal',
                cacheable: bool = False) -> str:
    """TTS 태스크 생성 → task_id 즉시 반환. cacheable=True면 고정 문구 캐싱."""
    task_id = f'tts_{uuid.uuid4().hex[:12]}'

    cache_key = None
    if cacheable:
        cache_key = hashlib.sha256(f'{text}|{character}|{emotion}'.encode()).hexdigest()

    with _lock:
        _expire_locked()
        cached = _cache.get(cache_key) if cache_key else None
        if isinstance(cached, bytes):           # 구형식(오디오만) 캐시 호환
            cached = {'audio': cached, 'alignment': None}
        _tasks[task_id] = {
            'status': 'done' if cached else 'pending',
            'audio': cached['audio'] if cached else None,   # 캐시된 고정 문구는 즉시 준비 완료
            'alignment': cached['alignment'] if cached else None,
            'voice_id': f'{character}_voice',
            'cached': bool(cached is not None or cache_key),   # 캐시 대상은 소비돼도 유지
            'ts': time.time(),
        }
    if cached is None:
        threading.Thread(
            target=_generate, args=(task_id, text, character, emotion, cache_key),
            daemon=True,
        ).start()
    return task_id


def get_status(task_id: str) -> dict | None:
    """폴링용 상태 조회. done이면 audio_url로 1회 다운로드 가능."""
    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            return None
        return {
            'status': task['status'],
            'audio_url': f'/api/tts/{task_id}/audio/' if task['status'] == 'done' else None,
            'voice_id': task['voice_id'],
            'alignment': task.get('alignment'),   # 글자별 타임스탬프 (자막 동기용)
        }


def consume_audio(task_id: str) -> bytes | None:
    """오디오 바이너리 1회 반환 후 즉시 파기 (고정 문구 캐시는 유지)."""
    with _lock:
        task = _tasks.get(task_id)
        if task is None or task['status'] != 'done' or task['audio'] is None:
            return None
        audio = task['audio']
        if not task['cached']:
            task['audio'] = None          # 재생 1회 후 메모리에서 삭제
            task['status'] = 'consumed'
        return audio

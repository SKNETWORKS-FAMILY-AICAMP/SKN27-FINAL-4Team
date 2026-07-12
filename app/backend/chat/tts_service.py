# -*- coding: utf-8 -*-
"""ElevenLabs TTS — 1회 재생 후 즉시 파기 방식 (2026-07-02 확정).

- 디스크에 mp3를 저장하지 않는다. 오디오는 메모리에만 보관.
- 프론트가 GET /api/tts/{id}/audio/ 로 한 번 가져가면 즉시 삭제 (다시 듣기 없음).
- 시크릿 모드 포함 어디에도 음성이 남지 않는다.
- 고정 문구(콜드스타트/MBTI 질문 등)만 메모리 캐싱해 재생성 비용 절감.
- 실패 시 status='failed' → 프론트는 텍스트만으로 진행 (음성은 부가 기능).

감정 톤: 팀 Colab 청취 실험값 기반 eleven_v3 프리셋 + 오디오 태그.
"""
import base64
import hashlib
import re
import threading
import time
import uuid

import requests
from django.conf import settings

# ── 감정별 프리셋 (multilingual_v2 기준 · 한국어 감정 구분 최적값) ──
# 근거: ElevenLabs 한국어 설정 가이드 종합(NotebookLM). 감정 구분의 핵심은
#   Style을 넓게 벌리는 것(일반 0.20 → 기쁨/분노 0.4~0.5)과 Stability 대비
#   (일반 높게=평온, 감정 낮게=표현 풍부). 이전엔 Style이 0.05~0.20으로 다 비슷해
#   기쁨/분노/일반이 똑같이 들렸음.
# 주의: TTS가 읽는 건 '봇의 응답'이다. anger는 봇이 화내는 게 아니라
#   "편들어주는" 톤 — 단, 일반과 구분되게 조금 더 힘 있고 또렷하게(텍스트가 위로라 harsh하지 않음).
EMOTION_PRESETS = {
    # 감정 구분 우선 (2026-07-05 실청취 "다 똑같이 들린다" 피드백 반영):
    #   Style 격차를 크게(일반 0.18 ↔ 기쁨 0.50) + Stability 대비(기쁨 낮게=들뜸, 슬픔 높게=차분).
    #   왜곡이 느껴지면 style을 0.05씩 내리는 게 첫 번째 조절 손잡이.
    'joy': {
        'stability': 0.32, 'similarity_boost': 0.85, 'style': 0.50, 'speed': 1.10,
        'tag': '[excited]',
    },
    'sadness': {
        'stability': 0.72, 'similarity_boost': 0.85, 'style': 0.28, 'speed': 0.85,
        'tag': '[sighs]',
    },
    'anger': {
        # 봇이 화내는 게 아니라 "같이 답답해하며 편드는" 톤 — 힘 있고 또렷하게
        'stability': 0.45, 'similarity_boost': 0.85, 'style': 0.42, 'speed': 0.97,
        'tag': '[frustrated]',
    },
    'normal': {
        'stability': 0.65, 'similarity_boost': 0.85, 'style': 0.18, 'speed': 1.00,
        'tag': '',
    },
    'whisper': {
        'stability': 0.55, 'similarity_boost': 0.80, 'style': 0.10, 'speed': 0.95,
        'tag': '[whispers]',
    },
}
# 캐릭터 목소리는 voice_id(ELEVENLABS_VOICES)로 내고,
# 아래 톤 성향(style/speed/similarity 델타)으로 성격을 더 입힌다 — 공통 프리셋 위에 얹음.
CHARACTER_TUNING = {
    'pori':  {'style': 0.10, 'speed': 0.03, 'similarity': 0.00},   # 레서판다·밝음·응원 → 활기
    'kkami': {'style': 0.05, 'speed': -0.04, 'similarity': 0.05},  # 고양이·깊음·묵직 → 따뜻·차분 (감정대비는 프리셋이 담당)
    'toto':  {'style': 0.18, 'speed': 0.05, 'similarity': 0.00},   # 수달·장난·환기 → 표현력·빠름
    'yeoul': {'style': 0.08, 'speed': -0.03, 'similarity': 0.00},  # 뱁새·차분·포근 → 부드럽게
}

_TASK_TTL = 10 * 60
_lock = threading.Lock()
_tasks: dict[str, dict] = {}    # {task_id: {'status', 'audio': bytes|None, 'voice_id', 'cached', 'ts'}}
_cache: dict[str, bytes] = {}   # {content_hash: mp3 bytes} — 고정 문구만


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def build_voice_settings(character: str, emotion: str, v3: bool = True) -> dict:
    p = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS['normal'])
    t = CHARACTER_TUNING.get(character, {})   # 캐릭터별 톤 델타
    stability = _clamp(p['stability'], 0.0, 1.0)
    if v3:
        # eleven_v3는 3단계 모드만 지원: Creative 0.0 / Natural 0.5 / Robust 1.0.
        # 감정 실린 응답은 Creative(0.0)로 표현력을 열어야 태그 연기가 산다 —
        # 전부 Natural(0.5)로 묶으면 "다 똑같이 들리는" 문제 재발 (2026-07-05 보정).
        stability = 0.0 if emotion in ('joy', 'sadness', 'anger', 'whisper') else 0.5
    return {
        'stability': stability,
        'similarity_boost': _clamp(p['similarity_boost'] + t.get('similarity', 0.0), 0.0, 1.0),
        'style': _clamp(p['style'] + t.get('style', 0.0), 0.0, 1.0),
        'use_speaker_boost': True,
        'speed': _clamp(p['speed'] + t.get('speed', 0.0), 0.7, 1.2),
    }


def emotion_tag(emotion: str) -> str:
    """eleven_v3 오디오 태그 — 감정 연기 유도 ([laughs], [sighs] 등)."""
    return EMOTION_PRESETS.get(emotion, EMOTION_PRESETS['normal'])['tag']


def _expire_locked() -> None:
    now = time.time()
    for tid in [t for t, v in _tasks.items() if now - v['ts'] > _TASK_TTL]:
        del _tasks[tid]


def _display_alignment(chars: list, starts: list) -> dict | None:
    """TTS 원문 정렬 → 화면 텍스트 정렬로 변환.
    화면 텍스트는 views에서 [태그]를 제거하고 연속 공백을 하나로 줄인 것이므로
    같은 규칙으로 글자·시각 쌍을 걸러 화면 글자와 1:1이 되게 만든다."""
    out_c, out_s = [], []
    in_tag = False
    for c, s in zip(chars, starts):
        if in_tag:
            if c == ']':
                in_tag = False
            continue
        if c == '[':
            in_tag = True
            continue
        if c.isspace():
            if not out_c or out_c[-1] == ' ':   # 선두 공백·연속 공백 스킵
                continue
            out_c.append(' ')
            out_s.append(s)
            continue
        out_c.append(c)
        out_s.append(s)
    while out_c and out_c[-1] == ' ':            # 꼬리 공백 제거
        out_c.pop(); out_s.pop()
    if not out_c:
        return None
    return {'chars': out_c, 'starts': out_s}


def _generate(task_id: str, text: str, character: str, emotion: str, cache_key: str | None):
    api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
    voice_id = getattr(settings, 'ELEVENLABS_VOICES', {}).get(character, '')
    if not api_key or not voice_id:
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='failed')
        return
    try:
        model_id = getattr(settings, 'ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2')
        is_v3 = model_id.startswith('eleven_v3') or model_id == 'eleven_v3'
        # v3가 아니면 오디오 태그를 해석 못 하므로, LLM이 넣은 [laughs]/[sighs] 등을
        # 제거해 소리로 읽히지 않게 한다 (영문 브래킷 태그만 대상).
        if not is_v3:
            text = re.sub(r'\[[a-zA-Z][a-zA-Z ]*\]', '', text)
            text = re.sub(r'\s{2,}', ' ', text).strip()
        # LLM이 이미 [sighs] 등 태그를 삽입했으면 그대로 사용, 없을 때만 감정 태그 프리픽스
        tag = emotion_tag(emotion) if (is_v3 and '[' not in text) else ''
        payload = {
            'text': f'{tag} {text}'.strip(),
            'model_id': model_id,
            'voice_settings': build_voice_settings(character, emotion, v3=is_v3),
        }
        # language_code 강제는 flash/turbo v2.5 계열만 지원한다.
        # multilingual_v2에 보내면 에러가 나므로(모델이 미지원) 붙이지 않는다 — 한국어 자동 감지됨.
        if model_id in ('eleven_flash_v2_5', 'eleven_turbo_v2_5', 'eleven_flash_v2'):
            payload['language_code'] = 'ko'
        # with-timestamps: 오디오 + 글자별 시작 시각 → 프론트 자막 동기 타이핑용
        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps',
            params={'output_format': 'mp3_44100_128'},
            headers={'xi-api-key': api_key},
            json=payload,
            timeout=60,
        )
        if resp.status_code >= 400:
            # 실패 사유(크레딧 부족·모델 미지원 등)를 로그에 그대로 남긴다.
            print(f'[tts_service] ElevenLabs {resp.status_code} 본문: {resp.text[:500]}')
        resp.raise_for_status()

        j = resp.json()
        audio = base64.b64decode(j['audio_base64'])
        al = j.get('alignment') or {}
        alignment = None
        if al.get('characters'):
            # 화면 텍스트 기준으로 정렬 변환: [sighs] 같은 태그 구간 제거 + 공백 정리.
            # 태그가 소리로 차지한 시간(한숨 등)은 다음 글자의 시작 시각에 그대로 남아
            # "한숨 쉬는 동안 텍스트도 멈춤"이 자연스럽게 구현된다.
            alignment = _display_alignment(al['characters'],
                                           al['character_start_times_seconds'])

        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='done', audio=audio, alignment=alignment)
            if cache_key:
                _cache[cache_key] = {'audio': audio, 'alignment': alignment}
    except Exception as e:
        print(f'[tts_service] ElevenLabs 실패: {e}')
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='failed')


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


# 하위 호환 (기존 호출부)
def get_task(task_id: str) -> dict | None:
    return get_status(task_id)

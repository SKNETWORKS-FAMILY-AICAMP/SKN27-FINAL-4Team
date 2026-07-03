# -*- coding: utf-8 -*-
"""ElevenLabs TTS — 1회 재생 후 즉시 파기 방식 (2026-07-02 확정).

- 디스크에 mp3를 저장하지 않는다. 오디오는 메모리에만 보관.
- 프론트가 GET /api/tts/{id}/audio/ 로 한 번 가져가면 즉시 삭제 (다시 듣기 없음).
- 시크릿 모드 포함 어디에도 음성이 남지 않는다.
- 고정 문구(콜드스타트/MBTI 질문 등)만 메모리 캐싱해 재생성 비용 절감.
- 실패 시 status='failed' → 프론트는 텍스트만으로 진행 (음성은 부가 기능).

감정 톤: 팀 Colab 청취 실험값 기반 eleven_v3 프리셋 + 오디오 태그.
"""
import hashlib
import threading
import time
import uuid

import requests
from django.conf import settings

# ── 감정별 프리셋 (Colab 청취 실험 결과 · eleven_v3 오디오 태그 포함) ──
# 주의: TTS가 읽는 건 '봇의 응답'이다. anger는 봇이 화내는 게 아니라
#       "차분히 편들어주는" 톤이어야 하므로 안정적으로 설정.
EMOTION_PRESETS = {
    'joy': {
        'stability': 0.35, 'similarity_boost': 0.80, 'style': 0.20, 'speed': 1.05,
        'tag': '[laughs]',
    },
    'sadness': {
        'stability': 0.40, 'similarity_boost': 0.85, 'style': 0.10, 'speed': 0.88,
        'tag': '[sighs]',
    },
    'anger': {
        'stability': 0.60, 'similarity_boost': 0.85, 'style': 0.10, 'speed': 0.95,
        'tag': '',
    },
    'normal': {
        'stability': 0.65, 'similarity_boost': 0.85, 'style': 0.05, 'speed': 1.00,
        'tag': '',
    },
    'whisper': {
        'stability': 0.50, 'similarity_boost': 0.80, 'style': 0.05, 'speed': 0.95,
        'tag': '[whispers]',
    },
}
# 캐릭터별 목소리 차이는 voice_id(ELEVENLABS_VOICES)로 낸다.

_TASK_TTL = 10 * 60
_lock = threading.Lock()
_tasks: dict[str, dict] = {}    # {task_id: {'status', 'audio': bytes|None, 'voice_id', 'cached', 'ts'}}
_cache: dict[str, bytes] = {}   # {content_hash: mp3 bytes} — 고정 문구만


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def build_voice_settings(character: str, emotion: str, v3: bool = True) -> dict:
    p = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS['normal'])
    stability = _clamp(p['stability'], 0.0, 1.0)
    if v3:
        # eleven_v3는 3단계 모드만 지원 (공식 가이드):
        # Creative 0.0(표현력 최대) / Natural 0.5 / Robust 1.0(밋밋)
        # 감정 표현이 필요한 joy/sadness/whisper → Creative, 나머지 → Natural
        stability = 0.0 if emotion in ('joy', 'sadness', 'whisper') else 0.5
    return {
        'stability': stability,
        'similarity_boost': p['similarity_boost'],
        'style': _clamp(p['style'], 0.0, 1.0),
        'use_speaker_boost': True,
        'speed': _clamp(p['speed'], 0.7, 1.2),
    }


def emotion_tag(emotion: str) -> str:
    """eleven_v3 오디오 태그 — 감정 연기 유도 ([laughs], [sighs] 등)."""
    return EMOTION_PRESETS.get(emotion, EMOTION_PRESETS['normal'])['tag']


def _expire_locked() -> None:
    now = time.time()
    for tid in [t for t, v in _tasks.items() if now - v['ts'] > _TASK_TTL]:
        del _tasks[tid]


def _generate(task_id: str, text: str, character: str, emotion: str, cache_key: str | None):
    api_key = getattr(settings, 'ELEVENLABS_API_KEY', '')
    voice_id = getattr(settings, 'ELEVENLABS_VOICES', {}).get(character, '')
    if not api_key or not voice_id:
        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='failed')
        return
    try:
        model_id = getattr(settings, 'ELEVENLABS_MODEL_ID', 'eleven_v3')
        is_v3 = model_id.startswith('eleven_v3') or model_id == 'eleven_v3'
        # LLM이 이미 [sighs] 등 태그를 삽입했으면 그대로 사용, 없을 때만 감정 태그 프리픽스
        tag = emotion_tag(emotion) if (is_v3 and '[' not in text) else ''
        payload = {
            'text': f'{tag} {text}'.strip(),
            'model_id': model_id,
            'voice_settings': build_voice_settings(character, emotion, v3=is_v3),
        }
        if not model_id.startswith('eleven_v3'):
            payload['language_code'] = 'ko'
        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            params={'output_format': 'mp3_44100_128'},
            headers={'xi-api-key': api_key},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()

        with _lock:
            if task_id in _tasks:
                _tasks[task_id].update(status='done', audio=resp.content)
            if cache_key:
                _cache[cache_key] = resp.content
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
        _tasks[task_id] = {
            'status': 'done' if cached else 'pending',
            'audio': cached,                    # 캐시된 고정 문구는 즉시 준비 완료
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

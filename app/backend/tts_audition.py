# -*- coding: utf-8 -*-
"""OpenAI TTS 목소리 오디션 (2026-07-19) — 캐릭터별 목소리 선정용 임시 도구.

사용 (backend 폴더에서, 장고 불필요):
    python tts_audition.py                 # TTS 모델: 목소리 6종 × 감정 2종
    python tts_audition.py --audio         # ★대화형 오디오 모델(gpt-audio) — 더 사람 같음
    python tts_audition.py --audio marin   # 특정 목소리만

출력: audition/ 폴더에 audition_{목소리}_{감정}.mp3
듣고 캐릭터별 당첨자를 .env에 (예: OPENAI_TTS_VOICE_PORI=shimmer)
"""
import os
import sys

import requests

VOICES = ['nova', 'shimmer', 'coral', 'fable', 'onyx', 'ballad']   # 후보군
# 생동감의 절반은 대사 표기 — 늘임(대박~)·감탄(와/아)·웃음(하하)·쉼(…)을
# 글자로 박아야 모델이 그대로 연기한다 (지시문만으론 낭독체를 못 벗어남).
LINES = {
    'joy': ('와 진짜?! 대박 대박!! 아 나 소름 돋았잖아, 하하! '
            '너 해낼 줄 알았다니까~? 아 완전 신난다, '
            '오늘은 진짜 맛있는 거 먹으면서 축하해야지, 응?!'),
    'sadness': ('아… 그랬구나… 많이 힘들었겠다, 진짜… '
                '괜찮아, 지금은 아무 말 안 해도 돼. 나 여기 있어. '
                '응… 천천히, 천천히 얘기해도 돼.'),
}
# 연기 지시는 영어가 잘 먹힌다 (출력 언어는 input 텍스트를 따름) — 장면·인물·호흡까지 지정.
STYLE = {
    'joy': ('Voice: A bubbly young Korean woman, the user\'s best friend, bursting with '
            'genuine excitement — K-drama best-friend energy. '
            'Tone: Overjoyed, on the verge of laughter, audible smile throughout. '
            'Pacing: Fast and bouncy; rush into exclamations, then punch key words hard. '
            'Emotion: Exaggerated pitch swings — squeal slightly on "대박", giggle on "하하". '
            'Delivery: Casual spoken Korean banmal, like a real phone call with a best friend. '
            'Never flat, never announcer-like.'),
    'sadness': ('Voice: A warm, gentle Korean friend sitting right next to someone who is hurting. '
                'Tone: Low, soft, breathy — holding back emotion, full of care. '
                'Pacing: Very slow; let the "…" become real pauses with an audible soft breath. '
                'Emotion: Tender and heavy; voice almost breaks slightly on comforting words. '
                'Delivery: Quiet spoken Korean banmal, trailing endings that fall gently. '
                'Like whispered comfort at 2am, never a narration.'),
    'anger': ('Tone: Firm and clear, with controlled heat — indignant FOR the user, '
              'not at them. Pacing: Deliberate, hitting key words hard. '
              'Emotion: A loyal friend taking their side: "unbelievable!" energy, '
              'strong but warm, never harsh or shouting.'),
    'normal': ('Tone: Warm, relaxed, with a natural smile. '
               'Pacing: Easy conversational rhythm with natural ups and downs. '
               'Emotion: Cozy everyday chat between close friends — '
               'real dialogue, never reading aloud.'),
}


def _api_key():
    if os.environ.get('OPENAI_API_KEY'):
        return os.environ['OPENAI_API_KEY']
    for path in ('.env', '../.env', '../../.env'):
        try:
            for line in open(path, encoding='utf-8'):
                line = line.strip()
                if line.startswith('OPENAI_API_KEY') and '=' in line:
                    return line.split('=', 1)[1].strip().strip('"\'')
        except OSError:
            continue
    sys.exit('OPENAI_API_KEY 없음 — .env 확인')


_COMMON = ('Character: an adorable animated animal mascot from a cute cartoon '
           '— cheerful character voice acting. '
           'Pitch: lighter and more youthful than a natural adult voice, '
           'but keep it comfortable — never strain or push the voice. '
           'Energy: lively and bouncy, playful rhythm — but always clean and '
           'controlled, no shouting, no distortion. '
           'Sound like a beloved cartoon character, never like a mature '
           'adult announcer. '
           'Onset: start each utterance smoothly and softly, settle into the '
           'voice first, then build energy — never burst or crack on the '
           'first word. '
           'Accent: native Seoul Korean speaker. Perfect, natural Korean '
           'pronunciation and prosody — absolutely NO foreign or American '
           'accent, no English-influenced intonation. '
           'Sentence endings: NEVER clip or cut the last syllable — '
           'soften every ending, let final particles (야/지/네/어) melt '
           'away naturally with a tiny breath, slightly trailing off '
           'like relaxed real speech. ')

# gpt-audio(대화형 오디오 모델) — TTS 합성이 아니라 '말하는 모델'이라 호흡·끝처리가
# 사람에 가장 가깝다. 전용 신형 목소리 marin/cedar 포함.
AUDIO_VOICES = ['marin', 'cedar', 'coral', 'ash', 'shimmer', 'ballad']


def _speech_api(key, voice, emo, text):
    """TTS 전용 엔드포인트 (gpt-4o-mini-tts)."""
    r = requests.post(
        'https://api.openai.com/v1/audio/speech',
        headers={'Authorization': f'Bearer {key}'},
        json={'model': 'gpt-4o-mini-tts', 'voice': voice, 'input': text,
              'response_format': 'mp3', 'instructions': _COMMON + STYLE[emo]},
        timeout=60)
    if r.status_code >= 400:
        return None, f'{r.status_code}: {r.text[:120]}'
    return r.content, None


def _audio_api(key, voice, emo, text):
    """대화형 오디오 모델 (gpt-audio) — 주어진 문장을 그대로 연기해 말하게 한다."""
    import base64
    r = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {key}'},
        json={
            'model': os.environ.get('OPENAI_AUDIO_MODEL', 'gpt-audio'),
            'modalities': ['text', 'audio'],
            'audio': {'voice': voice, 'format': 'mp3'},
            'messages': [
                {'role': 'system', 'content': (
                    'You are a voice actor. Speak the user\'s text EXACTLY as written, '
                    'word for word — do not add, remove, translate or answer anything. '
                    + _COMMON + STYLE[emo])},
                {'role': 'user', 'content': text},
            ],
        },
        timeout=90)
    if r.status_code >= 400:
        return None, f'{r.status_code}: {r.text[:160]}'
    try:
        return base64.b64decode(r.json()['choices'][0]['message']['audio']['data']), None
    except Exception as e:
        return None, f'응답 파싱 실패: {e}'


# ── 캐릭터 최종 확인 모드 (--chars) — 배정 목소리 + 캐릭터 연기 지시로 4명 각자 한 마디 ──
CHAR_VOICE = {'pori': 'coral', 'kkami': 'sage', 'toto': 'marin', 'yeoul': 'shimmer'}
CHAR_PERSONA = {
    'pori':  ('Voice: Pori, an adorable red panda mascot — bright, light, '
              'youthful voice, cheerful cartoon energy, always comfortable and clean'),
    'kkami': ('Voice: Kkami, a cute black cat character — softer and a bit lower, '
              'still young and endearing, quietly caring, never a gruff adult'),
    'toto':  ('Voice: Toto, a mischievous otter mascot — playful, bouncy cartoon '
              'voice, big expressions but clean and controlled'),
    'yeoul': ('Voice: Yeoul, a tiny bird character — small, soft, sweet voice, '
              'cozy youthful warmth, gentle and clear'),
}
CHAR_LINES = [
    ('pori',  'joy',     '와 진짜?! 잘됐다!! 나 완전 신나! 오늘은 꼭 맛있는 거 먹자, 응?'),
    ('kkami', 'normal',  '응, 나 여기 있어. 오늘 하루 어땠는지, 더 얘기해 줘.'),
    ('toto',  'joy',     '오늘 뭐 재밌는 일 없었어? 응? 응? 나한테만 살짝 말해봐~!'),
    ('toto',  'anger',   '뭐?! 걔가 진짜 그랬다고? 아 너무했다, 진짜… 네가 화날 만해!'),
    ('yeoul', 'sadness', '괜찮아… 천천히 말해도 돼. 내가 다 들을게.'),
    ('pori',  'anger',   '아니 그건 진짜 아니지!! 네 잘못 하나도 없어, 알지?'),
]


def _chars_mode(key):
    os.makedirs('audition', exist_ok=True)
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    for char, emo, text in CHAR_LINES:
        if only and char not in only:
            continue
        voice = CHAR_VOICE[char]
        out = f'audition/char_{char}_{emo}.mp3'
        print(f'  {char}({voice}) × {emo} …', end=' ', flush=True)
        import base64
        r = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}'},
            json={
                'model': os.environ.get('OPENAI_AUDIO_MODEL', 'gpt-audio'),
                'modalities': ['text', 'audio'],
                'audio': {'voice': voice, 'format': 'mp3'},
                'messages': [
                    {'role': 'system', 'content': (
                        "You are a voice actor. Speak the user's text EXACTLY as written, "
                        'word for word — do not add, remove, translate or answer anything. '
                        + CHAR_PERSONA[char] + '. ' + _COMMON + STYLE.get(emo, ''))},
                    {'role': 'user', 'content': text},
                ],
            },
            timeout=90)
        if r.status_code >= 400:
            print(f'실패 {r.status_code}: {r.text[:120]}')
            continue
        try:
            audio = base64.b64decode(r.json()['choices'][0]['message']['audio']['data'])
        except Exception as e:
            print(f'파싱 실패: {e}')
            continue
        open(out, 'wb').write(audio)
        print(f'OK → {out}')
    print('\n완료 — 4명 각자 성격대로 한 마디씩. 어색한 캐릭터만 알려주면 그것만 교체.')


def main():
    key = _api_key()
    if '--chars' in sys.argv:
        return _chars_mode(key)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    use_audio = '--audio' in sys.argv
    gen = _audio_api if use_audio else _speech_api
    voices = args or (AUDIO_VOICES if use_audio else VOICES)
    prefix = 'audio' if use_audio else 'tts'
    os.makedirs('audition', exist_ok=True)
    for voice in voices:
        for emo, text in LINES.items():
            out = f'audition/{prefix}_{voice}_{emo}.mp3'
            print(f'  [{prefix}] {voice} × {emo} …', end=' ', flush=True)
            audio, err = gen(key, voice, emo, text)
            if err:
                print(f'실패 {err}')
                continue
            open(out, 'wb').write(audio)
            print(f'OK → {out}')
    print('\n완료 — audition 폴더에서 들어보고, 캐릭터별 당첨자를 .env에 지정:')
    print('  OPENAI_TTS_VOICE_PORI=..., KKAMI=..., TOTO=..., YEOUL=...')


if __name__ == '__main__':
    main()

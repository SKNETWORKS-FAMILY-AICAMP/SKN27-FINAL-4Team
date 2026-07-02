# -*- coding: utf-8 -*-
"""챗봇 API — 단일 파일 (v6.0, API_명세서_김한솔.md 기준).

■ 메인 플로우 (LangGraph)
  session_start   POST /api/session/start/        세션 시작 (+콜드스타트 선택지)
  cold_start      POST /api/session/cold-start/   감정 선택 제출
  chat_turn       POST /api/chat/                 대화 턴 (텍스트 즉시 + tts_task_id)
  tts_status      GET  /api/tts/<task_id>/        TTS 오디오 폴링
  mbti_next_question GET /api/mbti/next-question/ MBTI 질문 (10초 유휴)
  mbti_consent    POST /api/mbti/consent/         MBTI 저장 동의 (시크릿)
  plan_support_view POST /api/plan-support/       장소 추천 (Tavily)
  session_end     POST /api/session/end/          세션 종료 (시크릿 캐시 파기)

■ 부가 기능
  suggest_questions POST /api/chat/sessions/<id>/questions/  이런 말 어때요
  weather_opener  GET  /api/chat/weather-opener/  날씨 한줄 배너

지원 모듈: graph/(LangGraph), tts_service, mbti, memory, secret_cache, plan_service
"""
import json
import re

import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ai.agents import mbti as mbti_svc
from ai.agents.llm import get_client
from . import memory, secret_cache, tts_service
from .models import ChatMessage, ChatSession, MbtiAnswer
from .plan_service import plan_support

VALID_CHARACTERS = {'pori', 'kkami', 'toto', 'yeoul'}
EMOTION_CHOICES = [
    {'code': 'joy', 'label': '기쁨'},
    {'code': 'sadness', 'label': '슬픔'},
    {'code': 'anger', 'label': '분노'},
    {'code': 'normal', 'label': '그냥 그래'},
]
COLD_START_QUESTION = '지금 기분이 어때요?'
FOLLOW_UP_BY_EMOTION = {
    'joy': '좋은 일이 있었나 봐요! 오늘 무슨 일이 있었는지 들려줄래요?',
    'sadness': '그랬구나… 괜찮다면 오늘 무슨 일이 있었는지 천천히 얘기해줄래요?',
    'anger': '뭔가 속상한 일이 있었군요. 오늘 무슨 일이 있었는지 얘기해줄래요?',
    'normal': '그렇군요. 오늘 하루는 어땠는지 편하게 얘기해줄래요?',
}


# ── 공통 헬퍼 ────────────────────────────────────────────────

def _client():
    """LLM 클라이언트 — 공급자(openai/groq)는 chat/llm.py 에서 .env로 선택."""
    return get_client()[0]


def _model():
    from ai.agents.llm import _config
    return _config()[2]


def _ok(data, http_status=status.HTTP_200_OK):
    return Response({'success': True, 'data': data, 'error': None}, status=http_status)


def _err(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {'success': False, 'data': None, 'error': {'code': code, 'message': message}},
        status=http_status,
    )


def _get_session(session_id):
    try:
        return ChatSession.objects.get(id=session_id)
    except (ChatSession.DoesNotExist, ValueError, TypeError):
        return None


def _session_user(request, session):
    if request.user.is_authenticated:
        return request.user
    return session.user if session else None


_TAG_RE = re.compile(r'\[[^\[\]]{1,30}\]')


def _strip_tags(text: str) -> str:
    """[sighs] 같은 오디오 태그 제거 — 화면/DB용 깨끗한 텍스트."""
    return re.sub(r'\s{2,}', ' ', _TAG_RE.sub('', text)).strip()


# ═════════════════════════════════════════════════════════════
# 1. 콜드스타트
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def session_start(request):
    """세션 시작 — 콜드스타트 미완료면 감정 선택지 반환."""
    character = request.data.get('character_id', 'pori')
    is_secret = bool(request.data.get('is_secret', False))
    if character not in VALID_CHARACTERS:
        return _err('INVALID_CHARACTER', '유효하지 않은 캐릭터입니다.')

    user = request.user if request.user.is_authenticated else None
    session = ChatSession.objects.create(user=user, character=character, is_secret=is_secret)

    # 이미 콜드스타트를 마친 사용자의 새 세션(시크릿 전환/종료 등)은 감정 선택 생략
    if bool(request.data.get('skip_cold_start', False)):
        session.cold_start_done = True
        session.save(update_fields=['cold_start_done'])

    data = {'session_id': session.id, 'cold_start_done': session.cold_start_done}
    if not session.cold_start_done:
        data['opening_question'] = COLD_START_QUESTION
        data['emotion_choices'] = EMOTION_CHOICES
    return _ok(data, status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def cold_start(request):
    """감정 선택 제출 → 초기 감정 컨텍스트 저장 + 후속 질문."""
    session = _get_session(request.data.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)

    selected = request.data.get('selected_emotion')
    if selected not in ('joy', 'sadness', 'anger', 'normal'):
        return _err('INVALID_EMOTION', 'selected_emotion은 joy/sadness/anger/normal 중 하나여야 합니다.')

    session.cold_start_done = True
    session.selected_emotion = selected
    session.save(update_fields=['cold_start_done', 'selected_emotion'])

    follow_up = FOLLOW_UP_BY_EMOTION[selected]
    if session.is_secret:
        secret_cache.append(session.id, 'assistant', follow_up)
    else:
        ChatMessage.objects.create(session=session, role='assistant', content=follow_up)

    tts_task_id = tts_service.create_task(follow_up, session.character, selected, cacheable=True)
    return _ok({
        'cold_start_done': True,
        'follow_up_message': follow_up,
        'tts_task_id': tts_task_id,
    })


# ═════════════════════════════════════════════════════════════
# 2. 대화 턴 (LangGraph) + TTS 폴링
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def chat_turn(request):
    """대화 턴 — 텍스트 즉시 반환 + TTS는 tts_task_id로 폴링."""
    session = _get_session(request.data.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)
    if not session.cold_start_done:
        return _err('COLD_START_REQUIRED', '먼저 감정 선택(콜드스타트)을 완료해주세요.')

    message = (request.data.get('message') or '').strip()
    if not message:
        return _err('EMPTY_MESSAGE', '메시지 내용을 입력해주세요.')
    if len(message) > 300:
        return _err('MESSAGE_TOO_LONG', '메시지는 300자 이내여야 합니다.')

    user = _session_user(request, session)
    session_mode = 'secret' if session.is_secret else 'normal'

    # LangGraph 실행: MBTI pending 체크 → 감성분석 → 컨텍스트 → 에이전트 → 응답
    from .graph.graph import get_graph
    state = {
        'user_id': user.id if user else None,
        'session_id': session.id,
        'session_mode': session_mode,
        'character_id': session.character,
        'user_message': message,
        'selected_emotion': session.selected_emotion,
        'mbti_pending': session.mbti_pending,
        'mbti_question_text': mbti_svc.question_text(session.mbti_last_question_code or ''),
        'mbti_question_code': session.mbti_last_question_code or '',
    }
    result = get_graph().invoke(state)

    tagged_response = result.get('final_response', '')   # [sighs] 등 연기 태그 포함 (TTS용)
    final_response = _strip_tags(tagged_response)        # 화면/DB용
    emotion_label = result.get('emotion_label')          # MBTI 답변 턴이면 None
    is_mbti_answer = bool(result.get('is_mbti_answer'))
    show_consent = bool(result.get('mbti_needs_consent'))

    # MBTI pending 정리 (답변이든 다른 얘기든 해제)
    if session.mbti_pending:
        session.mbti_pending = False
        if show_consent:
            session.mbti_candidate_answer = message      # 동의 시 저장할 답변 보관
        session.save(update_fields=['mbti_pending', 'mbti_candidate_answer'])

    # 저장 — 출력을 막지 않음 (일반: DB+비동기 요약 / 시크릿: RAM 캐시)
    message_id = None
    if session.is_secret:
        secret_cache.append(session.id, 'user', message)
        secret_cache.append(session.id, 'assistant', final_response)
    else:
        ChatMessage.objects.create(session=session, role='user', content=message)
        assistant_msg = ChatMessage.objects.create(
            session=session, role='assistant',
            content=final_response, emotion_label=emotion_label,
        )
        message_id = assistant_msg.id
        memory.update_async(user.id if user else None, session.id)

    # TTS 병렬 생성 (ElevenLabs) — 연기 태그 포함 원문으로 생성, 1회 재생 후 파기
    tts_task_id = tts_service.create_task(
        tagged_response, session.character, emotion_label or 'normal')

    return _ok({
        'session_id': session.id,
        'message_id': message_id,
        'message': {'text': final_response},
        'emotion_label': emotion_label,
        'tts_task_id': tts_task_id,
        'ui': {
            'show_recommendation_button': False,
            'show_plan_result': False,
            'mbti_pending': is_mbti_answer,
            'show_mbti_save_consent': show_consent,
        },
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def tts_status(request, task_id):
    """TTS 폴링 — pending/done/failed. done이면 audio_url에서 1회 다운로드."""
    task = tts_service.get_status(task_id)
    if task is None:
        return _err('TASK_NOT_FOUND', 'TTS 태스크를 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)
    data = {'status': task['status'], 'audio_url': task.get('audio_url')}
    if task['status'] == 'done':
        data['voice_id'] = task.get('voice_id')
    return _ok(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def tts_audio(request, task_id):
    """오디오 1회 반환 후 서버에서 즉시 파기 (다시 듣기 없음 — 저장 안 함 원칙)."""
    from django.http import HttpResponse
    audio = tts_service.consume_audio(task_id)
    if audio is None:
        return _err('AUDIO_GONE', '이미 재생되었거나 존재하지 않는 음성입니다.', status.HTTP_404_NOT_FOUND)
    return HttpResponse(audio, content_type='audio/mpeg')


# ═════════════════════════════════════════════════════════════
# 3. MBTI 서브플로우
# ═════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def mbti_next_question(request):
    """프론트 10초 유휴 타이머 → 호출. 수집 미완료면 질문 반환 + pending 설정."""
    session = _get_session(request.GET.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)

    user = _session_user(request, session)
    nq = mbti_svc.next_question(user)
    if nq is None or session.mbti_pending:
        return _ok({'has_question': False})

    code, text = nq
    session.mbti_pending = True
    session.mbti_last_question_code = code
    session.save(update_fields=['mbti_pending', 'mbti_last_question_code'])

    # MBTI 질문도 대화 이력에 남긴다 (다음 턴 컨텍스트 연결)
    if session.is_secret:
        secret_cache.append(session.id, 'assistant', text)
    else:
        ChatMessage.objects.create(session=session, role='assistant', content=text)

    tts_task_id = tts_service.create_task(text, session.character, 'normal', cacheable=True)
    return _ok({
        'has_question': True,
        'question_code': code,
        'question_text': text,
        'tts_task_id': tts_task_id,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def mbti_consent(request):
    """시크릿 모드 전용 — MBTI 답변 저장 동의/거부."""
    session = _get_session(request.data.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)

    consent = bool(request.data.get('consent', False))
    user = _session_user(request, session)
    saved = False

    if consent and user and session.mbti_candidate_answer:
        MbtiAnswer.objects.create(
            user=user,
            question_code=session.mbti_last_question_code or 'unknown',
            answer_text=session.mbti_candidate_answer,
        )
        saved = True

    session.mbti_candidate_answer = None
    session.save(update_fields=['mbti_candidate_answer'])

    confirm = '고마워요, 살짝 기억해둘게요!' if saved else '알겠어요, 이 얘기는 여기서만 남길게요.'
    tts_task_id = tts_service.create_task(confirm, session.character, 'normal', cacheable=True)
    return _ok({'saved': saved, 'confirm_message': confirm, 'tts_task_id': tts_task_id})


# ═════════════════════════════════════════════════════════════
# 4. 계획도움 / 세션 종료
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def plan_support_view(request):
    """위치 기반 장소 추천 (Tavily + WalkCuration).
    ⚠️ 트리거 조건 미확정 — 현재 프론트 진입점 없음, 확정 시 연결."""
    session = _get_session(request.data.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)

    location = request.data.get('location_context') or {}
    address = location.get('address', '')

    emotion = 'normal'
    if not session.is_secret:
        last = (ChatMessage.objects
                .filter(session=session, role='assistant', emotion_label__isnull=False)
                .order_by('-created_at').first())
        if last:
            emotion = last.emotion_label

    return _ok({'plan_result': plan_support(address, emotion)})


@api_view(['POST'])
@permission_classes([AllowAny])
def session_end(request):
    """세션 종료 — 시크릿 모드 RAM 캐시 + 음성(mp3) 파일 즉시 파기."""
    session = _get_session(request.data.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)
    secret_cache.purge(session.id)
    return _ok({'ended': True})   # 음성은 애초에 저장 안 함 (1회 재생 후 파기)


# ═════════════════════════════════════════════════════════════
# 5. 부가 기능 (추천 질문 / 날씨 / 피드백)
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def suggest_questions(request, session_id):
    """'이런 말 어때요?' 추천 질문 3개 생성."""
    session = _get_session(session_id)
    if session is None:
        return Response({'error': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    recent = list(session.messages.order_by('-created_at')[:6])
    recent.reverse()
    context = '\n'.join(f"{'사용자' if m.role == 'user' else '캐릭터'}: {m.content}" for m in recent)

    system = (
        "당신은 공감 대화 전문가입니다. 대화 흐름을 읽고 사용자가 다음에 할 수 있는 말 3가지를 추천해주세요.\n"
        "짧고 자연스러운 구어체로, 반드시 아래 JSON 형식으로만 응답하세요:\n"
        '{"questions": ["질문1", "질문2", "질문3"]}'
    )

    try:
        resp = _client().chat.completions.create(
            model=_model(),
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': f'대화:\n{context}'},
            ],
            max_tokens=150,
            temperature=0.9,
        )
        raw = resp.choices[0].message.content.strip()
        start, end = raw.find('{'), raw.rfind('}') + 1
        result = json.loads(raw[start:end])
    except Exception:
        result = {'questions': ['오늘 하루 어땠어?', '요즘 제일 힘든 게 뭐야?', '그냥 수다 떨까?']}

    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def weather_opener(request):
    """대화방 상단 날씨 한줄 배너 (Open-Meteo)."""
    lat = request.GET.get('lat', '37.5665')
    lon = request.GET.get('lon', '126.9780')

    weather_type = 'clear'
    temp_c = 20
    weather_desc = '맑음'

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get('current_weather', {})
            temp_c = round(current.get('temperature', 20))
            wcode = current.get('weathercode', 0)

            if wcode == 0:
                weather_type, weather_desc = 'clear', '맑음'
            elif wcode in (1, 2, 3, 45, 48):
                weather_type, weather_desc = 'clouds', '흐림'
            elif wcode in (51, 53, 55, 61, 63, 65, 80, 81, 82):
                weather_type, weather_desc = 'rain', '비'
            elif wcode in (71, 73, 75, 77, 85, 86):
                weather_type, weather_desc = 'snow', '눈'
            elif wcode in (95, 96, 99):
                weather_type, weather_desc = 'thunderstorm', '뇌우'
    except Exception:
        pass

    opener = f"오늘 날씨는 {weather_desc}이고 기온은 {temp_c}도네. 편안한 마음으로 대화를 시작해볼까?"
    return Response({
        'opener': opener,
        'weather_type': weather_type,
        'weather_desc': weather_desc,
        'temp_c': temp_c,
    })


# (👍👎 피드백/MLOps 재학습 큐는 2차 확장으로 제거 — 2026-07-02)

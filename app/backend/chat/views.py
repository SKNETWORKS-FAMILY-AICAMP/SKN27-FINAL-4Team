# -*- coding: utf-8 -*-
"""챗봇 API — 단일 파일 (v6.0, API_명세서_김한솔.md 기준).

■ 메인 플로우 (LangGraph)
  session_start   POST /api/session/start/        세션 시작 (친구 첫인사)
  chat_turn       POST /api/chat/                 대화 턴 (텍스트 즉시 + tts_task_id)
  tts_status      GET  /api/tts/<task_id>/        TTS 오디오 폴링
  mbti_next_question GET /api/mbti/next-question/ MBTI 질문 (10초 유휴 · 일반 모드 전용)
  session_end     POST /api/session/end/          세션 종료 (시크릿 캐시 파기)

지원 모듈: graph/(LangGraph), tts_service, mbti, memory, secret_cache
"""
import re

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ai.agents import mbti as mbti_svc
from . import memory, secret_cache, tts_service
from .models import ChatMessage, ChatSession


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

VALID_CHARACTERS = {'pori', 'kkami', 'toto', 'yeoul'}


# ── 공통 헬퍼 ────────────────────────────────────────────────

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
# 1. 세션 시작 (친구 첫인사)
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def session_start(request):
    """세션 시작 — 친구 컨셉: 감정 안 묻고 날씨·시간·닉네임으로 먼저 말 건다.

    (구 콜드스타트 감정 선택지는 폐지. cold_start_done은 항상 True로 시작.)"""
    character = request.data.get('character_id', 'pori')
    is_secret = bool(request.data.get('is_secret', False))
    if character not in VALID_CHARACTERS:
        return _err('INVALID_CHARACTER', '유효하지 않은 캐릭터입니다.')

    user = request.user if request.user.is_authenticated else None
    # 감정 선택 단계가 없어졌으므로 콜드스타트는 바로 완료 상태로 시작
    session = ChatSession.objects.create(
        user=user, character=character, is_secret=is_secret, cold_start_done=True)

    # 친구 첫인사 생성 (날씨 좌표는 프론트가 선택적으로 전달)
    nickname = getattr(user, 'nickname', None) if user else None
    lat = request.data.get('lat')
    lon = request.data.get('lon')
    from .opener_service import generate_opener
    # 기억 기반 첫인사는 일반 모드 전용 (시크릿에서 지난 대화 언급 금지)
    memory_uid = user.id if (user and not is_secret) else None
    opener = generate_opener(nickname, lat, lon, user_id=memory_uid)

    # 첫인사도 대화 이력에 남긴다 (다음 턴 컨텍스트 연결)
    if is_secret:
        secret_cache.append(session.id, 'assistant', opener)
    else:
        ChatMessage.objects.create(session=session, role='assistant', content=opener)

    tts_task_id = tts_service.create_task(opener, character, 'normal')

    return _ok({
        'session_id': session.id,
        'cold_start_done': True,
        'opener': opener,
        'tts_task_id': tts_task_id,
    }, status.HTTP_201_CREATED)


# ═════════════════════════════════════════════════════════════
# 2. 대화 턴 (LangGraph) + TTS 폴링
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
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

    # 직전 턴 감정 — 초단문 바이패스·저확신 폴백용 (일반 모드만, 시크릿은 감정 미저장)
    prev_emotion = None
    if not session.is_secret:
        prev_emotion = (
            ChatMessage.objects
            .filter(session=session, role='assistant', emotion_label__isnull=False)
            .order_by('-created_at')
            .values_list('emotion_label', flat=True)
            .first()
        )

    # LangGraph 실행: MBTI pending 체크 → 컨텍스트 → 감성분석(확신도 게이트) → 에이전트 → 응답
    from .graph.graph import get_graph
    state = {
        'user_id': user.id if user else None,
        'session_id': session.id,
        'session_mode': session_mode,
        'character_id': session.character,
        'user_message': message,
        'selected_emotion': session.selected_emotion,
        'prev_emotion': prev_emotion,
        'mbti_pending': session.mbti_pending,
        'mbti_question_text': mbti_svc.question_text(session.mbti_last_question_code or ''),
        'mbti_question_code': session.mbti_last_question_code or '',
    }
    result = get_graph().invoke(state)

    tagged_response = result.get('final_response', '')   # [sighs] 등 연기 태그 포함 (TTS용)
    final_response = _strip_tags(tagged_response)        # 화면/DB용
    emotion_label = result.get('emotion_label')          # MBTI 답변 턴이면 None
    is_mbti_answer = bool(result.get('is_mbti_answer'))

    # MBTI pending 정리 (답변이든 다른 얘기든 해제)
    if session.mbti_pending:
        session.mbti_pending = False
        session.save(update_fields=['mbti_pending'])

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
        uid = user.id if user else None
        memory.capture_async(uid, message)        # 중요 정보 즉시 저장
        memory.update_async(uid, session.id)      # 8턴 경계 압축·정리

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
            'mbti_pending': is_mbti_answer,
        },
    })


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
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
@authentication_classes([CsrfExemptSessionAuthentication])
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
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def mbti_next_question(request):
    """프론트 10초 유휴 타이머 → 호출. 수집 미완료면 질문 반환 + pending 설정.
    시크릿 모드는 완전 무저장 원칙 — 답을 저장할 수 없으니 질문 자체를 안 한다."""
    session = _get_session(request.GET.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)
    if session.is_secret:
        return _ok({'has_question': False})

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


# (시크릿 모드 MBTI 저장 동의 플로우는 "시크릿 = 완전 무저장" 원칙으로 제거 — 2026-07-03.
#  시크릿에서는 MBTI 질문 자체를 하지 않는다.)


# ═════════════════════════════════════════════════════════════
# 4. 세션 종료
# ═════════════════════════════════════════════════════════════

@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def session_end(request):
    """세션 종료 — 시크릿: RAM 캐시 파기 / 일반: 8턴 못 채운 잔여 대화 요약 반영."""
    session = _get_session(request.data.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)
    secret_cache.purge(session.id)
    if not session.is_secret and session.user_id:
        memory.update_async(session.user_id, session.id, force=True)
    return _ok({'ended': True})   # 음성은 애초에 저장 안 함 (1회 재생 후 파기)


# (👍👎 피드백/MLOps 재학습 큐는 2차 확장으로 제거 — 2026-07-02)
# (구 콜드스타트 감정 선택 · 날씨 배너 API는 친구 컨셉 개편으로 제거 — 2026-07-03)
# (추천 질문 '이런 말 어때요' API는 기능 폐기로 제거 — 2026-07-03)
# (계획도움 /api/plan-support/ · WalkCuration은 장소 추천 기능 폐기로 제거 — 2026-07-05)

# -*- coding: utf-8 -*-
"""챗봇 API — 단일 파일 (v6.0, API_명세서_김한솔.md 기준).

■ 메인 플로우 (LangGraph)
  session_start   POST /api/session/start/        세션 시작 (친구 첫인사)
  chat_turn       POST /api/chat/                 대화 턴 (텍스트 즉시 + tts_task_id)
  tts_status      GET  /api/tts/<task_id>/        TTS 오디오 폴링
  mbti_next_question GET /api/mbti/next-question/ (레거시·미사용) — MBTI 질문은 chat_turn 응답에 삽입
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
from . import graph_memory, memory, secret_cache, tts_service
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
    image_data_url = (request.data.get('image') or '').strip()   # 사진 첨부(data URL) · 저장 안 함
    if not message and not image_data_url:
        return _err('EMPTY_MESSAGE', '메시지 내용을 입력해주세요.')
    if len(message) > 300:
        return _err('MESSAGE_TOO_LONG', '메시지는 300자 이내여야 합니다.')
    if image_data_url:
        if not image_data_url.startswith('data:image/'):
            return _err('INVALID_IMAGE', '이미지 형식이 올바르지 않습니다.')
        if len(image_data_url) > 5_000_000:   # base64 ~3.7MB 초과 차단
            return _err('IMAGE_TOO_LARGE', '이미지가 너무 큽니다. 더 작게 보내주세요.')

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

    # MBTI 질문은 대화 맥락으로 즉석 생성되므로, 판별엔 '실제로 물어본 문장'
    # (직전 assistant 메시지)을 쓴다. 없으면 고정 template로 폴백.
    mbti_q_text = ''
    if session.mbti_pending and not session.is_secret:
        mbti_q_text = (
            ChatMessage.objects
            .filter(session=session, role='assistant')
            .order_by('-created_at')
            .values_list('content', flat=True)
            .first()
        ) or ''
    if not mbti_q_text:
        mbti_q_text = mbti_svc.question_text(session.mbti_last_question_code or '')

    # LangGraph 실행: MBTI pending 체크 → 컨텍스트 → 감성분석(확신도 게이트) → 에이전트 → 응답
    from .graph.graph import get_graph
    state = {
        'user_id': user.id if user else None,
        'session_id': session.id,
        'session_mode': session_mode,
        'character_id': session.character,
        'user_message': message,
        'image_data_url': image_data_url or None,   # 멀티모달(사진) · 저장은 안 함
        'selected_emotion': session.selected_emotion,
        'prev_emotion': prev_emotion,
        'mbti_pending': session.mbti_pending,
        'mbti_question_text': mbti_q_text,
        'mbti_question_code': session.mbti_last_question_code or '',
    }
    result = get_graph().invoke(state)

    tagged_response = result.get('final_response', '')   # [sighs] 등 연기 태그 포함 (TTS용)
    final_response = _strip_tags(tagged_response)        # 화면/DB용
    emotion_label = result.get('emotion_label')          # MBTI 답변 턴이면 None
    is_mbti_answer = bool(result.get('is_mbti_answer'))
    image_caption = (result.get('image_caption') or '').strip()   # 사진 캡션 (저장·리포트·기억용)

    # ── MBTI 질문을 대화 흐름에 자연스럽게 엮기 (유휴 타이머 대신) ──
    #  트리거가 '침묵(초)'이 아니라 '방금 사용자가 한 말'이 되도록 이 턴 안에서 판단.
    #  조건: 로그인 · 일반모드 · 이번 턴이 MBTI 답변 턴이 아님 · 감정이 안 무거움(joy/normal)
    #       · 워밍업(사용자 3턴↑) · 4턴마다 1번 · 수집 미완료.
    #  통과하면 봇 응답 끝에 질문 한 문장을 '같은 말풍선'으로 얹는다.
    probe_code = None
    if (user and not session.is_secret and not session.mbti_pending
            and emotion_label in ('joy', 'normal')):
        user_turn_no = ChatMessage.objects.filter(session=session, role='user').count() + 1
        if user_turn_no >= 3 and user_turn_no % 4 == 0 and not mbti_svc.is_complete(user):
            _recent = list(ChatMessage.objects.filter(session=session).order_by('-created_at')[:6])
            _recent.reverse()
            _history = [{'role': m.role, 'content': m.content} for m in _recent]
            _probe = mbti_svc.generate_question(user, _history)
            if _probe:
                probe_code, _probe_text = _probe
                final_response = f'{final_response}\n\n{_probe_text}'
                tagged_response = f'{tagged_response}\n\n{_probe_text}'

    # MBTI pending 정리 (답변이든 다른 얘기든 해제)
    if session.mbti_pending:
        session.mbti_pending = False
        session.save(update_fields=['mbti_pending'])

    # 저장 — 출력을 막지 않음 (일반: DB+비동기 요약 / 시크릿: RAM 캐시)
    message_id = None
    # 저장 텍스트: 사진은 원본 대신 캡션(설명)으로 남긴다 → 마음리포트·기억이 사진 맥락을 반영
    if image_caption:
        stored_user_msg = f'{message} (사진: {image_caption})'.strip()
    elif image_data_url:
        stored_user_msg = message or '[사진]'
    else:
        stored_user_msg = message
    if session.is_secret:
        secret_cache.append(session.id, 'user', stored_user_msg)
        secret_cache.append(session.id, 'assistant', final_response)
    else:
        ChatMessage.objects.create(session=session, role='user', content=stored_user_msg)
        assistant_msg = ChatMessage.objects.create(
            session=session, role='assistant',
            content=final_response, emotion_label=emotion_label,
        )
        message_id = assistant_msg.id
        uid = user.id if user else None
        memory.capture_async(uid, stored_user_msg)   # 중요 정보 즉시 저장 (사진 캡션 포함)
        graph_memory.capture_async(uid, stored_user_msg)  # 구조화 기억(그래프) 병행 — Neo4j 미설정 시 no-op
        memory.update_async(uid, session.id)      # 8턴 경계 압축·정리

        # 응답에 MBTI 질문을 얹었으면, 다음 사용자 메시지를 그 답변으로 받도록 pending 설정
        if probe_code:
            session.mbti_pending = True
            session.mbti_last_question_code = probe_code
            session.save(update_fields=['mbti_pending', 'mbti_last_question_code'])

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
        data['alignment'] = task.get('alignment')   # 글자별 타임스탬프 (자막 동기용, 없으면 null)
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
    """(레거시) 구 10초 유휴 타이머용 엔드포인트 — 현재 프론트는 호출하지 않음.
    MBTI 질문은 chat_turn 응답에 대화 흐름으로 얹는다(2026-07-08). 코드는 하위호환용 유지.
    수집 미완료면 질문 반환 + pending 설정. 시크릿 모드는 완전 무저장 원칙으로 질문 안 함."""
    session = _get_session(request.GET.get('session_id'))
    if session is None:
        return _err('SESSION_NOT_FOUND', '세션을 찾을 수 없습니다.', status.HTTP_404_NOT_FOUND)
    if session.is_secret:
        return _ok({'has_question': False})

    if session.mbti_pending:
        return _ok({'has_question': False})

    user = _session_user(request, session)

    # 방금까지의 대화 맥락 → 자연스러운 질문 생성 재료
    recent = list(
        ChatMessage.objects.filter(session=session).order_by('-created_at')[:6]
    )
    recent.reverse()
    history = [{'role': m.role, 'content': m.content} for m in recent]

    nq = mbti_svc.generate_question(user, history)
    if nq is None:
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


# (복합 감정 임계값 보정용 임시 /api/emotion/probe/ 는 실측 완료 후 제거 — 2026-07-10.
#  재보정 필요 시 predict_emotion_full을 임시 뷰로 노출해 절 분할 실측 재현 가능)

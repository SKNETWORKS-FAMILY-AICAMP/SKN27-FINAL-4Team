# -*- coding: utf-8 -*-
"""user_memory 장기 요약 갱신 — 비동기 백그라운드 (최종_통합_흐름도 §4).

일반 모드 턴 종료 후 스레드로 실행되어 출력 응답을 지연시키지 않는다.
어시스턴트 응답 누적 SUMMARY_EVERY턴마다 LLM으로 기존 요약 + 최근 대화를 압축 갱신.
"""
import os
import threading

SUMMARY_EVERY = 8
MAX_SUMMARY_CHARS = 800


def _update(user_id: int, session_id: int) -> None:
    try:
        from chat.models import ChatMessage, UserMemory

        count = ChatMessage.objects.filter(
            session_id=session_id, role='assistant').count()
        if count == 0 or count % SUMMARY_EVERY != 0:
            return

        recent = list(
            ChatMessage.objects.filter(session_id=session_id)
            .order_by('-created_at')[:SUMMARY_EVERY * 2]
        )
        recent.reverse()
        convo = '\n'.join(
            f"{'사용자' if m.role == 'user' else '챗봇'}: {m.content}" for m in recent
        )

        memory, _ = UserMemory.objects.get_or_create(user_id=user_id)

        from ai.agents.llm import get_llm
        llm = get_llm(temperature=0.3, max_tokens=400)
        resp = llm.invoke([
            ('system',
             '당신은 대화 기록을 압축하는 요약가입니다. 기존 요약과 최근 대화를 합쳐 '
             f'사용자에 대한 장기 기억 요약을 {MAX_SUMMARY_CHARS}자 이내로 갱신하세요. '
             '사용자의 상황·감정 패턴·중요한 사건 중심으로, 3인칭 서술로 작성합니다.'),
            ('user', f'[기존 요약]\n{memory.summary_text or "(없음)"}\n\n[최근 대화]\n{convo}'),
        ])
        memory.summary_text = resp.content.strip()[:MAX_SUMMARY_CHARS]
        memory.save(update_fields=['summary_text', 'updated_at'])
    except Exception as e:
        print(f'[memory] user_memory 갱신 실패: {e}')


def update_async(user_id: int | None, session_id: int) -> None:
    """비동기 갱신 트리거. 비로그인 사용자는 스킵."""
    if not user_id:
        return
    threading.Thread(target=_update, args=(user_id, session_id), daemon=True).start()

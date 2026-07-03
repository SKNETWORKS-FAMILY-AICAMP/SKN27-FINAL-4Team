# -*- coding: utf-8 -*-
"""user_memory 장기 기억 — 비동기 백그라운드 (최종_통합_흐름도 §4).

2단 구조 (중요도 기반 즉시 저장 + 주기 정리):
① capture_async — 매 턴, 사용자 메시지에 기억할 가치가 있으면 '그 즉시' 한 줄 저장.
   (세션이 어떻게 끝나든 중요한 얘기는 이미 저장돼 있음)
② update_async — 8턴마다 / 세션 종료 시, 쌓인 기억을 압축·중복 제거·상태 갱신.
모두 스레드로 실행되어 출력 응답을 지연시키지 않는다.
"""
import datetime
import os
import threading

SUMMARY_EVERY = 8
MAX_SUMMARY_CHARS = 800


def _today_kst() -> str:
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d (%a)')


# ── ① 중요도 기반 즉시 캡처 ─────────────────────────────────

def _capture(user_id: int, message: str) -> None:
    try:
        from ai.agents.llm import get_llm
        resp = get_llm(temperature=0, max_tokens=60).invoke([
            ('system',
             "너는 친한 친구의 '기억'을 담당한다. 사용자의 메시지에 나중에 다시 물어볼 가치가 있는 정보"
             "(예정된 일, 중요한 사건·고민, 인물, 취향·좋아하는 것)가 있으면 한 줄(50자 이내)로 추출하라.\n"
             f"- 날짜 표현(내일, 다음주 화요일 등)은 오늘 {_today_kst()} 기준 실제 날짜로 변환.\n"
             "- 날씨·그날의 메뉴 같은 일회성 스몰토크, 단순 감탄·맞장구면 NONE 만 출력."),
            ('user', message),
        ])
        fact = resp.content.strip()
        if not fact or fact.upper().startswith('NONE') or len(fact) < 4:
            return

        from chat.models import UserMemory
        memory, _ = UserMemory.objects.get_or_create(user_id=user_id)
        line = f'- {fact}'
        if line in (memory.summary_text or ''):
            return
        memory.summary_text = ((memory.summary_text or '').rstrip() + '\n' + line).strip()
        memory.save(update_fields=['summary_text', 'updated_at'])

        # 한도 초과 시 즉시 압축 (오래된 것부터 밀려나지 않게 LLM 정리)
        if len(memory.summary_text) > MAX_SUMMARY_CHARS:
            _consolidate(memory)
    except Exception as e:
        print(f'[memory] 즉시 캡처 실패: {e}')


def _consolidate(memory) -> None:
    """기억이 한도를 넘으면 압축·중복 제거 (저장이 아니라 정리)."""
    from ai.agents.llm import get_llm
    resp = get_llm(temperature=0.3, max_tokens=400).invoke([
        ('system',
         f'다음 장기 기억을 {MAX_SUMMARY_CHARS}자 이내로 정리하라. 정보를 새로 만들지 말 것.\n'
         '- 중복 병합, 끝난 일은 결과만 남기고 압축, 지난 날짜의 일정은 결과 중심으로 축약.\n'
         f'- 오늘은 {_today_kst()}. 예정된 일·진행 중인 사건·반복 고민·인물·취향은 유지.'),
        ('user', memory.summary_text),
    ])
    text = resp.content.strip()
    if text:
        memory.summary_text = text[:MAX_SUMMARY_CHARS]
        memory.save(update_fields=['summary_text', 'updated_at'])


def capture_async(user_id: int | None, message: str) -> None:
    """중요 정보 즉시 저장 트리거. 비로그인 사용자는 스킵."""
    if not user_id or not (message or '').strip():
        return
    threading.Thread(target=_capture, args=(user_id, message), daemon=True).start()


# ── ② 주기 정리 (8턴 경계 / 세션 종료) ───────────────────────


def _update(user_id: int, session_id: int, force: bool = False) -> None:
    """force=False: 턴 종료 후 — SUMMARY_EVERY턴마다 갱신.
    force=True: 세션 종료 시 — 8턴 못 채운 잔여 대화도 요약에 반영."""
    try:
        from chat.models import ChatMessage, UserMemory

        count = ChatMessage.objects.filter(
            session_id=session_id, role='assistant').count()
        if count == 0:
            return
        if force:
            # 방금 8턴 경계에서 이미 요약됐으면 중복 방지 (opener 1개뿐이어도 스킵)
            if count % SUMMARY_EVERY == 0 or count <= 1:
                return
        elif count % SUMMARY_EVERY != 0:
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

        import datetime
        today = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9)))
        today_str = today.strftime('%Y-%m-%d (%a)')

        from ai.agents.llm import get_llm
        llm = get_llm(temperature=0.3, max_tokens=400)
        resp = llm.invoke([
            ('system',
             '너는 사용자의 진짜 친한 친구의 "기억"을 관리한다. 기존 요약과 최근 대화를 합쳐 '
             f'장기 기억을 {MAX_SUMMARY_CHARS}자 이내로 갱신하라. 3인칭 서술.\n'
             '[꼭 기억할 것 — 우선순위 순]\n'
             '1. 예정된 일: 면접·시험·발표·약속 — 상대 표현(다음주 화요일)은 오늘 날짜 기준 실제 날짜로 변환해 기록 '
             '(다음 만남에서 안부를 물을 재료)\n'
             '2. 진행 중인 사건: 이직·연애·갈등·건강 — 최신 상태 위주로 갱신, 끝난 일은 결과만 남기고 압축\n'
             '3. 반복되는 고민·감정 패턴: 자주 언급되는 주제라는 것이 드러나게\n'
             '4. 취향과 사람: 좋아하는 것, 자주 등장하는 인물(사용자가 부르는 호칭 그대로)\n'
             '[버릴 것] 일회성 스몰토크(날씨, 그날의 메뉴 등), 챗봇이 한 말'),
            ('user',
             f'[오늘 날짜] {today_str}\n\n[기존 요약]\n{memory.summary_text or "(없음)"}'
             f'\n\n[최근 대화]\n{convo}'),
        ])
        memory.summary_text = resp.content.strip()[:MAX_SUMMARY_CHARS]
        memory.save(update_fields=['summary_text', 'updated_at'])
    except Exception as e:
        print(f'[memory] user_memory 갱신 실패: {e}')


def update_async(user_id: int | None, session_id: int, force: bool = False) -> None:
    """비동기 갱신 트리거. 비로그인 사용자는 스킵.
    force=True는 세션 종료 시 호출 — 잔여 대화 요약."""
    if not user_id:
        return
    threading.Thread(
        target=_update, args=(user_id, session_id, force), daemon=True).start()

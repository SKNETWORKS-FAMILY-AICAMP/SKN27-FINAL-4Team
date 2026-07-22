# -*- coding: utf-8 -*-
"""MBTI 서브플로우 — 유도 질문 목록 및 진행 상태 (최종_통합_흐름도 §5).

- 트리거: 대화 턴(chat_turn) 응답 끝에 자연스럽게 얹음 — 게이트(일반 모드·감정 안 무거움·사용자 3턴↑·4턴마다·수집 미완료). generate_question가 최근 대화 반영해 반말로 생성. (구 10초 유휴 타이머 방식 폐지, 2026-07-08)
- 저장: 일반 모드 즉시 (시크릿 모드는 MBTI 질문 자체 안 함)
- 4개 축(I/E, S/N, T/F, J/P) × 5문항 = 총 20문항. 각 축 최소 5답이면 수집 완료로 간주.
- NOTE: 축 코드는 mbti 파이프라인(MbtiQuestionResponse.target_axis)과 동일하게 IE/SN/TF/JP 사용.
"""

# (question_code, 스몰토크형 유도 질문)
QUESTIONS = [
    # ── IE 축 (내향 / 외향) ──────────────────────────────────
    ('IE_1', '그러고 보니 궁금한 거 있는데, 넌 주말에 사람들 만나면 힘이 나? 아니면 혼자 쉬어야 충전돼?'),
    ('IE_2', '새로운 모임 가면 네가 먼저 말 거는 편이야, 아니면 누가 말 걸어주길 기다리는 편이야?'),
    ('IE_3', '힘든 하루 보냈을 때 친구한테 연락하고 싶어, 아니면 혼자 조용히 있고 싶어?'),
    ('IE_4', '파티나 모임 갔다 오면 다음 날 개운해, 아니면 좀 피곤해?'),
    ('IE_5', '혼자서 조용히 시간 보낼 때 어떤 기분이 들어?'),
    # ── SN 축 (감각 / 직관) ──────────────────────────────────
    ('SN_1', '여행 갈 때 코스 딱 짜놓는 게 좋아, 아니면 가서 느낌대로 다니는 게 좋아?'),
    ('SN_2', '누구 얘기 들을 때 실제로 뭔 일 있었는지가 궁금해, 아니면 그 뒤에 숨은 의미가 더 궁금해?'),
    ('SN_3', '새 물건 살 때 스펙이나 기능을 꼼꼼히 따져, 아니면 느낌이나 디자인으로 고르는 편이야?'),
    ('SN_4', '대화할 때 구체적인 사실을 주고받는 게 편해, 아니면 아이디어나 가능성 얘기가 더 재밌어?'),
    ('SN_5', '뭔가 배울 때 단계별로 차근차근 익히는 게 좋아, 아니면 큰 그림부터 파악하는 게 좋아?'),
    # ── TF 축 (사고 / 감정) ──────────────────────────────────
    ('TF_1', '친구가 고민 털어놓으면 넌 해결책부터 떠올라, 아니면 걔 마음이 어땠을지가 먼저 떠올라?'),
    ('TF_2', '뭔가 정할 때 논리적으로 맞는지가 중요해, 아니면 사람들 기분 안 상하는 게 중요해?'),
    ('TF_3', '누군가 틀린 말 하면 바로 지적하는 편이야, 아니면 굳이 말 안 하고 넘어가는 편이야?'),
    ('TF_4', '칭찬받을 때 능력 인정받는 게 기분 좋아, 아니면 마음을 알아준다는 느낌이 더 좋아?'),
    ('TF_5', '토론할 때 논리가 중요해, 아니면 서로 감정 안 상하는 게 더 중요해?'),
    # ── JP 축 (판단 / 인식) ──────────────────────────────────
    ('JP_1', '할 일 생기면 미리미리 끝내야 맘 편해, 아니면 마감 닥쳐야 시동 걸려?'),
    ('JP_2', '계획 갑자기 바뀌면 스트레스야, 아니면 오히려 그게 더 재밌어?'),
    ('JP_3', '여행 짐은 미리 다 싸놓는 편이야, 아니면 출발 직전에 대충 넣는 편이야?'),
    ('JP_4', '오늘 할 일 목록 만들어두는 편이야, 아니면 그냥 생각나는 대로 하는 편이야?'),
    ('JP_5', '약속 시간에 여유 있게 일찍 도착하는 편이야, 아니면 딱 맞춰서 오는 편이야?'),
]

_CODE2TEXT = dict(QUESTIONS)
AXES = ('IE', 'SN', 'TF', 'JP')

# 각 문항이 '알아보려는 성향' (LLM이 자연스러운 질문을 만들 때 참고)
_AXIS_INTENT = {
    'IE_1': '사람들과 어울릴 때 힘이 나는지, 아니면 혼자 있어야 충전되는지 (에너지 방향)',
    'IE_2': '새로운 자리에서 먼저 다가가는지, 아니면 누가 다가와주길 기다리는지',
    'IE_3': '힘든 날 사람을 찾는지, 아니면 혼자만의 시간을 원하는지',
    'IE_4': '모임 후 에너지가 충전되는지, 아니면 소진되는지',
    'IE_5': '혼자 있는 시간이 편안한지, 아니면 심심하고 어색한지',
    'SN_1': '뭔가 할 때 구체적으로 계획을 짜는지, 아니면 느낌대로 즉흥으로 하는지',
    'SN_2': '실제로 있었던 사실이 궁금한지, 아니면 그 뒤에 숨은 의미가 궁금한지',
    'SN_3': '선택할 때 구체적 스펙·수치가 중요한지, 아니면 직관적 느낌이 중요한지',
    'SN_4': '대화에서 사실·정보 교환이 편한지, 아니면 아이디어·가능성 탐색이 더 즐거운지',
    'SN_5': '배울 때 순서대로 익히는 걸 선호하는지, 아니면 개요·맥락부터 파악하는 걸 선호하는지',
    'TF_1': '친구 고민에 해결책이 먼저 떠오르는지, 아니면 마음 공감이 먼저인지',
    'TF_2': '결정할 때 논리·원칙이 기준인지, 아니면 사람들 기분·분위기가 기준인지',
    'TF_3': '틀린 것을 발견하면 바로 말하는지, 아니면 관계를 고려해 참는지',
    'TF_4': '능력·성과를 인정받을 때 더 기쁜지, 아니면 감정·마음을 알아줄 때 더 기쁜지',
    'TF_5': '토론에서 논리적 결론이 중요한지, 아니면 관계 유지가 더 중요한지',
    'JP_1': '할 일을 미리 끝내야 마음 편한지, 아니면 마감이 닥쳐야 시동 걸리는지',
    'JP_2': '계획이 갑자기 바뀌면 스트레스인지, 아니면 오히려 재밌는지',
    'JP_3': '준비를 미리 철저히 하는지, 아니면 직전에 몰아서 하는지',
    'JP_4': '할 일 목록을 만들어야 마음이 편한지, 아니면 즉흥적으로 움직이는 게 편한지',
    'JP_5': '시간 약속에 여유 있게 도착하는지, 아니면 딱 맞춰서 오는 편인지',
}

# 파이프라인 조건과 동일하게 축당 최소 5개 답변이 있어야 수집 완료
MIN_PER_AXIS = 5


def question_text(code):
    """질문 코드 → 질문 문장 (없으면 빈 문자열)."""
    return _CODE2TEXT.get(code, '')


def _answered_codes(user):
    from chat.models import MbtiAnswer
    return set(
        MbtiAnswer.objects.filter(user=user).values_list('question_code', flat=True)
    )


def is_complete(user):
    """각 축에 최소 MIN_PER_AXIS(5)개 답변이 있으면 수집 완료. 비로그인은 수집 대상 아님."""
    if user is None:
        return True
    answered = _answered_codes(user)
    return all(
        sum(1 for c in answered if c.startswith(axis)) >= MIN_PER_AXIS
        for axis in AXES
    )


import random

def _next_code(user):
    """다음에 물어볼 미답변 문항 코드. 완료/비로그인 시 None.

    2026-07-22: 챗봇은 MBTI를 '드물게' 물어보는 보조 채널이라, 물어보는 횟수 자체가 적다.
      그래서 아무 축이나 뽑으면(random) 특정 축에 쏠려 리포트가 한쪽만 채워질 수 있다.
      → '지금까지 답변이 가장 적은 축'의 미답변 문항부터 고른다. 적게 물어도 4축이 고르게
        채워지도록. (완성 책임은 마이페이지 mock-qna에 있으므로 여기선 균형만 챙긴다)
    """
    if user is None or is_complete(user):
        return None
    answered = _answered_codes(user)
    unanswered = [code for code, _ in QUESTIONS if code not in answered]
    if not unanswered:
        return None
    # 축별 답변 수 → 가장 적은 축 우선 (동률이면 축 순서 IE→SN→TF→JP)
    answered_per_axis = {
        axis: sum(1 for c in answered if c.startswith(axis)) for axis in AXES
    }
    unanswered_axes = {code[:2] for code in unanswered}
    target_axis = min(
        (a for a in AXES if a in unanswered_axes),
        key=lambda a: (answered_per_axis[a], AXES.index(a)),
    )
    axis_pool = [code for code in unanswered if code.startswith(target_axis)]
    return random.choice(axis_pool)   # 같은 축 안에서만 랜덤 (문항 순서 편향 방지)


def generate_question(user, recent_history=None):
    """다음 미답변 축을 '방금 대화에 자연스럽게 엮은 반말 질문'으로 생성.
    설문이 아니라 친구가 문득 궁금해하듯. LLM 실패 시 고정 template로 폴백.
    반환: (code, text) / 완료·비로그인 시 None."""
    code = _next_code(user)
    if code is None:
        return None
    fallback = _CODE2TEXT.get(code, '')
    intent = _AXIS_INTENT.get(code, '')
    try:
        import os
        from ai.agents.llm import get_llm
        convo = '\n'.join(
            f"{'사용자' if m.get('role') == 'user' else '나'}: {m.get('content', '')}"
            for m in (recent_history or [])[-6:]
        )
        # 추론형 모델은 짧은 질문을 출력하기 전 reasoning 토큰을 사용하므로
        # 80토큰에서는 content가 비어 정적 문항으로만 폴백할 수 있다.
        max_tokens = int(os.environ.get('MBTI_CHAT_QUESTION_MAX_TOKENS', '320'))
        resp = get_llm(temperature=0.8, max_tokens=max_tokens).invoke([
            ('system',
             "너는 사용자의 진짜 친한 친구다. 방금 나눈 대화에 자연스럽게 이어서, "
             "아래 [알아볼 성향]을 슬쩍 떠보는 질문 '하나만' 만들어라.\n"
             "- 심리테스트·설문처럼 딱딱하게 묻지 마. 방금 얘기 흐름에 엮어서, 친구가 문득 궁금해하듯.\n"
             "- 두 갈래 중 뭐냐고 가볍게 고르게 해도 좋아. 반드시 반말, 1~2문장, 오직 순수 한국어.\n"
             "- 물음표로 끝내. 목록/이모지/존댓말 금지."),
            ('user', f"[최근 대화]\n{convo or '(방금 시작됨)'}\n\n[알아볼 성향]\n{intent}"),
        ])
        text = resp.content.strip()
        # 존댓말 어미 검출
        formal_endings = ['요?', '까요?', '나요?', '습니까?', '니다?', '에요?', '이에요?']
        has_formal = any(end in text for end in formal_endings)
        
        if not (8 <= len(text) <= 120) or '?' not in text or has_formal:
            text = fallback
    except Exception:
        text = fallback
    return (code, text) if text else None

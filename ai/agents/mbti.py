# -*- coding: utf-8 -*-
"""MBTI 서브플로우 — 유도 질문 목록 및 진행 상태 (최종_통합_흐름도 §5).

- 트리거: 턴 종료 후 10초 무입력(프론트 타이머) + 수집 미완료 → GET /api/mbti/next-question/
- 저장: 일반 모드 즉시 / 시크릿 모드 동의 시 (POST /api/mbti/consent/)
- 4개 축(E/I, S/N, T/F, J/P) × 2문항 = 총 8문항. 각 축 최소 1답이면 수집 완료로 간주.
"""

# (question_code, 스몰토크형 유도 질문)
QUESTIONS = [
    ('EI_1', '그러고 보니 궁금한 거 있는데, 넌 주말에 사람들 만나면 힘이 나? 아니면 혼자 쉬어야 충전돼?'),
    ('EI_2', '새로운 모임 가면 네가 먼저 말 거는 편이야, 아니면 누가 말 걸어주길 기다리는 편이야?'),
    ('SN_1', '여행 갈 때 코스 딱 짜놓는 게 좋아, 아니면 가서 느낌대로 다니는 게 좋아?'),
    ('SN_2', '누구 얘기 들을 때 실제로 뭔 일 있었는지가 궁금해, 아니면 그 뒤에 숨은 의미가 더 궁금해?'),
    ('TF_1', '친구가 고민 털어놓으면 넌 해결책부터 떠올라, 아니면 걔 마음이 어땠을지가 먼저 떠올라?'),
    ('TF_2', '뭔가 정할 때 논리적으로 맞는지가 중요해, 아니면 사람들 기분 안 상하는 게 중요해?'),
    ('JP_1', '할 일 생기면 미리미리 끝내야 맘 편해, 아니면 마감 닥쳐야 시동 걸려?'),
    ('JP_2', '계획 갑자기 바뀌면 스트레스야, 아니면 오히려 그게 더 재밌어?'),
]

_CODE2TEXT = dict(QUESTIONS)
AXES = ('EI', 'SN', 'TF', 'JP')

# 각 문항이 '알아보려는 성향' (LLM이 자연스러운 질문을 만들 때 참고)
_AXIS_INTENT = {
    'EI_1': '사람들과 어울릴 때 힘이 나는지, 아니면 혼자 있어야 충전되는지 (에너지 방향)',
    'EI_2': '새로운 자리에서 먼저 다가가는지, 아니면 누가 다가와주길 기다리는지',
    'SN_1': '뭔가 할 때 구체적으로 계획을 짜는지, 아니면 느낌대로 즉흥으로 하는지',
    'SN_2': '실제로 있었던 사실이 궁금한지, 아니면 그 뒤에 숨은 의미가 궁금한지',
    'TF_1': '친구 고민에 해결책이 먼저 떠오르는지, 아니면 마음 공감이 먼저인지',
    'TF_2': '결정할 때 논리·원칙이 기준인지, 아니면 사람들 기분·분위기가 기준인지',
    'JP_1': '할 일을 미리 끝내야 마음 편한지, 아니면 마감이 닥쳐야 시동 걸리는지',
    'JP_2': '계획이 갑자기 바뀌면 스트레스인지, 아니면 오히려 재밌는지',
}


def question_text(code):
    """질문 코드 → 질문 문장 (없으면 빈 문자열)."""
    return _CODE2TEXT.get(code, '')


def _answered_codes(user):
    from chat.models import MbtiAnswer
    return set(
        MbtiAnswer.objects.filter(user=user).values_list('question_code', flat=True)
    )


def is_complete(user):
    """각 축에 최소 1개 답변이 있으면 수집 완료. 비로그인은 수집 대상 아님."""
    if user is None:
        return True
    answered = _answered_codes(user)
    return all(any(c.startswith(axis) for c in answered) for axis in AXES)


def _next_code(user):
    """다음에 물어볼 미답변 문항 코드. 완료/비로그인 시 None."""
    if user is None or is_complete(user):
        return None
    answered = _answered_codes(user)
    for code, _ in QUESTIONS:
        if code not in answered:
            return code
    return None


def next_question(user):
    """다음 미답변 질문 (code, 고정 template text). 완료/비로그인 시 None.
    (컨텍스트 없이 쓰는 폴백 경로 · generate_question의 하위 호환)"""
    code = _next_code(user)
    return (code, _CODE2TEXT[code]) if code else None


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
        from ai.agents.llm import get_llm
        convo = '\n'.join(
            f"{'사용자' if m.get('role') == 'user' else '나'}: {m.get('content', '')}"
            for m in (recent_history or [])[-6:]
        )
        resp = get_llm(temperature=0.8, max_tokens=80).invoke([
            ('system',
             "너는 사용자의 진짜 친한 친구다. 방금 나눈 대화에 자연스럽게 이어서, "
             "아래 [알아볼 성향]을 슬쩍 떠보는 질문 '하나만' 만들어라.\n"
             "- 심리테스트·설문처럼 딱딱하게 묻지 마. 방금 얘기 흐름에 엮어서, 친구가 문득 궁금해하듯.\n"
             "- 두 갈래 중 뭐냐고 가볍게 고르게 해도 좋아. 반드시 반말, 1~2문장, 오직 순수 한국어.\n"
             "- 물음표로 끝내. 목록/이모지/존댓말 금지."),
            ('user', f"[최근 대화]\n{convo or '(방금 시작됨)'}\n\n[알아볼 성향]\n{intent}"),
        ])
        text = resp.content.strip()
        if not (8 <= len(text) <= 120) or '?' not in text:
            text = fallback
    except Exception:
        text = fallback
    return (code, text) if text else None

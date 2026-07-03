# -*- coding: utf-8 -*-
"""MBTI 서브플로우 — 유도 질문 목록 및 진행 상태 (최종_통합_흐름도 §5).

- 트리거: 턴 종료 후 10초 무입력(프론트 타이머) + 수집 미완료 → GET /api/mbti/next-question/
- 저장: 일반 모드 즉시 / 시크릿 모드 동의 시 (POST /api/mbti/consent/)
- 4개 축(E/I, S/N, T/F, J/P) × 2문항 = 총 8문항. 각 축 최소 1답이면 수집 완료로 간주.
"""

# (question_code, 스몰토크형 유도 질문)
QUESTIONS = [
    ('EI_1', '그러고 보니 궁금한 게 있어요. 주말엔 사람들 만나면 힘이 나요, 아니면 혼자 쉬어야 충전돼요?'),
    ('EI_2', '새로운 모임에 가면 먼저 말을 거는 편이에요, 누가 말 걸어주길 기다리는 편이에요?'),
    ('SN_1', '여행 갈 때 구체적인 코스를 짜는 게 좋아요, 아니면 가서 느낌대로 다니는 게 좋아요?'),
    ('SN_2', '얘기 들을 때 실제 있었던 일이 궁금해요, 아니면 그 뒤에 숨은 의미가 더 궁금해요?'),
    ('TF_1', '친구가 고민을 털어놓으면 해결책부터 떠올라요, 아니면 마음이 어땠을지가 먼저 떠올라요?'),
    ('TF_2', '결정할 때 논리적으로 맞는지가 중요해요, 아니면 사람들 기분이 상하지 않는 게 중요해요?'),
    ('JP_1', '할 일이 생기면 미리미리 끝내야 마음이 편해요, 아니면 마감이 다가와야 시동이 걸려요?'),
    ('JP_2', '계획이 갑자기 바뀌면 스트레스 받는 편이에요, 아니면 오히려 재밌다고 느껴요?'),
]

_CODE2TEXT = dict(QUESTIONS)
AXES = ('EI', 'SN', 'TF', 'JP')


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


def next_question(user):
    """다음 미답변 질문 (code, text) 반환. 완료/비로그인 시 None."""
    if user is None or is_complete(user):
        return None
    answered = _answered_codes(user)
    for code, text in QUESTIONS:
        if code not in answered:
            return code, text
    return None

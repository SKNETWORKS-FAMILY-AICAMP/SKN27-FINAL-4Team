# -*- coding: utf-8 -*-
"""답변 접지 검증 (2026-07-14) — 근거 없는 '과거 대화 단정' 차단.

대상 결함 (평가 실측): R02 "한강 얘기 많이 했잖아"(한 번 말함),
F02 "저번에 말한 그 친구랑 연락한다며"(잊어서 컨텍스트에 없는데 맞장구).
공통점: 컨텍스트에 없는 "네가 전에 말했다"를 지어내는 것.

구조 — 결정적 게이트 → LLM 확인 (위기 감지·만료 벡터와 같은 시그니처 패턴):
  ① 게이트: 답변에 과거 단정·빈도 주장 신호가 없으면 통과 (대부분의 턴 — 비용 0)
  ② 신호가 있으면 검증 LLM 1회: 그 단정이 컨텍스트(기억+최근 대화)에 근거 있나
  ③ 근거 없으면 호출부가 1회 재생성 (그 단정 금지 지시 주입)

소비자: ai/agents/nodes.py(운영) + chat/memory_eval.py(평가) — 같은 모듈, 같은 동작.
실패 시 무해: 검증 LLM 오류면 통과 처리 (챗봇 흐름을 막지 않는다).
"""
import re

# 과거 대화 단정 신호어 — "네가 전에 ~했다/말했다"류
_PAST_CLAIM = re.compile(
    r'했(었)?잖아|했었지|말했(었)?잖아|말했었|그랬잖아|한다고 했|다고 했(었)?잖아')
# 빈도 주장 — 어순 무관 조합으로 판정: "많이 얘기했" / "얘기를 많이 했" 둘 다
# (5회차 어순 구멍 실측 후 확장, 2026-07-14)
_FREQ = re.compile(r'자주|많이|계속|맨날|종종|여러\s*번')
_TALK = re.compile(r'얘기|이야기|말(했|하)')
# 위기 발화 재인용 게이트 (F2, E2E 실측 2026-07-14): 요약에 남긴 위기 발화("죽고 싶다")를
# 캐주얼한 답변(리포트 요약 등)이 원문 그대로 재인용하는 사고 차단. 사용자가 이번 턴에
# 먼저 꺼낸 경우는 예외 (위로 연속성 — 요약에 위기를 남기는 이유 그 자체).
_CRISIS_ECHO = re.compile(r'죽고\s*싶|자살|자해|사라지고\s*싶|끝내\s*버리고\s*싶')


def _verify_llm(answer: str, evidence: str, question: str):
    """단정이 근거 있는지 LLM 판정. 반환: 근거 없는 단정 요지(str) 또는 None(문제 없음)."""
    from ai.agents.llm import get_llm
    resp = get_llm(temperature=0, max_tokens=40).invoke([
        ('system',
         "검증자다. [답변 초안]에서 '사용자가 과거에 말했다/했었다'고 단정하는 내용을 찾아, "
         "그 근거가 [컨텍스트]에 있는지 판정하라.\n"
         "- 근거 없는 단정이 있으면: 그 단정의 요지만 15자 이내로 출력.\n"
         "- 전부 근거가 있거나 단정이 없으면: '없음' 한 단어만 출력.\n"
         "주의1: '많이/자주 얘기했다'는 ① [요즘 흐름]에 있거나 ② 컨텍스트에 같은 주제의 "
         "기억이 3개 이상 나열돼 있으면 근거 인정. 한두 번 언급을 '자주'라고 하면 근거 없음이다.\n"
         "주의2: 컨텍스트에 있는 사실을 표현만 바꿔 말한 것은 근거 있음이다 "
         "('그만뒀어'→'그만둔 거 기억나', '먹기로 했어'→'먹기로 했잖아'). "
         "자구가 달라도 같은 사실이면 통과시켜라 — 과잉 차단이 누락보다 나쁘다.\n"
         "주의3(딱 한 가지 예외): 컨텍스트에 취향('좋아한다/빠져있다/시작했다')만 있는데 "
         "답변이 그걸 '~하기로 했다/약속했다'는 계획으로 승격해 단정하면 근거 없음이다 "
         "(취향≠계획 — 실측 날조 사례). 이 경우가 아니고 애매하면 '없음'을 출력하라."),
        ('user', f'[컨텍스트]\n{evidence}\n\n[사용자 질문]\n{question}\n\n[답변 초안]\n{answer}'),
    ])
    text = (resp.content or '').strip()
    if not text or text.startswith('없음'):
        return None
    return text[:30]


def check_grounded(answer: str, evidence: str, question: str = '', crisis_turn: bool = False):
    """(통과 여부, 근거 없는 단정 요지) 반환. crisis_turn=True면 위기 게이트 우회."""
    # 위기 재인용은 최우선·결정적 (LLM 검증 불필요 — 인용 자체가 위반).
    # 단 이번 턴이 위기로 분류됐으면 우회 (감사 P1-2): "다 끝내고 싶어"처럼 게이트 어휘를
    # 벗어난 위기 표현에서 봇의 정당한 공감("죽고 싶을 만큼 힘들구나")을 막으면 안 된다.
    if not crisis_turn and _CRISIS_ECHO.search(answer or '') and not _CRISIS_ECHO.search(question or ''):
        print('[answer_guard] 위기 발화 재인용 감지 → 재생성 (완곡화 지시)')
        return False, '위기 발화 재인용'
    freq_claim = bool(_FREQ.search(answer or '') and _TALK.search(answer or ''))
    past_claim = bool(_PAST_CLAIM.search(answer or ''))
    if not answer or not (freq_claim or past_claim):
        return True, None   # 과거 단정·빈도 주장 자체가 없음 — 비용 0 통과
    # 빈도 게이트 디커플 (감사 P2-3, 2026-07-14): 이전엔 [요즘 흐름] 없으면 무조건
    # 재생성했지만, 통찰 생성이 확률적이라 "무슨 얘기 많이 했지?" 질문에서 봇이 구조적으로
    # 못 이기는 게임이 됐다. 이제 빈도 주장도 LLM 검증으로 — 검증자가 '같은 주제 기억
    # 3개 이상'을 근거로 인정할 수 있다 (R02식 한 번 언급 '자주' 뻥은 여전히 차단).
    try:
        offending = _verify_llm(answer, evidence or '(비어 있음)', question)
    except Exception as e:
        print(f'[answer_guard] 검증 실패(통과 처리): {e}')
        return True, None
    if offending is None:
        return True, None
    print(f"[answer_guard] 근거 없는 단정 감지: '{offending}' → 재생성")
    return False, offending


def retry_instruction(offending: str, attempt: int = 1) -> str:
    """재생성 시 주입할 지시문. 2차부터는 초강수 — 빈도·단정 표현 자체를 금지."""
    if offending and '위기' in offending:
        return ("★재작성 지시: '죽고 싶다' 같은 위기 발화 원문을 인용하지 마라. "
                "그 시기는 '마음이 많이 무거웠던 때가 있었다' 정도로만 완곡하게 담고, "
                "나머지 내용은 그대로 답하라.★")
    if attempt >= 2:
        return ("★재작성 지시(최종): '자주/많이/계속/맨날 얘기했다', '~했잖아/했었지' 같은 "
                "표현을 한 글자도 쓰지 마라. 컨텍스트에 있는 일들을 그냥 나열만 하거나, "
                "모르면 모른다고 답하라.★")
    return (f"★방금 초안에서 '{offending}'라는 단정을 했는데, 컨텍스트에 그 근거가 없다. "
            "근거 없는 '전에 말했잖아'류 단정 없이 다시 답하라 — 확실하지 않으면 "
            "단정 대신 물어보거나, 모른다고 솔직하게.★")

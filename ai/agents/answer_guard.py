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


def _verify_llm(answer: str, evidence: str, question: str):
    """단정이 근거 있는지 LLM 판정. 반환: 근거 없는 단정 요지(str) 또는 None(문제 없음)."""
    from ai.agents.llm import get_llm
    resp = get_llm(temperature=0, max_tokens=40).invoke([
        ('system',
         "검증자다. [답변 초안]에서 '사용자가 과거에 말했다/했었다'고 단정하는 내용을 찾아, "
         "그 근거가 [컨텍스트]에 있는지 판정하라.\n"
         "- 근거 없는 단정이 있으면: 그 단정의 요지만 15자 이내로 출력.\n"
         "- 전부 근거가 있거나 단정이 없으면: '없음' 한 단어만 출력.\n"
         "주의: '많이/자주 얘기했다'는 컨텍스트의 [요즘 흐름]에 있을 때만 근거 인정. "
         "한 번 언급된 일을 자주라고 하면 근거 없음이다."),
        ('user', f'[컨텍스트]\n{evidence}\n\n[사용자 질문]\n{question}\n\n[답변 초안]\n{answer}'),
    ])
    text = (resp.content or '').strip()
    if not text or text.startswith('없음'):
        return None
    return text[:30]


def check_grounded(answer: str, evidence: str, question: str = ''):
    """(통과 여부, 근거 없는 단정 요지) 반환."""
    freq_claim = bool(_FREQ.search(answer or '') and _TALK.search(answer or ''))
    past_claim = bool(_PAST_CLAIM.search(answer or ''))
    if not answer or not (freq_claim or past_claim):
        return True, None   # 과거 단정·빈도 주장 자체가 없음 — 비용 0 통과
    # 빈도 주장은 결정적 판정 (2026-07-14): 설계상 빈도의 근거는 [요즘 흐름]뿐이다
    # — 통찰 없이 '많이/자주 얘기했다'는 무조건 근거 없음. 검증 LLM의 관대함(3회차
    # 실측)에 맡기지 않고 코드가 판정한다.
    if freq_claim and '요즘 흐름' not in (evidence or ''):
        print("[answer_guard] 빈도 주장인데 [요즘 흐름] 없음 → 재생성 (결정적 판정)")
        return False, '많이/자주 얘기했다는 주장'
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
    if attempt >= 2:
        return ("★재작성 지시(최종): '자주/많이/계속/맨날 얘기했다', '~했잖아/했었지' 같은 "
                "표현을 한 글자도 쓰지 마라. 컨텍스트에 있는 일들을 그냥 나열만 하거나, "
                "모르면 모른다고 답하라.★")
    return (f"★방금 초안에서 '{offending}'라는 단정을 했는데, 컨텍스트에 그 근거가 없다. "
            "근거 없는 '전에 말했잖아'류 단정 없이 다시 답하라 — 확실하지 않으면 "
            "단정 대신 물어보거나, 모른다고 솔직하게.★")

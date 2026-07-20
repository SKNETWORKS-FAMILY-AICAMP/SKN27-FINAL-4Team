# -*- coding: utf-8 -*-
"""PII 마스킹 (2026-07-15, 팀 안건) — 개인정보는 시스템 입구에서 완전 제거.

원칙 (팀 결정):
- ★형태(패턴) 기반★: 회원 본인 값 대조가 아니라, 전화번호·주민번호처럼 '생긴' 것은
  누구의 것이든 전부 마스킹 — 채팅 속 제3자 정보(친구 번호 등)까지 커버.
- ★완전 마스킹★: 부분 보존(010-****-5678) 없이 값 전체를 [종류] 태그로 치환.
  뒤 4자리도 본인확인 재료라 위험하다는 결정 — 값은 0비트도 남기지 않는다.
- ★입구 1회★: 메시지 수신 직후(views.chat_turn) 적용 → 이후의 LLM 전송·원본 저장·
  요약·그래프가 전부 자동으로 안전. "저장소에도 AI에게도 원문이 존재한 적 없음."
- 결정적 정규식 — LLM 판단 없음(오탐/환각 0 원칙). 시그니처 패턴의 게이트 층.

오폭 방지: 날짜(2026-07-20, 7월 20일), D-day, 금액 등 일상 숫자는 구조(자릿수·
구분자·프리픽스)가 달라 매칭되지 않는다 — test_pii_mask.py로 박제.
"""
import re

# 순서 중요: 긴/구체적 패턴 먼저 (주민 13자리가 전화로 반쪽 매칭되는 것 방지)
_PATTERNS = [
    # 주민등록번호: 6자리-[1~8]로 시작하는 7자리 (성별 자리 1~8)
    ('주민번호', re.compile(r'\d{6}\s*[-‐–]\s*[1-8]\d{6}')),
    # 카드번호: 4-4-4-4 (구분자 있음) 또는 붙은 15~16자리
    ('카드번호', re.compile(r'\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}|(?<!\d)\d{15,16}(?!\d)')),
    # 전화번호: 휴대폰(01X) 구분자 유무 + 유선(0XX-XXX(X)-XXXX 구분자 필수)
    ('전화번호', re.compile(
        r'01[016789][-. ]?\d{3,4}[-. ]?\d{4}'
        r'|(?<!\d)0\d{1,2}[-. ]\d{3,4}[-. ]\d{4}(?!\d)')),
    ('이메일', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')),
]

# 계좌번호: 자릿수만으론 오폭 위험(운송장·쿠폰 등) → '계좌 문맥 단어'가 있을 때만
_ACCOUNT_CTX = re.compile(r'계좌|입금|송금|이체|은행|적금|통장')
_ACCOUNT_NUM = re.compile(r'(?<!\d)\d{2,6}[- ]?\d{2,6}[- ]?\d{2,8}(?!\d)')


def mask(text: str):
    """(마스킹된 텍스트, 감지된 종류 리스트) 반환. 감지 없으면 원문 그대로."""
    if not text:
        return text, []
    found = []
    for label, pattern in _PATTERNS:
        text, n = pattern.subn(f'[{label}]', text)
        if n:
            found.append(label)
    # 계좌: 문맥 단어 + 총 10자리 이상 숫자 덩어리일 때만
    if _ACCOUNT_CTX.search(text):
        def _acct(m):
            digits = re.sub(r'\D', '', m.group(0))
            if len(digits) >= 10:
                if '계좌번호' not in found:
                    found.append('계좌번호')
                return '[계좌번호]'
            return m.group(0)   # 짧은 숫자(금액 등)는 보존
        text = _ACCOUNT_NUM.sub(_acct, text)
    return text, found


def notice(found: list) -> str:
    """감지 턴에 봇 답변 뒤에 붙는 결정적 안내 한 줄 (투명성 — LLM에 안 맡김)."""
    if not found:
        return ''
    return f" 아 그리고, {'·'.join(found)} 같은 건 개인정보라 내가 안전하게 가리고 기억할게!"

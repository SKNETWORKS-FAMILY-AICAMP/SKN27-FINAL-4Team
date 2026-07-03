# -*- coding: utf-8 -*-
"""LangGraph 공유 상태 (ChatState) — [개별] LangGraph_흐름도_김한솔.md v6.0 §1 기준."""
from typing import Optional, TypedDict


class ChatState(TypedDict, total=False):
    # 식별/세션
    user_id: Optional[int]
    session_id: int
    session_mode: str            # "normal" | "secret"
    character_id: str            # pori / kkami / toto / yeoul

    # 입력
    user_message: str
    selected_emotion: Optional[str]   # 콜드스타트에서 선택한 초기 감정 (첫 턴 참고)

    # MBTI 서브플로우
    mbti_pending: bool
    mbti_question_text: str           # 직전에 던진 MBTI 질문 (판별용)
    mbti_question_code: str
    is_mbti_answer: Optional[bool]    # mbti_check_node 판별 결과
    mbti_needs_consent: bool          # 시크릿 모드: 저장 동의 필요 → 프론트 버튼
    mbti_saved: bool

    # 컨텍스트 (감정 라우팅 직후 1회 조회)
    recent_history: list              # [{'role': 'user'|'assistant', 'content': str}]
    memory_summary: str               # user_memory.summary_text

    # 감성분석 (KcELECTRA + XGBoost, argmax 확정 분류)
    emotion_probs: dict
    emotion_label: str                # joy / sadness / anger / normal

    # 응답 생성
    agent_guide: str                  # 감정 에이전트가 만든 응답 지침
    need_plan: bool                   # ⚠️ 트리거 조건 미확정 — 현재는 버튼 기반이라 항상 False
    search_context: str               # Tavily 검색 결과
    final_response: str

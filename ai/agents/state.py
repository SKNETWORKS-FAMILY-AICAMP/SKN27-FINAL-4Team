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
    image_data_url: Optional[str]     # 사진 첨부 시 data URL (멀티모달 · 저장 안 함)
    image_caption: str                # 사진 한 줄 캡션 (저장·리포트·기억용, analysis_node 생성)
    selected_emotion: Optional[str]   # 콜드스타트에서 선택한 초기 감정 (첫 턴 참고)

    # MBTI 서브플로우
    mbti_pending: bool
    mbti_question_text: str           # 직전에 던진 MBTI 질문 (판별용)
    mbti_question_code: str
    is_mbti_answer: Optional[bool]    # mbti_check_node 판별 결과
    mbti_saved: bool                  # (시크릿은 MBTI 질문 자체를 안 함 — 완전 무저장)

    # 컨텍스트 (감정 라우팅 직후 1회 조회)
    recent_history: list              # [{'role': 'user'|'assistant', 'content': str}]
    memory_summary: str               # user_memory.summary_text

    # 감성분석 (KcELECTRA + XGBoost, argmax 확정 분류)
    emotion_probs: dict
    emotion_label: str                # joy / sadness / anger / normal
    prev_emotion: Optional[str]       # 직전 턴 감정 (초단문 바이패스·저확신 폴백용)
    emotion_source: str               # model / llm_context / short_bypass / crisis / mixed_llm / mixed_model / fallback (디버깅용)
    emotion_secondary: Optional[str]  # 복합 감정의 부감정 (응답 생성 전용 — 저장하지 않음, 2026-07-10)
    crisis: bool                      # 위기 신호 감지 (라우팅 전용 — 저장하지 않음, 2026-07-10)

    # 응답 생성
    agent_guide: str                  # 감정 에이전트가 만든 응답 지침
    final_response: str
    # (need_plan·search_context는 Plan Agent(장소 추천) 폐기로 제거 — 2026-07-05)

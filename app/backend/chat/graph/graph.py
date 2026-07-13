# -*- coding: utf-8 -*-
"""StateGraph 조립 — [개별] LangGraph_흐름도_김한솔.md v6.0 §3·§5 기준.

라우팅 규칙:
  entry ─ mbti_pending? ─ 예 → mbti_check ─ 답변? ─ yes → mbti_save → END
        │                                 └ no ──→ load_context (pending 해제는 뷰에서)
        └ 아니오 ──────────────────────────────→ load_context
  load_context → analysis → (emotion_label) → joy/sadness/anger/normal_agent
  (컨텍스트를 분석보다 먼저 조회 — 저확신 시 LLM 재분류가 최근 대화를 참고하기 위함)
  agent → resp_prep → END

콜드스타트 게이팅·TTS·저장(비동기)·유휴 타이머는 그래프 밖(뷰/프론트)에서 처리.
체크포인터는 사용하지 않음 — 턴 단위 stateless, 컨텍스트는 PostgreSQL에서 조회.
"""
from langgraph.graph import END, StateGraph

from ai.agents.nodes import (
    analysis_node,
    anger_agent_node,
    crisis_agent_node,
    joy_agent_node,
    load_context_node,
    mbti_check_node,
    mbti_save_node,
    normal_agent_node,
    resp_prep_node,
    sadness_agent_node,
)
from ai.agents.state import ChatState

_graph = None


def build_graph():
    builder = StateGraph(ChatState)

    builder.add_node('mbti_check', mbti_check_node)
    builder.add_node('mbti_save', mbti_save_node)
    builder.add_node('analysis', analysis_node)
    builder.add_node('load_context', load_context_node)
    builder.add_node('joy_agent', joy_agent_node)
    builder.add_node('sadness_agent', sadness_agent_node)
    builder.add_node('anger_agent', anger_agent_node)
    builder.add_node('normal_agent', normal_agent_node)
    builder.add_node('crisis_agent', crisis_agent_node)   # 위기 대응 (2026-07-10)
    builder.add_node('resp_prep', resp_prep_node)

    # entry: MBTI pending 체크 (입력 직후 최우선)
    builder.set_conditional_entry_point(
        lambda s: 'mbti_check' if s.get('mbti_pending') else 'load_context',
        {'mbti_check': 'mbti_check', 'load_context': 'load_context'},
    )

    # mbti_check: 답변이면 저장/확인응답, 아니면 일반 플로우 합류
    builder.add_conditional_edges(
        'mbti_check',
        lambda s: 'mbti_save' if s.get('is_mbti_answer') else 'load_context',
        {'mbti_save': 'mbti_save', 'load_context': 'load_context'},
    )
    builder.add_edge('mbti_save', END)

    # 컨텍스트 1회 조회 → 감성분석(위기 감지 → 확신도 게이트) → 에이전트 1개만 실행
    # 위기 감지 시 감정은 sadness로 고정(표정·TTS 톤 일관)하되 crisis_agent가 위로 전담
    builder.add_edge('load_context', 'analysis')
    builder.add_conditional_edges(
        'analysis',
        lambda s: 'crisis' if s.get('crisis') else s.get('emotion_label', 'normal'),
        {
            'crisis': 'crisis_agent',
            'joy': 'joy_agent',
            'sadness': 'sadness_agent',
            'anger': 'anger_agent',
            'normal': 'normal_agent',
        },
    )

    # 에이전트 → 응답 정제 (Plan Agent는 장소 추천 기능 폐기로 제거 — 2026-07-05)
    for agent in ('joy_agent', 'sadness_agent', 'anger_agent', 'normal_agent', 'crisis_agent'):
        builder.add_edge(agent, 'resp_prep')
    builder.add_edge('resp_prep', END)

    return builder.compile()


def get_graph():
    """모듈 싱글턴 (최초 1회 컴파일)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

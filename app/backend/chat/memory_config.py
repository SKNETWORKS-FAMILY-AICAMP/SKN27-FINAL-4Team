# -*- coding: utf-8 -*-
"""기억 시스템 다이얼 일원화 (2026-07-19) — 흩어져 있던 조절값을 한 곳으로.

기준 (하드코딩 정리 원칙, 2026-07-19 합의):
  ① 틀린 답이 존재하는 '의미 판단'은 LLM(+결정적 게이트)이 한다 — 숫자로 흉내내지 않는다.
  ② '많고 적음'만 있는 양·범위는 숫자 다이얼로 두되, env로 빼고 실측 근거를 적는다.
  ③ 데이터에서 유도 가능한 값은 유도한다 — 예: 종결 단언 노출 창은 사건 자신의
     occurs 날짜에서 유도 (CLOSURE_WINDOW=14 삭제, 2026-07-19).

소비자: graph_memory_v2_base(운영 v2).
v1(graph_memory)은 발표까지 보험으로 동결 — 자체 상수 유지 (발표 후 통합).
"""
import os

# ── 회상 — 양 다이얼 (기준 ②) ──────────────────────────────
RECALL_LIMIT = int(os.environ.get('MEM_RECALL_LIMIT', '6'))            # 일반 기억 노출 상한 — 프롬프트 오염 방지
OPENLOOP_MAX_AGE = int(os.environ.get('MEM_OPENLOOP_AGE_DAYS', '30'))  # 열린 고리(안 끝난 일) 추적 최대 나이
RELCHANGE_WINDOW = int(os.environ.get('MEM_RELCHANGE_DAYS', '30'))     # 관계 변화 회고 창
ABSENCE_MIN = int(os.environ.get('MEM_ABSENCE_DAYS', '7'))             # 공백 인사 최소 일수

# ── 임베딩 임계값 — v1 실측 잠정치, v2 스키마에서 벤치 재측정 대상 ──
VEC_INDEX = 'memory_vec'   # v1과 공유 (Event.embedding, 768, cosine)
VEC_RECALL_MIN = float(os.environ.get('MEM_VEC_RECALL_MIN', '0.33'))   # 의미 회상 채널 최소 유사도
VEC_DEDUP_MIN = float(os.environ.get('MEM_VEC_DEDUP_MIN', '0.93'))     # 중복 병합 최소 유사도
EXPIRE_VEC_MIN = float(os.environ.get('MEM_EXPIRE_VEC_MIN', '0.60'))   # 만료 대상 벡터 매칭 최소 유사도

# ── 쿼리 안 숫자 장부 (기준 ② — 위치 기록용. 쿼리 원문은 graph_memory_v2_base) ──
# LIMIT 3        : 회상 채널별 노출 상한 (종결 단언·다가오는 일·최근 종결 나열)
# LIMIT 4        : 의미·감정 채널 노출 상한
# LIMIT 10/20/30 : LLM 해석기에 주는 후보 풀 크기 (인물 10 / 이름 20 / 활성 항목 30)
# *1..5          : 인과 사슬(BECAUSE_OF) 추적 최대 깊이
# RECENT_N=10    : 최근 원문 턴 수 (ai/agents/nodes.py — 위로 연속성 담당)
# 이 숫자를 바꿀 땐 여기 장부와 해당 쿼리를 같이 고친다 (숫자만 흩어지는 것 방지).
#
# ── 다른 도메인의 다이얼 위치 (전체 지도) ──
# 감정 게이트 4종 (EMO_*)   : ai/agents/nodes.py 상단 — env 오버라이드 가능
# TTS 4종 (TTS_*)           : chat/tts_service.py 상단 — env 오버라이드 가능
# LLM 호출별 max_tokens/temperature : 호출부 설계값 (이주 안 함 — 목적별로 다른 게 정상)
# MBTI 질문 주기(3턴 후 4턴마다)·최근 6개 조회 : chat/views.py (UX 설계 확정 후 재논의)

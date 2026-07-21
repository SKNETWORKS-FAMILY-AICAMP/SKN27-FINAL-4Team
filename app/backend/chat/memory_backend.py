# -*- coding: utf-8 -*-
"""기억 백엔드 — v2 단일화 (2026-07-21).

역사: v1/v2 전환 스위치(MEMORY_V2 플래그)로 운영하다가, v2가 27종 평가
94%·테스트 85종을 통과하며 기준선을 넘어 v1을 완전 철거했다.
.env의 MEMORY_V2는 더 이상 읽지 않는다 (있어도 무해).

모든 소비자(views·nodes·opener·커맨드)는 이 모듈만 임포트한다 —
그래프 구현을 직접 임포트하는 새 코드 금지 (죽은 스키마 오참조 사고 방지).
"""
from chat import graph_memory_v2_base as backend

recall = backend.recall
capture_async = backend.capture_async
is_enabled = backend.is_enabled
upcoming = backend.upcoming
panel_summary = backend.panel_summary

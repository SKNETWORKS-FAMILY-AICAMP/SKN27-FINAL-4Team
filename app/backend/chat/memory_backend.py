# -*- coding: utf-8 -*-
"""기억 백엔드 선택 스위치 (2026-07-18) — v1/v2 전환은 이 플래그 하나.

.env:  MEMORY_V2=1  → v2 기본 스키마(graph_memory_v2_base)
       (미설정/그 외) → v1(graph_memory)

배선 = .env 한 줄 + 서버 재시작. 롤백 = 플래그 제거 + 재시작 (코드 무변경).
게이트 원칙(§8-4-6): 플래그를 1로 올리는 것은 27종×3회 실측이 기준선을 넘은 뒤에만.
"""
import os

if os.environ.get('MEMORY_V2', '').strip() == '1':
    from chat import graph_memory_v2_base as backend
    print('[memory_backend] v2 기본 스키마(graph_memory_v2_base) 사용')
else:
    from chat import graph_memory as backend
    print('[memory_backend] v1(graph_memory) 사용')

recall = backend.recall
capture_async = backend.capture_async
is_enabled = backend.is_enabled
upcoming = getattr(backend, 'upcoming', lambda uid, days=None: '')
panel_summary = getattr(backend, 'panel_summary',   # v1엔 없음 → 빈 패널 (롤백 안전)
                        lambda uid: {'upcoming': [], 'prefs': [], 'people': [], 'recent': []})

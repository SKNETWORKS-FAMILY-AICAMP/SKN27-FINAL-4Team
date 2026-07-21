# -*- coding: utf-8 -*-
"""챗봇 URL 라우팅 — 단일 파일.
config/urls.py 에서 path('api/', include('chat.urls')) 로 마운트된다.
전체 엔드포인트 목록은 views.py 상단 docstring 참조."""
from django.urls import path

from . import views

urlpatterns = [
    # ── 메인 플로우 (v6.0 · LangGraph) ──
    path('session/start/',       views.session_start),       # 세션 시작 (친구 첫인사)
    path('session/end/',         views.session_end),         # 세션 종료 (시크릿 캐시 파기)
    path('chat/',                views.chat_turn),           # 대화 턴 (텍스트 즉시 + tts_task_id)
    path('tts/<str:task_id>/',       views.tts_status),      # TTS 상태 폴링
    path('tts/<str:task_id>/audio/', views.tts_audio),       # 오디오 1회 다운로드 후 파기
    path('mbti/next-question/',  views.mbti_next_question),  # MBTI 질문 (10초 유휴 · 일반 전용)
    path('memory/panel/',        views.memory_panel),        # 기억 패널 (좌측 UI 카드, UI #3)
]

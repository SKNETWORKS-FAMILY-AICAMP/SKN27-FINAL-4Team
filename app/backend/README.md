# backend — 웰니스 챗봇 백엔드 (Django + LangGraph)

기준 문서: `docs/최종_통합_흐름도.md` · `docs/[개별] API_명세서_김한솔.md` (v6.0)

## 파일 구조 (2026-07-02 정리 완료)

```
backend/
├── config/
│   ├── settings.py      DB(Postgres)·MEDIA·ElevenLabs·캐시 설정
│   └── urls.py          admin / api/user / api/mypage / api/(chat)
├── chat/                ★ 챗봇 핵심 앱 — views.py와 urls.py는 각각 하나뿐
│   ├── views.py         모든 챗봇 엔드포인트 (상단 docstring에 전체 목록)
│   ├── urls.py          모든 챗봇 라우팅
│   ├── models.py        ChatSession / ChatMessage / UserMemory / MbtiAnswer / WalkCuration
│   ├── graph/           LangGraph 멀티에이전트
│   │   ├── state.py       ChatState 스키마
│   │   ├── personas.py    캐릭터 4종(포리·까미·토토·여울) + 감정 지침
│   │   ├── nodes.py       노드: mbti_check/analysis/load_context/감정에이전트4/resp_prep
│   │   └── graph.py       StateGraph 조립 (라우팅 규칙 주석 참조)
│   ├── emotion_model.py KcELECTRA+XGBoost 감정분류 (산출물 없으면 자동 폴백)
│   ├── tts_service.py   ElevenLabs TTS 백그라운드 생성 + 폴링
│   ├── mbti.py          MBTI 8문항 + 수집 진행 판정
│   ├── memory.py        user_memory 장기 요약 (비동기)
│   ├── secret_cache.py  시크릿 모드 RAM 캐시 (DB 저장 없음)
│   ├── plan_service.py  Tavily 장소 검색 (+WalkCuration 조인)
│   └── tests.py         python manage.py test chat (sqlite — Postgres 불필요)
├── user/                로그인/회원 (팀 공용)
└── wellness/            마이페이지 (팀 공용)
```

## 실행

```bash
# 로컬
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# 또는 docker (레포 루트에서 — DB 리셋 포함)
docker compose down -v && docker compose up -d --build
```

## 필요한 .env 키

| 키 | 필수 | 비고 |
|---|---|---|
| `OPENAI_API_KEY` | Y | LLM (기본 공급자 — 2026-07-02 OpenAI로 확정) |
| `OPENAI_MODEL` | N | 기본 `gpt-5.4-mini` |
| `LLM_PROVIDER` | N | `openai`(기본) / `groq` — groq 쓸 땐 `GROQ_API_KEY` 필요 |
| `PG_*` | Y | PostgreSQL 접속 (docker면 자동) |
| `TAVILY_API_KEY` | N | 없으면 plan-support가 빈 결과 |
| `ELEVENLABS_API_KEY` + `VOICE_ID_{PORI,KKAMI,TOTO,YEOUL}` | N | 없으면 TTS만 failed, 대화는 정상 |

> .env는 레포 루트 하나로 통합. docker와 로컬 runserver 모두 루트 `.env`를 읽음.

## 검증 상태 (2026-07-02)

- `manage.py check` 통과, 미적용 마이그레이션 없음
- `manage.py test chat` — 9개 테스트 통과 (부가 API 3 + v6 플로우 6)
- LLM 실호출 경로(chat_turn 전체)는 스모크 테스트 필요

## 삭제/보관된 것

- `views_v6.py`/`urls_v6.py` → `views.py`/`urls.py`로 병합 (`_archive/backend_merged/` 보관)
- send_message·stream_tts·이너카운슬·차/BGM 추천·👍👎 피드백(MLOps) → 기능 제거 (레포 루트 `_archive/README.md` 참조)

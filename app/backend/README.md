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
│   ├── models.py        ChatSession / ChatMessage / UserMemory / MbtiAnswer
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
| `ELEVENLABS_API_KEY` + `VOICE_ID_{PORI,KKAMI,TOTO,YEOUL}` | N | 없으면 TTS만 failed, 대화는 정상 |
| `NLK_BIBLIO_SERVICE_KEY` | 마이페이지 도서 | 공공데이터포털의 `국립중앙도서관_서지 정보 제공 서비스` 활용신청 후 받은 일반 인증키(Decoding). 공통 키 `DATA_GO_KR_SERVICE_KEY`도 지원 |
| `NLK_ISBN_SERVICE_KEY` | N(표지 권장) | 국립중앙도서관 Open API의 `ISBN 서지정보` 승인 인증키. 없으면 서지 추천은 정상 동작하고 표지만 대체 이미지로 표시 |
| `TAVILY_API_KEY` | 마이페이지 날씨 | 공개 웹 날씨 맥락 검색. 사용자 프로필·정밀 좌표는 전송하지 않음 |
| `TAVILY_PLAN_NAME` | 운영 권장 | 확인한 Tavily 구독/계약 플랜명 |
| `TAVILY_COMMERCIAL_USE_CONFIRMED` | 운영 권장 | 고객용 서비스 통합 권한을 계약에서 확인한 후 `true`; 미설정 시 `manage.py check` 경고 |
| `TAVILY_KEY_ENVIRONMENT` | N | `development`(기본, 100 RPM) / `production`(1,000 RPM, 유료 플랜 또는 PAYGO 필요) |
| `TAVILY_SEARCH_DEPTH` | N | 기본 `basic`(1크레딧). `advanced`는 2크레딧이라 날씨 검색에는 비권장 |
| `TAVILY_INCLUDE_DOMAINS` | N | 기본 `weather.naver.com,weatheri.co.kr,kweather.co.kr`; 공급자명 검색 뒤 GPT에 노출할 HTTPS 결과를 후처리 필터링 |
| `KMA_CACHE_SECONDS` | N | 동일 격자·발표시각의 기상청 응답 공동 캐시, 기본 600초 |
| `KMA_API_HUB_AUTH_KEY` | 마이페이지 전체 날씨 | 기상청 API허브 인증키. 동네예보·중기예보·특보현황의 사용 세부 API를 모두 활용 신청한 키 |
| `KMA_API_HUB_SERVICES_CONFIRMED` | 운영 필수 | 전체 세부 API 정상 호출을 확인한 뒤 `true`; 미설정 시 `manage.py check` 경고 |
| `KMA_API_HUB_WEEKLY_SERVICES_CONFIRMED` | 운영 필수 | `getVilageFcst`·`getMidTa`·`getMidLandFcst` 실호출 성공 후 `true` |
| `KMA_API_HUB_VILAGE_ENDPOINT` | N | 기본 API허브 `VilageFcstInfoService_2.0` 호스트 |
| `KMA_API_HUB_MID_ENDPOINT` | N | 기본 API허브 `MidFcstInfoService` 호스트 |
| `KMA_API_HUB_WARNING_ENDPOINT` | N | 기본 API허브 `wrn_now_data.php` 호스트 |
| `KMA_WEEKLY_CACHE_SECONDS` | N | 단기·중기 7일 예보 공동 캐시, 기본 10,800초(3시간) |
| `KMA_WARNING_CACHE_SECONDS` | N | 전국 현재 특보현황 공동 캐시, 기본 300초 |

> .env는 레포 루트 하나로 통합. docker와 로컬 runserver 모두 루트 `.env`를 읽음.

### 날씨 API 배포 기준 (2026-07-15 확인)

- 구조화 기상 데이터는 기상청 API허브로 단일화했습니다. `getUltraSrtNcst`, `getUltraSrtFcst`, `getVilageFcst`, `getMidTa`, `getMidLandFcst`, `wrn_now_data.php`가 하나의 `KMA_API_HUB_AUTH_KEY`를 사용하며 기존 `KMA_API_KEY` 공공데이터포털 호출은 사용하지 않습니다. API허브 일반회원 한도는 일 20,000건·5GB입니다.
- 서버는 실황·초단기예보를 격자/발표시각별 10분 공동 캐시하고 일시 장애 때 최대 2시간 내 직전 정상값을 사용합니다. 전국 특보는 5분 공동 캐시한 뒤 선택 지역만 표시합니다.
- Tavily 무료 플랜은 월 1,000크레딧입니다. 검색은 네이버 날씨·웨더아이·케이웨더 공개 결과만 `basic` 깊이로 조회하고 지역·검색일별 30분 공동 캐시합니다. `검색 기반 주간예보 참고`는 API허브 단기·중기 7일 자료를 GPT가 요약하고, 민간 검색 결과는 설명·생활 추천 문맥만 보완합니다. 수치·예보·특보가 API허브와 다르면 API허브를 우선합니다.
- Tavily production 키는 유료 플랜 또는 PAYGO가 필요합니다. 고객용 배포 전 Tavily 서비스 약관·AUP를 서비스 이용약관에 반영하고 `TAVILY_PLAN_NAME`, `TAVILY_KEY_ENVIRONMENT`, `TAVILY_COMMERCIAL_USE_CONFIRMED`를 실제 계약 상태대로 설정합니다.
- 지수 막대는 LLM이 만들지 않습니다. 불쾌지수·계절별 체감온도는 관측값과 공개 산식으로 서버가 계산하고, 왼쪽 패널의 습도·풍속은 기상청 관측값을 그대로 표시합니다.
- 습도·풍속은 왼쪽 현재 날씨 패널에서만 표시합니다. 오른쪽에는 불쾌지수·체감온도와 API허브의 지역별 현재 특보를 표시하며, 특보를 임의 점수로 환산하지 않습니다.

API허브 배포 순서:

1. API허브에서 인증키를 발급합니다.
2. 동네예보의 `초단기실황조회`, `초단기예보조회`, `단기예보조회`를 활용 신청합니다.
3. 중기예보의 `중기기온조회`, `중기육상예보조회`와 기상특보의 `특보현황 조회`를 활용 신청합니다.
4. `KMA_API_HUB_AUTH_KEY`를 설정하고 실황·초단기·7일 주간예보·특보 스모크 테스트를 실행합니다.
5. 성공한 뒤에만 `KMA_API_HUB_SERVICES_CONFIRMED=true`로 설정합니다.

### 국립중앙도서관 국가서지 LOD 도서 검색

1. 공공데이터포털에서 **문화체육관광부 국립중앙도서관_서지 정보 제공 서비스**를 활용 신청합니다.
2. 개발계정은 자동승인 후 일반 인증키(Decoding)를 확인합니다.
3. 루트 `.env`에 `NLK_BIBLIO_SERVICE_KEY`를 설정합니다.
4. 운영 전 `python manage.py check`에서 `mybook.W001`이 사라졌는지 확인합니다.

도서 후보는 국가서지 LOD 기반 REST API의 `/getbookList_v2`만 사용합니다. 개인 프로필은 보내지 않고 AI가 만든 일반 표제명 검색어만 전달합니다. 복합 검색어와 개인화 핵심어 결과를 함께 비교하고, ISBN이 유효하며 RDF 자료유형이 `Book`인 비학위 일반 단행본만 허용합니다. 제목·주제의 개인화 일치도와 발행연도를 함께 평가한 뒤 중복 ISBN·동일 제목 판본을 제거합니다. 최종 선정된 3권의 표지는 ISBN 서지정보 API의 공식 `TITLE_URL`로만 보강하며, 표지 조회는 3초 제한·병렬 처리·성공 7일/미존재 6시간 공동 캐시를 적용합니다. 표지 API 장애는 추천을 실패시키지 않고 UI 대체 표지로 전환합니다. 429/5xx 응답은 짧은 지수 백오프로 제한 재시도하며, 장애 응답은 빈 추천으로 캐시하지 않습니다. 강제 새로고침 실패 시 검증된 이전 캐시가 있으면 이를 명시적으로 표시하고, 캐시가 없으면 재시도 가능한 503을 반환합니다. 기존 NAVER 도서 API 환경변수와 호출 경로는 사용하지 않습니다.

## 검증 상태 (2026-07-02)

- `manage.py check` 통과, 미적용 마이그레이션 없음
- `manage.py test chat` — 9개 테스트 통과 (부가 API 3 + v6 플로우 6)
- LLM 실호출 경로(chat_turn 전체)는 스모크 테스트 필요

## 삭제/보관된 것

- `views_v6.py`/`urls_v6.py` → `views.py`/`urls.py`로 병합 (`_archive/backend_merged/` 보관)
- send_message·stream_tts·이너카운슬·차/BGM 추천·👍👎 피드백(MLOps) → 기능 제거 (레포 루트 `_archive/README.md` 참조)

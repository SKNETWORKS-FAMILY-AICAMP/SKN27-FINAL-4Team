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

### MBTI 월간 자동 분석

Docker Compose에서는 `mbti-scheduler`가 매월 1일 00:05(Asia/Seoul)에 직전 월의
분석 후보를 `mbti_monthly_analysis_jobs`에 등록하고, `mbti-worker`가 한 번에
하나씩 처리합니다. 컨테이너가 월초 이후 재기동되어도 시작 시 직전 월을 한 번
확인하며, 입력 해시가 같은 작업은 다시 LLM을 호출하지 않습니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.mbti.yml up -d --build
```

외부 cron을 사용하는 배포 환경에서는 다음 one-shot 명령을 매월 1일에 실행하고,
worker 명령은 상시 프로세스로 운영합니다.

```bash
python manage.py schedule_mbti_monthly
python manage.py run_mbti_monthly_worker
```

수동 검증에는 `--period-key YYYY-MM`와 `--once`를 사용할 수 있습니다.

```bash
python manage.py schedule_mbti_monthly --period-key 2026-06
python manage.py run_mbti_monthly_worker --once
```

## 필요한 .env 키

| 키 | 필수 | 비고 |
|---|---|---|
| `OPENAI_API_KEY` | Y | LLM (기본 공급자 — 2026-07-02 OpenAI로 확정) |
| `OPENAI_MODEL` | N | 기본 `gpt-5.4-mini` |
| `LLM_PROVIDER` | N | `openai`(기본) / `groq` — groq 쓸 땐 `GROQ_API_KEY` 필요 |
| `PG_*` | Y | PostgreSQL 접속 (docker면 자동) |
| `OPENAI_API_KEY` (TTS 겸용) · `OPENAI_AUDIO_MODEL`(기본 `gpt-audio`) · `TTS_PROVIDER`(`openai`/`off`) | N | TTS는 OpenAI gpt-audio 사용(2026-07-19 확정, ElevenLabs·Typecast 은퇴). 키 없거나 `off`면 TTS만 failed, 대화는 정상 |
| `KAKAO_REST_API_KEY` | 마이페이지 도서 | Kakao Daum 책 검색의 후보·책 소개·서지정보·상세 링크·표지 조회. 미설정 시 소셜 로그인용 `KAKAO_CLIENT_ID`를 재사용 |
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
| `KMA_LIFE_INDEX_SERVICE_KEY` | 자외선지수 | 공공데이터포털의 `기상청_생활기상지수 조회서비스(3.0)` 활용신청 키. 미설정 시 같은 서비스에 승인된 `KMA_API_KEY` 재사용 |
| `KMA_LIFE_INDEX_SERVICE_CONFIRMED` | 운영 필수 | `getUVIdxV5` 실호출 성공 후 `true` |
| `KMA_UV_INDEX_ENDPOINT` | N | 기본 공공데이터포털 `LivingWthrIdxServiceV5/getUVIdxV5` 주소 |
| `KMA_WEEKLY_CACHE_SECONDS` | N | 단기·중기 7일 예보 공동 캐시, 기본 10,800초(3시간) |
| `KMA_WARNING_CACHE_SECONDS` | N | 전국 현재 특보현황 공동 캐시, 기본 300초 |

> .env는 레포 루트 하나로 통합. docker와 로컬 runserver 모두 루트 `.env`를 읽음.

### 날씨 API 배포 기준 (2026-07-15 확인)

- 실황·예보·특보 데이터는 기상청 API허브로 단일화했습니다. `getUltraSrtNcst`, `getUltraSrtFcst`, `getVilageFcst`, `getMidTa`, `getMidLandFcst`, `wrn_now_data.php`가 하나의 `KMA_API_HUB_AUTH_KEY`를 사용합니다. API허브 일반회원 한도는 일 20,000건·5GB입니다.
- 자외선지수는 관측값으로 추정하지 않습니다. 공공데이터포털의 기상청 생활기상지수 V5 `getUVIdxV5` 공식 발표값만 사용하며, 별도 활용신청 키가 없거나 값이 없으면 `정보 없음`으로 표시합니다.
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

자외선지수 배포 순서:

1. 공공데이터포털에서 `기상청_생활기상지수 조회서비스(3.0)`를 별도로 활용 신청합니다.
2. 승인된 키를 `KMA_LIFE_INDEX_SERVICE_KEY`에 설정하거나, 기존 `KMA_API_KEY`에 해당 서비스 승인을 추가합니다.
3. `getUVIdxV5` 실호출 성공을 확인한 뒤 `KMA_LIFE_INDEX_SERVICE_CONFIRMED=true`로 설정합니다.

### Kakao Daum 책 검색 기반 추천

1. Kakao Developers 앱의 REST API 키를 확인합니다.
2. 루트 `.env`에 `KAKAO_REST_API_KEY`를 설정합니다. 소셜 로그인과 같은 앱이면 `KAKAO_CLIENT_ID`도 재사용할 수 있습니다.
3. 운영 전 `python manage.py check`에서 `mybook.W001`이 사라졌는지 확인합니다.

도서 후보·책 소개·서지정보·상세 링크·표지는 Kakao Daum 책 검색 API로 단일화합니다. AI가 오늘의 감정, 관심사, 취미별로 대표 검색 의도와 2~4개의 서점 검색어를 만들고, 각 검색어의 Kakao 후보를 합쳐 ISBN과 동일 제목을 중복 제거합니다. 전날 또는 같은 날 직전 추천 ISBN은 테마별로 제외합니다. AI는 후보의 제목과 책 소개뿐 아니라 저자, 번역자, 출판사, 출간일, ISBN, 가격, 판매상태, 검색어 일치 맥락을 함께 비교해 최종 한 권과 장르, 추천사를 작성합니다. 사용자 프로필 원문은 Kakao에 보내지 않고 AI가 만든 검색어만 전달합니다. 429/5xx 응답은 짧은 지수 백오프로 제한 재시도하며, 강제 새로고침 실패 시 검증된 이전 캐시가 있으면 이를 명시적으로 표시하고 캐시가 없으면 재시도 가능한 503을 반환합니다.

## 검증 상태 (2026-07-02)

- `manage.py check` 통과, 미적용 마이그레이션 없음
- `manage.py test chat` — 9개 테스트 통과 (부가 API 3 + v6 플로우 6)
- LLM 실호출 경로(chat_turn 전체)는 스모크 테스트 필요

## 삭제/보관된 것

- `views_v6.py`/`urls_v6.py` → `views.py`/`urls.py`로 병합 (`_archive/backend_merged/` 보관)
- send_message·stream_tts·이너카운슬·차/BGM 추천·👍👎 피드백(MLOps) → 기능 제거 (레포 루트 `_archive/README.md` 참조)

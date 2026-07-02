# DevSpec - 마이페이지/설정/관리자

## 1. 목적과 범위

본 문서는 마이페이지, 개인 분석, 설정, 관리자 기능을 Django 기준으로 구현하기 위한 개발 명세다.

기준 문서:

- `요구사항정의서_v8.xlsx`
- `[화면설계서] 마이페이지 (한재웅) — 웹.html`
- `ERD_MY_설정_관리자_insert_only_v0.9.1.md`
- `시퀀스다이어그램_MY_설정_관리자_v0.9.1.md`
- `MBTI_성향추정_프로세스_흐름_보고서.md`

본 범위에서 직접 생성하거나 갱신하는 데이터는 마이페이지/설정/관리자 insert-only ERD에 정의된 테이블이다. 다른 담당자가 소유한 사용자, 온보딩, 대화, 마음리포트, 감정 분석, 안전 이벤트 원천 테이블은 조회 또는 외부 모듈 API 호출로만 사용한다.

## 2. Django 앱 구성

권장 앱 구조는 다음과 같다.

```text
apps/
  mypage/
    profile          # 프로필 확장 정보, 마이페이지 메인
    analysis         # MBTI/취향 분석 결과 조회, 분석 작업 등록
  settings_user/     # 언어/테마/접근성, 세션 관리, 차단, 탈퇴
  admin_ops/         # 관리자 KPI, 회원 상태, 안전/오류/신고, 콘텐츠/공지
  integrations/      # 외부 원천 테이블/API 어댑터
```

외부 원천은 모델을 중복 정의하지 않는다. 필요하면 `integrations` 계층에서 read-only repository 또는 API client로 감싼다.

## 3. 외부 참조 데이터

| 영역 | 참조 대상 | 사용 방식 |
| --- | --- | --- |
| 회원/인증 | `USERS`, `OAUTH_ACCOUNTS`, `USER_SESSIONS` | 사용자 식별, 계정 기본 정보, 세션 조회/종료 |
| 온보딩 | `USER_ONBOARDING_PROFILES`, `PERSONAS`, `CHARACTERS` | 프로필 조회, 캐릭터/닉네임 표시 |
| 대화 | `CONVERSATIONS`, `CHAT_SESSION`, `CHAT_MESSAGE`, `MESSAGE` | MBTI/취향 분석 입력 발화 조회 |
| 감정/척도 | `EMOTION_ANALYSIS_RESULTS`, `ANALYSIS`, `HIDDEN_SCALE_LOG` | 분석 보조 참고, 관리자 오류 확인 |
| 리포트/카드 | `MIND_REPORT`, `RESULT_CARD`, `FORTUNE_CARDS` | 보관함 연결, 관리자 콘텐츠 참조 |
| 안전 | `SAFETY_EVENT`, `SAFETY_CHECK_RESULTS`, `CRISIS_PROTOCOL_LOGS` | 관리자 안전 이벤트 확인 |

## 4. 내부 테이블

### 4.1 프로필/설정

| 테이블 | 역할 |
| --- | --- |
| `USER_PROFILE_EXTENSIONS` | 온보딩 원천 외 마이페이지 확장 프로필 |
| `USER_PROFILE_KEYWORDS` | 나를 표현하는 키워드 정렬 저장 |
| `USER_SETTINGS` | 언어, 테마, 글자 크기, 모션 최소화, 고대비 |
| `USER_SETTING_CHANGE_LOGS` | 설정 즉시 반영 성공/실패/권한 오류 이력 |
| `USER_BLOCKED_USERS` | 커뮤니티/채팅 차단 사용자 |
| `ACCOUNT_DELETION_REQUESTS` | 탈퇴 요청 |
| `DATA_DELETION_TASKS` | 도메인별 삭제 작업 상태 |

### 4.2 개인 분석

| 테이블 | 역할 |
| --- | --- |
| `MY_ANALYSIS_RUNS` | MBTI/취향 분석 실행 단위 |
| `MY_MBTI_AXIS_RESULTS` | 4축별 양방향 확률과 선택 글자 |
| `MY_MBTI_REPORTS` | 최종 유형, 신뢰도, 방사형 그래프, 근거 리포트 |
| `MY_TASTE_ANALYSIS_SUMMARIES` | 최근 관심사/선호 경향/변화 추이 화면용 JSON |
| `MY_PREFERENCE_INSIGHTS` | 키워드별 근거, 빈도, 추이, confidence |

### 4.3 관리자

| 테이블 | 역할 |
| --- | --- |
| `ADMIN_USERS` | 관리자 계정 |
| `ADMIN_AUDIT_LOGS` | 관리자 주요 작업 이력 |
| `USER_STATUS_CHANGE_LOGS` | 회원 상태 변경 이력 |
| `SAFETY_EVENT_REVIEW_LOGS` | 안전 이벤트 확인 이력 |
| `ANALYSIS_ERROR_REVIEW_LOGS` | 분석/리포트 오류 확인 이력 |
| `COMMUNITY_REPORT_REVIEW_LOGS` | 게시글/댓글/채팅 신고 처리 이력 |
| `SERVICE_CONTENT_ITEMS` | 운세/결과카드 문구/안전 안내 콘텐츠 |
| `SERVICE_ANNOUNCEMENTS` | 공지/점검 안내 |
| `SERVICE_METRIC_SNAPSHOTS` | 관리자 대시보드 KPI 스냅샷 |

## 5. API 명세

URL은 Django REST Framework 기준 예시다. 프로젝트 라우팅 규칙에 맞춰 prefix는 조정 가능하다.

### 5.1 마이페이지

| Method | URL | 설명 |
| --- | --- | --- |
| `GET` | `/api/mypage/` | 정적 방 메뉴, 사용자 표시명, 리포트 존재 여부 |
| `GET` | `/api/mypage/profile/` | 온보딩 원천 + 확장 프로필 조회 |
| `PATCH` | `/api/mypage/profile/` | 수정 가능한 확장 프로필 저장 |
| `GET` | `/api/mypage/report-entry/` | 마음리포트 보관함 진입 상태 조회 |

`GET /api/mypage/` 응답 예시:

```json
{
  "user": {"display_name": "한마음"},
  "menu": [
    {"id": "profile", "label": "프로필 조회", "url": "/mypage/profile"},
    {"id": "mbti", "label": "MBTI 분석", "url": "/mypage/mbti"},
    {"id": "taste", "label": "취향 분석", "url": "/mypage/taste"},
    {"id": "reports", "label": "리포트 보관함", "url": "/reports"},
    {"id": "settings", "label": "설정", "url": "/settings"}
  ],
  "fallback_menu_enabled": true
}
```

### 5.2 개인 분석

| Method | URL | 설명 |
| --- | --- | --- |
| `GET` | `/api/mypage/analysis/mbti/` | MBTI 화면 데이터 조회 |
| `POST` | `/api/mypage/analysis/mbti/refresh/` | MBTI 분석 작업 등록 |
| `GET` | `/api/mypage/analysis/taste/` | 취향 분석 화면 데이터 조회 |
| `POST` | `/api/mypage/analysis/taste/refresh/` | 취향 분석 작업 등록 |

분석 화면 조회는 먼저 최신 `MY_ANALYSIS_RUNS`를 조회한다. 결과가 없거나 만료되면 작업을 등록하고 `status=preparing` 또는 `unavailable` 응답을 내려준다.

MBTI 응답 예시:

```json
{
  "status": "completed",
  "period_label": "최근 30일 기준",
  "estimated_type": "INFP",
  "confidence_score": 0.72,
  "confidence_label": "medium",
  "display_axes": [
    {"label": "I", "score": 0.68},
    {"label": "N", "score": 0.61},
    {"label": "F", "score": 0.57},
    {"label": "P", "score": 0.64}
  ],
  "report": [
    "외향성: 사람/약속 언급 빈도 높음",
    "직관: 미래 시나리오 탐색 표현 반복",
    "감정: 상대 감정 고려 표현 많음",
    "인식: 선택지를 열어두는 경향"
  ],
  "caution": "비의료 참고 정보입니다."
}
```

취향 응답 예시:

```json
{
  "status": "completed",
  "interest_keywords": ["산책", "음악", "관계", "영화"],
  "preference_keywords": ["차분한 대화", "추천 반응", "짧은 계획"],
  "trend_items": [
    {"keyword": "음악", "delta": 0.18},
    {"keyword": "산책", "delta": 0.12},
    {"keyword": "관계", "delta": -0.06}
  ],
  "notice": null
}
```

분석 불가 응답 예시:

```json
{
  "status": "unavailable",
  "unavailable_reason": "최근 30일 내 의미 있는 사용자 발화가 5개 미만입니다.",
  "next_refresh_condition": "일반 대화가 5개 이상 쌓이면 다시 분석됩니다."
}
```

### 5.3 설정

| Method | URL | 설명 |
| --- | --- | --- |
| `GET` | `/api/settings/` | 계정 기본 정보와 설정값 조회 |
| `PATCH` | `/api/settings/ui/` | 언어/테마/접근성 저장 |
| `POST` | `/api/settings/reset/` | 설정값 기본값 복원 |
| `GET` | `/api/settings/sessions/` | 최근 세션 목록 조회 |
| `POST` | `/api/settings/sessions/{session_id}/revoke/` | 세션 종료 요청 |
| `GET` | `/api/settings/blocked-users/` | 차단 사용자 목록 |
| `POST` | `/api/settings/blocked-users/` | 사용자 차단 |
| `DELETE` | `/api/settings/blocked-users/{blocked_user_id}/` | 차단 해제 |
| `POST` | `/api/settings/account-deletion/` | 탈퇴 요청 |

설정 변경은 성공/실패 여부와 관계없이 `USER_SETTING_CHANGE_LOGS`에 기록한다.

### 5.4 관리자

| Method | URL | 설명 |
| --- | --- | --- |
| `GET` | `/api/admin/dashboard/` | KPI와 관리자 메인 데이터 |
| `GET` | `/api/admin/users/` | 회원 목록 조회/검색 |
| `POST` | `/api/admin/users/{user_id}/status/` | 회원 상태 변경 |
| `GET` | `/api/admin/safety-events/` | 안전 이벤트 목록 |
| `POST` | `/api/admin/safety-events/{event_id}/review/` | 안전 이벤트 확인 |
| `GET` | `/api/admin/analysis-errors/` | 분석/리포트 오류 목록 |
| `POST` | `/api/admin/analysis-errors/{job_id}/review/` | 오류 확인 이력 저장 |
| `GET` | `/api/admin/community-reports/` | 신고 목록 |
| `POST` | `/api/admin/community-reports/{report_id}/review/` | 신고 처리 |
| `GET` | `/api/admin/content-items/` | 콘텐츠 목록 |
| `POST` | `/api/admin/content-items/` | 콘텐츠 등록 |
| `PATCH` | `/api/admin/content-items/{content_item_id}/` | 콘텐츠 수정/비활성화 |
| `GET` | `/api/admin/announcements/` | 공지/점검 목록 |
| `POST` | `/api/admin/announcements/` | 공지/점검 등록 |
| `GET` | `/api/admin/audit-logs/` | 작업 이력 조회 |

관리자 API는 일반 사용자 인증과 분리하고, 모든 쓰기 작업은 `ADMIN_AUDIT_LOGS`를 남긴다.

## 6. 서비스 로직

### 6.1 마이페이지 메인

1. 세션에서 `user_id`를 확인한다.
2. 외부 원천에서 사용자명, 캐릭터/페르소나, 리포트 존재 여부를 조회한다.
3. 화면설계서의 5개 메뉴를 반환한다.
4. 이미지 로딩 실패나 작은 화면에서는 동일 기능을 목록/그리드 메뉴로 제공한다.
5. 별도 insert는 하지 않는다.

### 6.2 프로필

1. 온보딩 원천에서 이름, 캐릭터, 닉네임, 온보딩 MBTI를 조회한다.
2. `USER_PROFILE_EXTENSIONS`에서 성별, 출생연도, 현재 상태, 관심/취미를 조회한다.
3. `USER_PROFILE_KEYWORDS`에서 키워드를 정렬 조회한다.
4. 수정 요청 시 온보딩 원천과 충돌하지 않는 항목만 저장한다.
5. 저장 후 개인화 모듈에 갱신 이벤트를 보낸다.

### 6.3 MBTI 분석

1. 최근 기간의 일반 자유형 사용자 발화를 조회한다.
2. 의미 있는 발화가 최소 기준 미만이면 `MY_ANALYSIS_RUNS.status=unavailable`로 저장한다.
3. 발화를 전처리하고 임베딩한다.
4. pooled embedding을 4축 ML 모델에 입력한다.
5. `ei_score`, `ns_score`, `ft_score`, `jp_score`를 기준으로 양방향 확률을 계산한다.
6. 각 축에서 우세 글자를 선택해 최종 MBTI 문자열을 만든다.
7. 선택된 4글자의 우세 확률로 방사형 그래프 데이터를 만든다.
8. RAG로 축별 근거 발화를 검색한다.
9. LLM으로 3~4줄 근거 리포트를 생성한다.
10. 정책 필터로 진단/확정/낙인 표현을 제거한다.
11. `MY_ANALYSIS_RUNS`, `MY_MBTI_AXIS_RESULTS`, `MY_MBTI_REPORTS`에 저장한다.

### 6.4 취향 분석

1. 최근 기간과 비교 기간의 사용자 발화를 조회한다.
2. 최소 발화 수 또는 비교 기간이 부족하면 분석 불가 상태를 저장한다.
3. LLM 구조화 추출로 관심 주제, 선호 표현, 감정 반응, 콘텐츠 취향을 추출한다.
4. 키워드별 `confidence`, `mention_count`, `evidence_message_ids`를 만든다.
5. 이전 기간 대비 언급 비율 변화로 `trend_delta`를 계산한다.
6. 화면용 `interest_keywords_json`, `preference_keywords_json`, `trend_items_json`을 만든다.
7. `MY_ANALYSIS_RUNS`, `MY_TASTE_ANALYSIS_SUMMARIES`, `MY_PREFERENCE_INSIGHTS`에 저장한다.

### 6.5 설정

1. 계정 기본 정보는 외부 원천에서 조회만 한다.
2. 언어, 테마, 글자 크기, 모션 최소화, 고대비는 `USER_SETTINGS`에 저장한다.
3. 설정 변경 결과는 `USER_SETTING_CHANGE_LOGS`에 기록한다.
4. 세션 종료는 `USER_SESSIONS` 원천 모듈에 요청하고, 처리 이력만 로그로 남긴다.
5. 차단 사용자는 `USER_BLOCKED_USERS`에 저장하고, 해제 시 `unblocked_at`을 갱신한다.
6. 탈퇴 요청은 `ACCOUNT_DELETION_REQUESTS`를 만들고, 삭제 대상별로 `DATA_DELETION_TASKS`를 생성한다.

### 6.6 관리자

1. 관리자 인증은 일반 사용자 인증과 분리한다.
2. 대시보드 진입 시 KPI 원천을 집계하고 `SERVICE_METRIC_SNAPSHOTS`를 저장한다.
3. 회원 목록은 `USERS`를 조회하되 개인정보는 마스킹한다.
4. 회원 상태 변경은 외부 원천에 요청하고 `USER_STATUS_CHANGE_LOGS`, `ADMIN_AUDIT_LOGS`를 저장한다.
5. 안전 이벤트 확인은 원천 이벤트를 수정하지 않고 `SAFETY_EVENT_REVIEW_LOGS`를 저장한다.
6. 분석 오류 확인은 민감 원문 없이 `ANALYSIS_ERROR_REVIEW_LOGS`를 저장한다.
7. 신고 처리는 커뮤니티 원천 상태 변경을 요청하고 `COMMUNITY_REPORT_REVIEW_LOGS`를 저장한다.
8. 콘텐츠/공지 등록·수정은 검증 후 `SERVICE_CONTENT_ITEMS`, `SERVICE_ANNOUNCEMENTS`에 저장한다.

## 7. 권한과 보안

| 대상 | 정책 |
| --- | --- |
| 일반 사용자 API | 본인 `user_id` 데이터만 접근 가능 |
| 관리자 API | 관리자 인증과 role 확인 필수 |
| 관리자 회원 조회 | 개인정보 기본 마스킹 |
| 관리자 안전/오류 조회 | 원본 대화, 개인 민감 분석값 비노출 |
| 개인 분석 결과 | 비의료 참고 정보 문구 필수 |
| 탈퇴/초기화/세션 종료 | 확인 절차 필수 |
| 설정 변경 | 성공/실패/권한 오류 로그 기록 |

## 8. 상태값

### 8.1 분석 상태

```text
completed
unavailable
failed
preparing
```

`preparing`은 API 응답용 상태이며, DB에는 작업 등록 방식에 따라 `generation_status` 또는 별도 queue 상태로 관리할 수 있다.

### 8.2 신뢰도

```text
high
medium
low
```

초기 기준:

```text
high   = 평균 우세 확률 70% 이상이고 모든 축이 60% 이상
medium = 의미 있는 발화 수가 충분하고 대부분 축이 55% 이상
low    = 의미 있는 발화 수 부족 또는 55% 미만 경계 축 2개 이상
```

### 8.3 관리자 처리 상태

```text
pending
confirmed
closed
retry_needed
ignored
resolved
hidden
rejected
kept
needs_review
```

## 9. 배치/워커

개인 분석은 웹 요청에서 동기 실행하지 않는다.

권장 구조:

```text
분석 화면 진입
-> 최신 결과 조회
-> 결과 없음/만료 시 queue job 생성
-> Worker 실행
-> DB 저장
-> 화면 재조회 또는 polling
```

작업 idempotency 기준:

- 같은 `user_id`, `analysis_type`, `period_start`, `period_end` 조합의 진행 중 작업이 있으면 중복 등록하지 않는다.
- 최신 completed 결과가 있고 만료 기준을 넘지 않으면 새 작업을 만들지 않는다.
- failed 작업은 재시도 가능하되, 실패 사유를 남긴다.

## 10. 화면별 수용 기준

| 화면 | 수용 기준 |
| --- | --- |
| `F-MY-001` | 방 일러스트, 번호 마커, 하단 범례, 대체 메뉴, 재시도 안내 제공 |
| `F-MY-002` | 온보딩 원천 + 확장 프로필이 한 화면에 표시되고 항목별 수정 가능 |
| `F-MY-003` | 보관함 데이터 있음/없음/오류 상태를 구분 |
| `F-MY-004` | MBTI, 신뢰도, 방사형 그래프, 근거 리포트, 비의료 안내 표시 |
| `F-MY-005` | 최근 관심사, 선호 경향, 변화 추이, 데이터 부족 안내 표시 |
| `F-SET-001~007` | 설정 변경 즉시 반영, 실패/권한 오류 토스트, 초기화/탈퇴 확인 절차 |
| `F-ADM-001~002` | KPI, 회원 목록, 상태 변경 이력, 감사 로그 |
| `F-ADM-003~005` | 안전/오류/신고 상태 확인, 원문 비노출, 처리 이력 저장 |
| `F-ADM-006~008` | 콘텐츠/공지 등록, 검증, 비활성화, 작업 이력 조회 |

## 11. 1차 개발 우선순위

기준일은 2026-06-22이며, 1차 완료 목표일은 2026-07-10이다. 팀 차원의 Docker Compose, DB, Django 기본 구조는 2026-06-24부터 준비되는 것으로 가정한다. 따라서 2026-06-22 ~ 2026-06-23은 인프라 없이도 바로 만들 수 있는 분석 계약, 화면 응답 JSON, 프롬프트, 더미 데이터, 순수 함수 구현을 우선한다.

1차 범위는 반드시 마이페이지와 관리자페이지가 실제 화면에서 동작하는 상태를 목표로 한다. 커뮤니티페이지 자체 구현은 1차 이후로 미룰 수 있으며, 1차에서는 관리자 신고 처리 화면이 원천 API 또는 더미 데이터로 흐름만 확인되면 충분하다.

개발 방식은 Codex 기반 바이브코딩을 적극 활용한다. 먼저 화면/API/모델의 얇은 수직 슬라이스를 빠르게 만들고, 동작 확인 결과를 보면서 명세, 예외 처리, 테스트를 보강한다.

### 11.1 우선순위 기준

| 우선순위 | 기준 | 포함 범위 |
| --- | --- | --- |
| `P0` | 7월 10일 1차 시연에 없으면 안 되는 기능 | 마이페이지, MBTI/취향 MVP 표시, 관리자 대시보드/회원 관리 |
| `P1` | 복잡한 백엔드 없이도 화면 흐름을 완성해야 하는 기능 | 설정 화면, 관리자 콘텐츠/공지/로그, 신고/오류 확인 화면 |
| `P2` | 1차 이후 고도화 가능 | 커뮤니티페이지 본 구현, GraphRAG, DL fine-tuning, 고급 운영 지표 |

### 11.2 1차 필수 범위

| 영역 | 1차 목표 | 구현 방식 |
| --- | --- | --- |
| 마이페이지 메인 | 방 화면, 메뉴 진입, 사용자명 표시 | 실제 API + 부족한 원천은 adapter 더미 응답 허용 |
| 프로필 | 온보딩 원천 + 확장 프로필 조회/수정 | `USER_PROFILE_EXTENSIONS`, `USER_PROFILE_KEYWORDS` 우선 구현 |
| MBTI 분석 | 추정 유형, 신뢰도, 방사형 그래프, 근거 리포트 표시 | 보고서의 MVP 방식인 `Embedding + ML + Vector RAG + LLM Report` 기준 |
| 취향 분석 | 최근 관심사, 선호 경향, 변화 추이, 데이터 부족 안내 표시 | LLM 구조화 추출 또는 규칙 기반 임시 추출로 화면 JSON 우선 생성 |
| 설정 | 언어/테마/글자 크기/접근성 변경 | 복잡한 계정 백엔드 없이 `USER_SETTINGS` 저장과 토스트 확인 우선 |
| 관리자 대시보드 | KPI 카드, 회원 목록, 상태 변경 | 원천 집계가 미완성인 항목은 mock snapshot으로 시작 |
| 관리자 처리 화면 | 안전/오류/신고 목록 확인, 처리 이력 저장 | 원문 상세 노출 없이 review log insert 중심 |

### 11.3 06-22 ~ 06-23 선행 작업

이 기간에는 Docker Compose, DB, Django 프로젝트 구조를 기다리지 않는다. 대신 프로세스 보고서의 MVP 흐름을 코드로 옮기기 쉬운 형태로 고정한다.

| 우선순위 | 작업 | 산출물 |
| --- | --- | --- |
| `P0` | MBTI 4축 확률 조합 규칙 구현 | `ei/ns/ft/jp score -> estimated_type, display_axes, confidence_label` 순수 함수 |
| `P0` | MBTI 화면 응답 계약 확정 | `GET /api/mypage/analysis/mbti/` 성공/분석중/분석불가 JSON 샘플 |
| `P0` | 취향 분석 화면 응답 계약 확정 | `GET /api/mypage/analysis/taste/` 성공/분석불가 JSON 샘플 |
| `P0` | 분석 샘플 데이터 작성 | 최근 30일 사용자 발화 샘플, 데이터 부족 샘플, 경계 축 샘플 |
| `P0` | RAG Anchor Query 정리 | EI/NS/FT/JP 양방향 anchor query와 Top-K 검색 입력 포맷 |
| `P1` | LLM 리포트 프롬프트 초안 | MBTI 근거 리포트 3~4줄, 금지 표현, 불확실성 표현 규칙 |
| `P1` | 취향 구조화 추출 프롬프트 초안 | 관심사/선호/변화추이 JSON schema와 근거 message_id 규칙 |
| `P1` | 관리자/설정 mock API 응답 작성 | 대시보드 KPI, 회원 목록, 설정값, review log 샘플 JSON |
| `P1` | 화면 상태 정의 | completed, preparing, unavailable, failed 별 표시 문구 |

선행 작업의 핵심은 `나중에 Django view나 worker 안에 그대로 넣을 수 있는 로직과 계약`을 만드는 것이다. 특히 MBTI 분석은 프로세스 보고서 기준으로 아래 순서가 흔들리지 않아야 한다.

```text
사용자 발화
-> 전처리/임베딩
-> 4개 ML binary classifier
-> EI/NS/FT/JP 기준 확률
-> 우세 글자 조합
-> 방사형 그래프 데이터
-> Vector RAG 근거 발화 검색
-> LLM 근거 리포트
-> 대시보드 JSON
```

오늘내일 작성할 순수 함수의 최소 입출력은 아래와 같다.

```json
{
  "input": {
    "ei_score": 0.32,
    "ns_score": 0.61,
    "ft_score": 0.57,
    "jp_score": 0.36,
    "source_message_count": 32
  },
  "output": {
    "estimated_type": "INFP",
    "confidence_score": 0.63,
    "confidence_label": "medium",
    "display_axes": [
      {"label": "I", "score": 0.68},
      {"label": "N", "score": 0.61},
      {"label": "F", "score": 0.57},
      {"label": "P", "score": 0.64}
    ]
  }
}
```

### 11.4 1차에서 축소 가능한 범위

| 기능 | 1차 처리 |
| --- | --- |
| 커뮤니티페이지 | 직접 구현하지 않는다. 관리자 신고 목록은 더미 또는 원천 API 계약 기준으로 표시한다. |
| 세션 관리 | 세션 목록 조회와 종료 버튼 UI만 우선 구현하고, 실제 세션 종료는 adapter로 분리한다. |
| 탈퇴/데이터 삭제 | 요청 생성과 상태 표시까지만 구현한다. 실제 도메인별 삭제 worker는 1차 이후 보강한다. |
| 관리자 콘텐츠 검수 | 등록/수정/비활성화 CRUD 중심으로 구현하고 승인 워크플로는 단순화한다. |
| 분석 모델 고도화 | DL fine-tuning, GraphRAG, 실제 사용자 검증셋 운영은 MVP+로 넘긴다. |
| RAGAS 자동 평가 | 1차에서는 평가 데이터셋 설계와 수동 샘플 검증까지만 두고, CI 자동화는 이후 적용한다. |

### 11.5 일정 계획

| 기간 | 목표 | 산출물 |
| --- | --- | --- |
| 06-22 ~ 06-23 | 인프라 독립 선행 작업 | 분석 순수 함수, JSON 계약, 프롬프트, mock 응답, 샘플 발화 |
| 06-24 ~ 06-25 | 프로젝트 뼈대와 DB 기준 반영 | Django app, model, migration, seed/mock adapter |
| 06-26 ~ 06-28 | 마이페이지 기본 흐름 완성 | 메인, 프로필, 설정 기본 API/화면 |
| 06-29 ~ 07-02 | 분석 MVP 연결 | MBTI/취향 조회 API, worker 또는 management command, 화면 JSON |
| 07-03 ~ 07-06 | 관리자페이지 1차 완성 | 대시보드, 회원 상태 변경, 안전/오류/신고 review log |
| 07-07 ~ 07-08 | 통합 연결과 예외 처리 | 권한, 빈 상태, 실패 토스트, 데이터 부족 안내 |
| 07-09 ~ 07-10 | 1차 시연 안정화 | 시연 시나리오, 테스트 체크리스트, 문서 갱신 |

### 11.6 Codex 바이브코딩 작업 단위

Codex 작업은 한 번에 큰 기능 전체를 맡기기보다 아래처럼 검증 가능한 단위로 쪼갠다.

| 작업 단위 | Codex에 맡길 내용 | 확인 기준 |
| --- | --- | --- |
| 분석 순수 함수 | 4축 확률 조합, confidence 계산, 화면 상태 변환 | Python 단위 테스트 통과 |
| API 계약 | MBTI/취향/설정/관리자 mock JSON 작성 | 프론트가 DB 없이 화면 연결 가능 |
| 프롬프트 | MBTI 리포트, 취향 구조화 추출 프롬프트 작성 | 샘플 발화로 금지 표현 없이 JSON/리포트 생성 |
| 모델/마이그레이션 | ERD 기반 Django model 생성 | migration 생성, admin 등록 또는 shell 조회 |
| API skeleton | DRF serializer/view/url 작성 | Swagger 또는 API 응답 확인 |
| 화면 연결 | 기존 화면설계서 기준 컴포넌트와 API 연결 | 빈 상태/성공 상태가 모두 보임 |
| 분석 MVP | 입력 발화 -> 결과 JSON 변환 파이프라인 | MBTI 4축 조합과 취향 키워드가 화면 포맷으로 저장 |
| 관리자 CRUD | 목록/상세/처리 API와 로그 저장 | 처리 후 review log와 audit log가 남음 |
| 테스트 보강 | 권한, 상태값, 분석 불가 케이스 테스트 | 핵심 API 테스트 통과 |

### 11.7 구현 순서

1. 인프라 독립 분석 순수 함수, JSON 계약, 프롬프트, mock 응답 작성
2. 모델/마이그레이션과 seed/mock 데이터 작성
3. 외부 원천 조회 adapter 작성
4. 마이페이지 메인/프로필 API와 화면 연결
5. 설정 API와 변경 로그 구현
6. 개인 분석 조회 API와 분석 결과 테이블 저장
7. MBTI/취향 MVP worker 또는 management command 작성
8. 관리자 인증/대시보드/회원 상태 변경 구현
9. 안전/오류/신고 처리 이력 구현
10. 콘텐츠/공지 관리 CRUD 구현
11. 통합 테스트, 시연 데이터, 문서 갱신

## 12. 테스트 체크리스트

- 일반 사용자는 다른 사용자의 프로필/분석/설정에 접근할 수 없다.
- 프로필 수정 시 온보딩 원천과 중복 저장 충돌이 없다.
- 분석 대상 발화 부족 시 `unavailable_reason`이 표시된다.
- MBTI 4축 확률이 최종 유형과 방사형 그래프 값으로 일관되게 변환된다.
- 취향 변화 추이는 비교 기간 부족 시 계산하지 않는다.
- 설정 변경 실패도 `USER_SETTING_CHANGE_LOGS`에 남는다.
- 탈퇴 요청 시 도메인별 삭제 작업이 생성된다.
- 관리자 화면에는 원본 대화와 개인 민감 분석값이 노출되지 않는다.
- 관리자 쓰기 작업은 모두 `ADMIN_AUDIT_LOGS`를 남긴다.
- 다른 담당자 소유 테이블은 중복 생성하지 않는다.

# 마이페이지/설정 시퀀스 다이어그램 v1.0

## 정리 기준

본 문서는 화면설계서, 요구사항정의서 v8, ERD 문서, `MBTI_질문에이전트_및_성향취향분석_파이프라인_보고서.md`를 기준으로 다시 정리한 시퀀스다.

핵심 기준은 다음과 같다.

- 다른 담당자가 소유한 `USERS`, `CONVERSATIONS`, `CHAT_MESSAGE`, `MIND_REPORT`, `RESULT_CARD`, `SAFETY_EVENT` 등은 직접 생성하지 않고 조회 또는 외부 모듈 호출로만 사용한다.
- 이 문서의 insert/update 대상은 ERD에 정의된 마이페이지/설정 테이블이다.
- 화면 흐름은 화면설계서의 `F-MY-001~005`, `F-SET-001~006` 구조를 따른다.
- 개인 분석은 사용자가 점수를 직접 계산하는 기능이 아니라, 화면 진입 시 저장 결과를 보여주고 필요 시 백그라운드에서 갱신하는 구조다.

## 1. 마이페이지 메인 진입

`F-MY-001`은 정적 방 일러스트와 기능 진입 동선이다. 별도 insert 대상은 없다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant Web as 웹 클라이언트
    participant Auth as 인증/계정
    participant My as 마이페이지 API
    participant Ext as 외부 원천 조회

    U->>Web: /mypage 진입
    Web->>Auth: 로그인 상태 확인
    Auth-->>Web: user_id 반환
    Web->>My: 마이페이지 메인 데이터 요청
    My->>Ext: 사용자명, 캐릭터, 리포트 존재 여부 조회
    Ext-->>My: 표시용 요약 데이터
    My-->>Web: 방 일러스트, 번호 마커, 하단 범례, 링크 대상
    Web-->>U: 프로필/MBTI/취향/리포트/설정 아티팩트 표시

    alt 작은 화면 또는 이미지 로딩 실패
        Web-->>U: 목록/그리드 대체 메뉴 또는 재시도 안내 표시
    end
```

## 2. 프로필 조회 및 항목 수정

프로필은 온보딩 원천 값을 기준으로 보여주되, 마이페이지에서 추가/수정해야 하는 확장 정보만 `USER_PROFILE_EXTENSIONS`, `USER_PROFILE_KEYWORDS`에 저장한다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant Web as 웹 클라이언트
    participant Profile as 프로필 API
    participant Onboard as 온보딩/사용자 원천
    participant DB as MyPage DB
    participant Personalize as 개인화 모듈

    U->>Web: 프로필 조회 화면 진입
    Web->>Profile: 프로필 항목 요청
    Profile->>Onboard: 이름, 캐릭터, 온보딩 MBTI, 닉네임 조회
    Profile->>DB: USER_PROFILE_EXTENSIONS, USER_PROFILE_KEYWORDS 조회
    Onboard-->>Profile: 원천 프로필 데이터
    DB-->>Profile: 확장 프로필, 키워드
    Profile-->>Web: 항목별 표시 데이터
    Web-->>U: 이름/캐릭터/MBTI/상태/키워드/관심/취미 표시

    opt 항목별 수정
        U->>Web: 수정값 입력
        Web->>Profile: 수정 요청
        Profile->>Profile: 온보딩 원천과 충돌 여부 검증
        alt 저장 가능
            Profile->>DB: USER_PROFILE_EXTENSIONS upsert
            Profile->>DB: USER_PROFILE_KEYWORDS replace/insert
            Profile->>Personalize: 대화 개인화 갱신 알림
            Profile-->>Web: 저장 완료
            Web-->>U: 변경값 즉시 반영
        else 저장 불가
            Profile-->>Web: 실패 사유
            Web-->>U: 수정 실패 안내
        end
    end
```

## 3. 리포트 보관함 연결

`F-MY-003`은 마음리포트 모듈로 들어가는 연결 동선이다. 보관함 테이블은 새로 만들지 않는다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant Web as 웹 클라이언트
    participant My as 마이페이지 API
    participant Report as 마음리포트 모듈

    U->>Web: 리포트 보관함 아티팩트 선택
    Web->>My: 보관함 진입 상태 요청
    My->>Report: 사용자 리포트 존재 여부 조회

    alt 리포트 있음
        Report-->>My: 보관함 진입 가능
        My-->>Web: 보관함 URL/상태 반환
        Web-->>U: 마음리포트 보관함으로 이동
    else 리포트 없음
        Report-->>My: 빈 상태
        My-->>Web: 빈 상태와 생성 유도 문구
        Web-->>U: 빈 상태 안내
    else 조회 실패
        Report-->>My: 오류
        My-->>Web: 오류와 재시도 정보
        Web-->>U: 재시도 안내
    end
```

## 4. 개인 분석 화면 공통 진입

`F-MY-004`, `F-MY-005`는 같은 진입 패턴을 쓴다. 화면은 최신 저장 결과를 먼저 조회하고, 결과가 없거나 만료되면 분석 작업을 등록한다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant Web as 웹 클라이언트
    participant API as 개인 분석 API
    participant DB as MyPage DB
    participant Queue as 분석 큐
    participant Worker as 분석 워커

    U->>Web: MBTI 또는 취향 분석 화면 진입
    Web->>API: 분석 화면 데이터 요청
    API->>DB: MY_ANALYSIS_RUNS 최신 row 조회

    alt 표시 가능한 최신 결과 있음
        DB-->>API: analysis_run + 화면용 결과
        API-->>Web: 대시보드 데이터
        Web-->>U: 분석 화면 표시
    else 결과 없음 또는 갱신 필요
        DB-->>API: 없음/만료
        API->>Queue: 분석 작업 등록
        API-->>Web: 준비 중 상태, 다음 갱신 조건
        Web-->>U: 준비 중 안내
        Queue-->>Worker: 백그라운드 분석 실행
    else 데이터 부족
        DB-->>API: 기준 미충족
        API-->>Web: unavailable_reason
        Web-->>U: 분석 불가 사유와 다음 갱신 조건 표시
    end
```

## 5. MBTI 질문 Q&A 축적

MBTI 질문은 별도 Trigger Agent 없이 `MBTI Question Agent` 하나가 `recent_context`를 보고 질문 가능 여부와 질문 생성을 함께 처리한다. 질문이 최종 챗봇 응답에 포함되고 사용자가 답변한 경우에만 MBTI 분석용 Q&A로 저장한다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant Chat as 챗봇 시스템
    participant Agent as MBTI Question Agent
    participant Source as 대화 원천 DB
    participant DB as MyPage DB

    U->>Chat: 일반 대화 입력
    Chat->>Agent: recent_context 전달
    Agent-->>Chat: should_ask, question, target_axis, question_intent

    alt should_ask = true
        Chat-->>U: 일반 응답 + MBTI 질문
        Chat->>Source: 질문 발화 저장
        U->>Chat: MBTI 질문에 대한 자연어 답변
        Chat->>Source: 사용자 답변 저장
        Chat->>DB: MY_MBTI_QUESTION_PROMPTS insert(question_message_id, answer_message_id)
    else should_ask = false
        Chat-->>U: MBTI 질문 없이 일반 응답
    end
```

## 6. MBTI 분석 워커

MBTI 분석은 일반 대화 전체가 아니라 `MBTI Question Agent`가 만든 질문과 사용자 답변 Q&A만 사용한다. 분석 흐름은 `Q&A 조회 -> LLM 근거 코딩 -> 서버 count 집계 -> 4축 비율 계산 -> RAG 근거 리포트` 순서로 저장된다.

```mermaid
sequenceDiagram
    participant Worker as MBTI 분석 워커
    participant QDB as MBTI QnA Store
    participant Chat as 대화 원천 모듈
    participant LLMCode as LLM 코딩 모듈
    participant Stats as 4축 집계
    participant Embed as 임베딩/VectorDB
    participant RAG as 근거 검색
    participant LLMReport as 리포트 생성기
    participant Policy as 표현 정책
    participant DB as MyPage DB

    Worker->>QDB: 최근 30일 MBTI 질문-답변 Q&A 조회
    QDB-->>Worker: question_prompt_id, question_message_id, answer_message_id 목록

    alt Q&A 없음
        Worker->>DB: MY_ANALYSIS_RUNS insert(status=unavailable, unavailable_reason)
    else 분석 가능
        loop 각 MBTI Q&A
            Worker->>Chat: 질문/답변 중심 맥락 조회
            Chat-->>Worker: question, answer, optional context
            Worker->>LLMCode: 질문+답변 맥락 기반 4축 근거 코딩
            LLMCode-->>Worker: axis, pole, keyword, evidence_span
            Worker->>DB: MY_MBTI_MESSAGE_EVIDENCE insert
            Worker->>Embed: 근거 답변 임베딩 저장
            Embed-->>Worker: VectorDB 저장 상태
        end

        Worker->>Stats: axis/pole별 evidence count 집계
        Stats-->>Worker: 4축 비율, 추정 MBTI
        Worker->>Worker: display_axes_json, axis_ratios_json 구성
        Worker->>RAG: 선택된 축 방향별 근거 발화 검색
        RAG-->>Worker: 근거 message_id, 발화 snippet
        Worker->>LLMReport: RAG 근거 기반 3~4줄 리포트 생성
        LLMReport-->>Worker: report_text 초안
        Worker->>Policy: 진단/확정/낙인 표현 제거
        Policy-->>Worker: 비의료 참고 문구 포함 최종 문장

        Worker->>DB: MY_ANALYSIS_RUNS insert(status=completed)
        Worker->>DB: MY_MBTI_AXIS_RESULTS insert(4축)
        Worker->>DB: MY_MBTI_REPORTS insert(estimated_type, axis ratios, RAG evidence, report)
    end
```

## 7. 취향 및 선호 분석 워커

취향 분석은 장문 리포트보다 화면설계서의 `최근 관심사`, `선호 경향`, `변화 추이`, `데이터 안내`를 만들기 위한 구조화 흐름이다.

```mermaid
sequenceDiagram
    participant Worker as 취향 분석 워커
    participant Chat as 대화 원천 모듈
    participant LLM as 구조화 추출기
    participant Stats as 기간별 집계
    participant Policy as 표현 정책
    participant DB as MyPage DB

    Worker->>Chat: 최근 30일 사용자 발화 조회
    Chat-->>Worker: 발화 목록, message_id

    alt 사용자 발화 부족
        Worker->>DB: MY_ANALYSIS_RUNS insert(status=unavailable, unavailable_reason)
        Worker->>DB: MY_TASTE_ANALYSIS_SUMMARIES insert(unavailable_reason)
    else 분석 가능
        Worker->>LLM: 주제, 선호 표현, 감정 반응, 콘텐츠 취향 구조화 추출
        LLM-->>Worker: keyword, category, polarity, evidence_message_ids
        Worker->>Stats: 키워드별 mention_count, score 계산
        Stats-->>Worker: mention_count, score
        Worker->>Policy: 과잉추론/진단 표현 제거
        Policy-->>Worker: 화면 표시 가능 키워드

        Worker->>DB: MY_ANALYSIS_RUNS insert(status=completed)
        Worker->>DB: MY_TASTE_ANALYSIS_SUMMARIES insert(interest/preference/trend json)
        Worker->>DB: MY_PREFERENCE_INSIGHTS insert(키워드별 근거)
    end
```

## 8. 설정 조회 및 변경

설정 화면은 계정 기본 정보 조회와 UI 설정 변경을 분리한다. 계정 원천값은 조회만 하고, 언어/테마/접근성은 `USER_SETTINGS`에 저장한다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant Web as 웹 클라이언트
    participant Settings as 설정 API
    participant Auth as 계정 원천
    participant DB as MyPage DB

    U->>Web: 설정 화면 진입
    Web->>Settings: 설정 화면 데이터 요청
    Settings->>Auth: 로그인 계정, 닉네임, 가입 방식, 가입일 조회
    Settings->>DB: USER_SETTINGS 조회
    Auth-->>Settings: 계정 기본 정보
    DB-->>Settings: 언어/테마/접근성 설정
    Settings-->>Web: 설정 화면 데이터
    Web-->>U: 좌측 카테고리와 우측 상세 패널 표시

    opt 언어/테마/접근성 변경
        U->>Web: 설정값 변경
        Web->>Settings: 저장 요청
        alt 저장 성공
            Settings->>DB: USER_SETTINGS upsert
            Settings->>DB: USER_SETTING_CHANGE_LOGS insert(success)
            Settings-->>Web: 저장 완료
            Web->>Web: 새로고침 없이 즉시 반영
            Web-->>U: 완료 토스트
        else 저장 실패 또는 권한 오류
            Settings->>DB: USER_SETTING_CHANGE_LOGS insert(failed/permission_error)
            Settings-->>Web: 실패 사유
            Web-->>U: 재시도/재로그인 안내
        end
    end

    opt 설정값 초기화
        U->>Web: 기본값 복원 선택
        Web-->>U: 초기화 대상과 복구 가능 여부 확인
        U->>Web: 확인
        Web->>Settings: 초기화 요청
        Settings->>DB: USER_SETTINGS 기본값 저장, reset_at 갱신
        Settings->>DB: USER_SETTING_CHANGE_LOGS insert(reset)
        Settings-->>Web: 초기화 완료
        Web->>Web: 현재 화면 즉시 반영
    end
```

## 요구사항 연결 요약

| 범위 | 핵심 시퀀스 | insert/update 테이블 |
| --- | --- | --- |
| `F-MY-001` | 마이페이지 메인 진입 | 없음 |
| `F-MY-002` | 프로필 조회/수정 | `USER_PROFILE_EXTENSIONS`, `USER_PROFILE_KEYWORDS` |
| `F-MY-003` | 리포트 보관함 연결 | 없음 |
| `F-MY-004` | MBTI 화면 진입, MBTI 워커 | `MY_MBTI_QUESTION_PROMPTS`, `MY_MBTI_MESSAGE_EVIDENCE`, `MY_ANALYSIS_RUNS`, `MY_MBTI_AXIS_RESULTS`, `MY_MBTI_REPORTS` |
| `F-MY-005` | 취향 화면 진입, 취향 워커 | `MY_ANALYSIS_RUNS`, `MY_TASTE_ANALYSIS_SUMMARIES`, `MY_PREFERENCE_INSIGHTS` |
| `F-SET-001~003`, `F-SET-005`, `NF-SET-001` | 설정 조회/변경/초기화 | `USER_SETTINGS`, `USER_SETTING_CHANGE_LOGS` |

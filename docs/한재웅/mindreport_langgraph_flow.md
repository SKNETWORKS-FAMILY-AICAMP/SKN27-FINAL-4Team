# 마음리포트 LangGraph 멀티에이전트 흐름

현재 `app/backend/mindreport/services` 구현을 기준으로 정리한 흐름이다.

## 전체 그래프

```mermaid
flowchart TD
    START(["리포트 생성 요청"]) --> SUP["마음리포트 그래프 오케스트레이터<br/>State 생성 및 그래프 실행"]
    SUP --> CRITERIA["데이터 수집·생성 기준 에이전트<br/>collect_and_check_criteria"]

    CRITERIA -->|"주간 5개 또는 월간 20개 충족"| EMOTION["감정 점수·흐름 분석 에이전트<br/>score_and_analyze_emotion"]
    CRITERIA -->|"기준 미충족"| FALLBACK["폴백 리포트<br/>fallback_report"]

    EMOTION -->|"분석 성공"| CAUSE["원인 후보 추출·분류 에이전트<br/>extract_and_classify_causes"]
    EMOTION -->|"분석 실패"| FALLBACK

    CAUSE -->|"원인 있음 또는 근거 있는 원인 없음"| NARRATIVE["근거 기반 서술·실천 제안 생성 에이전트<br/>generate_narrative_and_actions"]
    CAUSE -->|"에이전트 실행 실패"| FALLBACK

    NARRATIVE -->|"생성 성공"| VALIDATE["리포트 검증·재생성 라우팅 에이전트<br/>validate_report"]
    NARRATIVE -->|"생성 실패"| FALLBACK

    VALIDATE -->|"검증 통과"| FORMAT["프론트엔드 payload 변환<br/>format_report"]
    VALIDATE -->|"데이터·생성 기준 오류"| CRITERIA
    VALIDATE -->|"감정 점수·시계열 오류"| EMOTION
    VALIDATE -->|"원인 키워드 근거 오류"| CAUSE
    VALIDATE -->|"서술·분량·표현 오류"| NARRATIVE
    VALIDATE -->|"고위험 신호"| SAFETY["안전 응답<br/>safety_response"]
    VALIDATE -->|"재시도 소진 또는 복구 불가"| FALLBACK

    FORMAT --> COMPLETE(["정상 리포트 완료"])
    FALLBACK --> FALLBACK_END(["폴백 리포트 완료"])
    SAFETY --> SAFETY_END(["안전 응답 완료"])
```

## 에이전트 내부 처리

```mermaid
flowchart LR
    subgraph E["감정 점수·흐름 분석 에이전트"]
        E1["기간 내 사용자 대화"] --> E2["날짜별 대화 그룹"]
        E2 --> E3["LLM 정서 근거 분류<br/>긍정·부정·각성도"]
        E3 --> E4["서버의 0~100 내부 점수 계산"]
        E4 --> E5{"서로 다른 기록일 3일 이상?"}
        E5 -->|"아니요"| EI["시계열 근거 부족"]
        E5 -->|"예"| ET["Rule 기반 시계열 분석"]
        ET --> EU["상승"]
        ET --> ED["하락"]
        ET --> EV["변동"]
        ET --> EM["유지<br/>초록·회색·빨강"]
    end

    subgraph C["원인 후보 추출·분류 에이전트"]
        C1["원본 대화"] --> C2["후보 추출 LLM"]
        C2 -->|"명시적 인과·반복 연관·전후 변화"| C3["근거 후보"]
        C2 -->|"충분한 근거 없음"| C0["no_supported_candidates"]
        C3 --> C4["독립 분류 LLM<br/>원본 근거 메시지 재검토"]
        C4 --> CS["stress<br/>publishable=true"]
        C4 --> CR["relief<br/>publishable=true"]
        C4 --> CU["unresolved<br/>화면 미표시"]
        C0 --> CN["no_supported_causes"]
        CU --> CN
    end

    subgraph N["근거 기반 서술·실천 제안 생성 에이전트"]
        N1["대화 근거·검증된 원인·실천 방향"] --> N2["서술 생성 LLM"]
        N2 --> N3["짧은 제목·한 문장 요약"]
        N2 --> N4["근거 기반 분석 3개 이상"]
        N2 --> N5["이유와 시작 방법이 있는 실천 대안"]
        N2 --> N6["점수·내부 상태·직접 인용 비노출"]
    end

    E --> C
    C --> N
```

## 검증 및 재생성

```mermaid
flowchart TD
    INPUT["생성된 리포트와 Graph State"] --> DATA["데이터 검증"]
    DATA --> ANALYSIS["분석 검증"]
    ANALYSIS --> SAFETY["안전성 검증"]

    DATA -->|"기간·대화 집합·생성 기준 오류"| R1["데이터 수집·생성 기준 에이전트 재실행"]
    ANALYSIS -->|"감정 패턴·점수 불일치"| R2["감정 점수·흐름 분석 에이전트 재실행"]
    ANALYSIS -->|"키워드 근거 오류"| R3["원인 후보 추출·분류 에이전트 재실행"]
    ANALYSIS -->|"점수·상태 노출, 직접 인용, 얕은 내용"| R4["근거 기반 서술·실천 제안 생성 에이전트 재실행"]
    SAFETY -->|"고위험 신호"| RS["안전 응답 전환"]

    DATA -->|"통과"| PASS{"전체 검증 통과?"}
    ANALYSIS -->|"통과"| PASS
    SAFETY -->|"통과"| PASS
    PASS -->|"예"| FORMAT["최종 payload 생성"]
    PASS -->|"아니요·재시도 소진"| FALLBACK["폴백 리포트"]
```

## 프론트엔드 출력

정상 리포트 payload에는 다음 데이터가 포함된다.

- 짧은 제목과 한 문장 요약
- 날짜별 감정 얼굴
- 검증을 통과한 스트레스 원인
- 검증을 통과한 스트레스 이완 원인
- 근거를 간접적으로 풀어 쓴 분석 문단
- 구체적인 실천 대안
- 원인 근거가 없으면 빈 배열과 안내 문구

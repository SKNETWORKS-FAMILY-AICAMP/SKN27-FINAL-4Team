---
tags: [SKN27기, 최종프로젝트, 4팀, ERD, 챗봇, 이너카운슬, 개별]
담당: 김한솔
문서버전: v1.0
작성일: 2026-06-21
---

# 🗄️ [개별] ERD — 김한솔 (챗봇·이너카운슬)

> [!info] 문서 개요
> - **담당자**: 김한솔 (PM)
> - **범위**: 챗봇 대화·감정분석·척도추정·이너카운슬·메모리 관련 엔티티
> - **DB 구성**: PostgreSQL (관계형) + Neo4j (그래프 LTM)
> - **작성 포맷**: Mermaid erDiagram

---

## 1. 전체 ERD

```mermaid
erDiagram

    USER {
        uuid    user_id PK
        string  nickname
        string  oauth_provider
        string  oauth_id
        bool    is_secret_default
        bool    consent_sensitive
        int     intimacy_level
        int     acorn_count
        datetime created_at
        datetime deleted_at
    }

    CHAT_SESSION {
        uuid    session_id PK
        uuid    user_id FK
        string  character_id
        bool    is_secret
        int     total_turns
        datetime started_at
        datetime ended_at
        bool    is_inner_council_used
    }

    MESSAGE {
        uuid    message_id PK
        uuid    session_id FK
        string  role
        text    content
        int     turn_count
        int     char_count
        datetime created_at
    }

    EMOTION_ANALYSIS {
        uuid    analysis_id PK
        uuid    message_id FK
        string  emotion_code
        string  emotion_label
        float   confidence
        string  model_version
        int     inference_ms
        datetime analyzed_at
    }

    SCALE_SCORE {
        uuid    score_id PK
        uuid    session_id FK
        string  scale_type
        float   estimated_score
        float   session_vector
        bool    is_final
        datetime scored_at
    }

    LTM_MEMORY {
        uuid    memory_id PK
        uuid    user_id FK
        string  node_type
        string  keyword
        string  relation
        float   weight
        datetime created_at
        datetime deleted_at
    }

    INNER_COUNCIL_SESSION {
        uuid    council_id PK
        uuid    session_id FK
        int     total_turns
        int     total_tokens
        bool    force_stopped
        text    summary_card
        datetime started_at
        datetime ended_at
    }

    AGENT_TURN {
        uuid    turn_id PK
        uuid    council_id FK
        string  agent_name
        text    content
        int     token_count
        int     turn_index
        datetime created_at
    }

    TEA_RECOMMENDATION {
        uuid    rec_id PK
        uuid    session_id FK
        string  tea_name
        string  emotion_matched
        string  caffeine_filter
        string  allergy_filter
        string  bgm_url
        datetime recommended_at
    }

    USER ||--o{ CHAT_SESSION : "has"
    USER ||--o{ LTM_MEMORY : "stores"
    CHAT_SESSION ||--o{ MESSAGE : "contains"
    CHAT_SESSION ||--o{ SCALE_SCORE : "produces"
    CHAT_SESSION ||--o| INNER_COUNCIL_SESSION : "triggers"
    CHAT_SESSION ||--o{ TEA_RECOMMENDATION : "receives"
    MESSAGE ||--o| EMOTION_ANALYSIS : "analyzed_by"
    INNER_COUNCIL_SESSION ||--o{ AGENT_TURN : "has"
```

---

## 2. 엔티티 상세 설명

### USER
| 컬럼 | 설명 |
| :--- | :--- |
| `user_id` | UUID PK |
| `oauth_provider` | kakao / naver |
| `is_secret_default` | 시크릿챗 기본값 설정 (설정 화면 SCR-007) |
| `consent_sensitive` | 민감정보 동의 여부 (온보딩 SCR-001) |
| `intimacy_level` | 친밀도 레벨 (REQ-F-007) |
| `acorn_count` | 도토리 수량 (마이페이지 SCR-006) |
| `deleted_at` | 회원 탈퇴 시 soft delete → 물리 삭제 트리거 |

### CHAT_SESSION
| 컬럼 | 설명 |
| :--- | :--- |
| `character_id` | 해온 / 그릉 / 달콩 |
| `is_secret` | 시크릿챗 모드 여부 (REQ-F-012) |
| `total_turns` | 누적 발화 턴 수 (과의존 가드레일 기준) |
| `is_inner_council_used` | 이너 카운슬 사용 여부 |

### MESSAGE
| 컬럼 | 설명 |
| :--- | :--- |
| `role` | user / assistant |
| `turn_count` | 4 이상부터 감정분석 활성화 (REQ-F-002) |
| `char_count` | 최대 300자 제한 검증 (REQ-NF-007) |

### EMOTION_ANALYSIS
| 컬럼 | 설명 |
| :--- | :--- |
| `emotion_code` | KcELECTRA 60개 감정 코드 (E10~E69) |
| `inference_ms` | 추론 응답시간 (p95 < 300ms 검증, REQ-NF-009) |

### SCALE_SCORE
| 컬럼 | 설명 |
| :--- | :--- |
| `scale_type` | PHQ-9 / GAD-7 / PHQ-15 / RSES / UCLA-3 / SPANE |
| `estimated_score` | 간접 추정 점수 (임상 진단 아님, 면책 고지) |
| `is_final` | 세션 종료 시 최종 확정 여부 |

### LTM_MEMORY (Neo4j 연동)
| 컬럼 | 설명 |
| :--- | :--- |
| `node_type` | Event / Person / Organization / Topic |
| `keyword` | 기억 키워드 (마이페이지 기억 보관소 노출) |
| `relation` | Neo4j 그래프 관계 엣지 타입 |
| `deleted_at` | 사용자 삭제 요청 시 DETACH DELETE 처리 |

### INNER_COUNCIL_SESSION
| 컬럼 | 설명 |
| :--- | :--- |
| `total_tokens` | 합산 토큰 사용량 (1,200 상한, REQ-NF-007) |
| `force_stopped` | 토큰 상한 도달로 강제 종료 여부 |
| `summary_card` | 3에이전트 합의 요약 카드 텍스트 |

### AGENT_TURN
| 컬럼 | 설명 |
| :--- | :--- |
| `agent_name` | haeon / geulung / dalkong |
| `token_count` | 개별 발화 토큰 수 (max_tokens=150) |
| `turn_index` | 발화 순서 인덱스 |

### TEA_RECOMMENDATION
| 컬럼 | 설명 |
| :--- | :--- |
| `emotion_matched` | 매핑된 감정 코드 |
| `caffeine_filter` | 카페인 민감 / 괜찮음 |
| `allergy_filter` | 국화과 / 메밀 / 없음 |
| `bgm_url` | 유튜브 BGM 플레이리스트 URL |

---

## 3. 시크릿챗 데이터 분리 정책

> [!caution] 시크릿챗 세션 데이터 처리 규칙
> - `CHAT_SESSION.is_secret = TRUE` 인 경우:
>   - `MESSAGE`, `EMOTION_ANALYSIS`, `SCALE_SCORE` 레코드는 세션 종료 즉시 영구 물리 삭제
>   - `TEA_RECOMMENDATION` 및 마음 리포트 생성 금지
>   - `LTM_MEMORY` 업데이트 금지
>   - 단, 백그라운드 안전성 가드레일은 익명으로 작동 후 즉시 파기

---

## 4. Neo4j 벡터 인덱스 — 심리이론 RAG 구조

> [!info] Neo4j Vector Index 역할
> 별도의 Chroma DB를 구축하지 않고, **Neo4j의 내장 Vector Index 기능**을 활성화하여 사용합니다.
> 심리학 이론 마크다운 문서 청크들을 `(:TheoryChunk)` 노드로 저장하고 임베딩 속성을 연결해 검색을 전담합니다.

### 저장 노드 구조

| 노드 레이블 | 프로퍼티 속성 | 메타데이터 속성 |
| :--- | :--- | :--- |
| `(:TheoryChunk)` | content: "CBT 생각 검증 질문: 늘 실패한다는 느낌, 어떤 상황에서 그런 생각이 제일 크게 들어?", embedding: [1536차원 벡터] | emotion: "불안", theory: "CBT" |
| `(:TheoryChunk)` | content: "ACT 탈융합: 불안이라는 파도가 너를 치고 지나가는 것뿐이야", embedding: [1536차원 벡터] | emotion: "불안", theory: "ACT" |
| `(:TheoryChunk)` | content: "내러티브 외재화: 무기력이라는 불청객이 널 힘들게 하는구나", embedding: [1536차원 벡터] | emotion: "슬픔", theory: "내러티브" |

### 실시간 검색 흐름

```
XGBoost → 감정 클래스 (예: 불안)
    ↓
Neo4j Vector Index 유사도 검색 (emotion=불안 필터)
    ↓
상위 2개 템플릿 반환
    ↓
GPT 시스템 프롬프트에 주입
    ↓
캐릭터가 자연스럽게 해당 기법으로 응답
```

### 감정 클래스 → 심리이론 매핑

| 감정 클래스 | 주 심리이론 | 보조 심리이론 |
| :--- | :--- | :--- |
| 분노 | 내러티브 (외재화) | CBT (인지재구성) |
| 슬픔 | 내러티브 | ACT (수용) |
| 불안 | CBT (생각 검증) | ACT (탈융합) |
| 당황 | 게슈탈트 (신체 알아차림) | CBT |
| 상처 | 내러티브 | CBT (자존감 재구성) |
| 기쁨 | — (일상 대화 전환) | — |

import os
import re

docs_dir = r"c:\dev\project\SKN27-FINAL-4Team\docs"

def clean_requirements():
    path = os.path.join(docs_dir, "[통합] 요구사항 정의서.md")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 3.2.2 섹션 통째로 교체
    pattern = re.compile(r"### 3\.2\.2 다중 에이전트 기반 이너 카운슬.*?### 3\.3", re.DOTALL)
    replacement = """### 3.2.2 다중 에이전트 기반 오케스트레이션 설계 명세 (Multi-Agent Orchestration)
시스템은 1:1 대화 성능(Latency)과 비용 최적화를 위해, 다중 에이전트 간의 무한 루프 토론을 배제하고 아래의 역할 분화형 오케스트레이션 설계를 준수해야 한다.
1.  **Supervisor 에이전트 (State 라우터)**:
    *   사용자 메시지 입력을 모니터링하여 대화 상태(State)와 턴 수를 체크하고, 다음으로 호출할 에이전트(분석, 기억, MBTI, 추천, 페르소나)를 라우팅한다.
2.  **분석 에이전트 (Analysis Agent)**:
    *   KcELECTRA와 XGBoost를 통해 사용자의 감정 강도를 파악하고, 6종 임상 척도를 추정하여 PostgreSQL에 저장한다.
3.  **기억 에이전트 (Memory Agent)**:
    *   Neo4j Graph DB를 쿼리하여 사용자의 인과적 장기 기억(LTM)과 RAG 이론 지식을 인출하여 Supervisor에 반환한다.
4.  **MBTI 에이전트 (MBTI Agent)**:
    *   대화 4턴 이상 시, 사용자의 텍스트 입력 내 단어 선택 빈도와 말투를 기반으로 MBTI 4축 가중치(E/I, S/N, T/F, J/P)를 실시간 추정하여 DB에 누적한다.
5.  **페르소나 발화 에이전트 (Persona Agent)**:
    *   Supervisor가 전달한 분석 지표, RAG 이론 스니펫, 장기 기억(LTM), MBTI 성향 추정 결과 및 BGM/차 정보를 종합해 고유 캐릭터(해온, 그릉, 달콩) 페르소나 어투와 이모티콘 표정이 일치된 최종 발화를 생성한다.

### 3.3"""
    
    new_content, count = re.subn(pattern, replacement, content)
    if count > 0:
        print("Replaced 3.2.2 in 요구사항 정의서 via Regex")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
    else:
        print("FAILED to replace 3.2.2 in 요구사항 정의서 via Regex")

def clean_comprehensive_plan():
    path = os.path.join(docs_dir, "[통합] 종합 기획안.md")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # ## 7. 멀티에이전트 아키텍처 섹션 통째로 교체
    pattern = re.compile(r"## 7\. 멀티에이전트 아키텍처.*?## 8\.", re.DOTALL)
    replacement = """## 7. 멀티에이전트 아키텍처 (오케스트레이션)

우리의 서비스는 여러 AI가 유기적으로 작동하는 **다중 에이전트(Multi-Agent) 시스템**입니다. 사용자 대화의 응답 속도와 API 비용 최적화를 위해 실시간 3인 토의방을 배제하고, 역할이 극도로 분화된 에이전트 간의 **병렬 파이프라인(Parallel Pipeline)** 구조를 채택했습니다.

```
                  [Supervisor 에이전트]
                             │
      ┌───────────────────────┼───────────────────────┐
      ▼                       ▼                       ▼
[분석 에이전트]          [기억/RAG 에이전트]       [MBTI 에이전트]
- 감정/척도 추정         - Neo4j LTM 및 RAG      - 4축 성향 추정
      │                       │                       │
      └───────────────────────┼───────────────────────┘
                              ▼
                   [페르소나 발화 에이전트]
             - GPT-4o-mini 최종 응답 합성
             - 캐릭터 어투(해온/그릉/달콩) 및 표정 이모티콘 렌더링
```

*   **비용 및 토큰 제어 가드레일 (Token Budgeting)**:
    *   **1:1 대화 제약**: 사용자 1회 입력 최대 한글 300자 제한, 프롬프트 메모리 최근 10개 메시지 턴 슬라이딩 윈도우 제한.
    *   **Memory & RAG Injection**: 요약 기억 최대 3개, RAG 심리 이론 지식 노드는 최대 2개로 제약 (합산 500토큰 이하).
    *   **MBTI 추정 제약**: 대화 턴 수가 4턴 이상인 세션 종료 시점에만 최종 MBTI 4축 성향 값을 누적 계산하여, 실시간 API 과도 호출을 차단합니다.

## 8."""
    
    new_content, count = re.subn(pattern, replacement, content)
    if count > 0:
        print("Replaced Section 7 in 종합 기획안 via Regex")
    else:
        print("FAILED to replace Section 7 in 종합 기획안 via Regex")

    # 6.1의 흐름도 Mermaid 블록 내 이너 카운슬 관련 명세 제거 및 새로운 다이어그램으로 치환
    pattern_flow = re.compile(r"### 6\.1  마음 웰니스 챗봇 대화 흐름도.*?### 6\.2", re.DOTALL)
    replacement_flow = """### 6.1  마음 웰니스 챗봇 대화 흐름도 (Chatbot Conversation Flow)

아래 다이어그램은 1:1 대화 및 분석 에이전트들의 오케스트레이션 작동과 최종 데이터 저장 및 파기 프로토콜을 보여주는 흐름도입니다.

```mermaid
flowchart TD
    classDef user fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef engine fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef agent fill:#efebe9,stroke:#5d4037,stroke-width:2px;
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef output fill:#fffde7,stroke:#fbc02d,stroke-width:2px;

    User([사용자 발화 입력]):::user
    TurnCheck{대화 턴 수 검사}:::engine
    
    BasicFlow[1~3턴: 탐색 구간]:::engine
    GPT_Basic[③ 페르소나 에이전트\\n- 다정한 기본 안부 및 탐색 질문]:::agent
    
    ActiveFlow[4턴 이상: 분석 및 RAG 구간]:::engine
    
    Agent_Analysis["① 분석 에이전트\\n(KcELECTRA + XGBoost)"]:::agent
    Agent_Context["② 기억 에이전트\\n(Neo4j LTM & RAG Index)"]:::agent
    Agent_MBTI["④ MBTI 에이전트\\n(대화 기반 MBTI 4축 추정)"]:::agent
    
    Emo_Class[사용자 감정 강도 분류\\n(6대 정서 클래스)]:::engine
    Scale_Est[6종 임상 척도 점수 추정\\n(PHQ-9, GAD-7 등)]:::engine
    RAG_Query[Neo4j Vector Index\\n- 심리이론 RAG 청크 쿼리]:::db
    LTM_Query[Neo4j LTM Graph\\n- 과거 사건/인맥 맥락 쿼리]:::db
    
    Mapper[공감 매핑 모듈\\n- 4대 공감 반응 결정\\nencourage / sad / angry / plan]:::engine
    
    GPT_Persona["③ 페르소나 에이전트\\n(GPT-4o-mini)\\n- 어투/공감모드/RAG/LTM/MBTI 합성"]:::agent
    Tea_BGM[추천 엔진\\n- 정서 맞춤 차 & BGM 매핑]:::engine
    
    Render([최종 화면 출력\\n- 말풍선, 표정 애니메이션\\n- 차 추천 카드 & BGM 링크]):::output
    
    EndCheck{대화 세션 종료}:::engine
    SecretCheck{시크릿챗 활성화?}:::engine
    Destroy[메모리 세션 즉시 파기\\n- DB/LTM 미기록]:::db
    UpdateDB[정형 데이터 PostgreSQL 저장\\n- Neo4j LTM 인과 그래프 업데이트\\n- 오늘의 마음 카드 발행]:::db

    User --> TurnCheck
    TurnCheck -- "1 ~ 3턴" --> BasicFlow
    BasicFlow --> GPT_Basic
    GPT_Basic --> Render
    
    TurnCheck -- "4턴 이상" --> ActiveFlow
    ActiveFlow --> Agent_Analysis
    ActiveFlow --> Agent_Context
    ActiveFlow --> Agent_MBTI
    
    Agent_Analysis --> Emo_Class
    Agent_Analysis --> Scale_Est
    Emo_Class & Scale_Est --> Mapper
    
    Agent_Context --> RAG_Query
    Agent_Context --> LTM_Query
    
    RAG_Query & LTM_Query & Agent_MBTI & Mapper --> GPT_Persona
    GPT_Persona --> Tea_BGM
    Tea_BGM --> Render
    
    Render --> EndCheck
    EndCheck --> SecretCheck
    SecretCheck -- "Yes (비저장)" --> Destroy
    SecretCheck -- "No (일반)" --> UpdateDB
    Destroy & UpdateDB --> Finish([세션 완전 종료]):::user
```

### 6.2"""
    
    new_content, count_flow = re.subn(pattern_flow, replacement_flow, new_content)
    if count_flow > 0:
        print("Replaced Flows in 종합 기획안 via Regex")
    
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)

def clean_system_design():
    path = os.path.join(docs_dir, "[통합] 시스템 설계서.md")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 3.4 이너 카운슬 시퀀스 단락 삭제
    pattern_seq = re.compile(r"### 3\.4 이너 카운슬 회의.*?### 4\.", re.DOTALL)
    new_content, count_seq = re.subn(pattern_seq, "### 3.4 [삭제]\n\n", content)
    if count_seq > 0:
        print("Deleted 3.4 in 시스템 설계서 via Regex")
    
    # ERD에서 이너 카운슬 테이블 삭제
    # Neo4j LTM 관계 및 PostgreSQL 테이블 선 삭제
    new_content = new_content.replace("    INNER_COUNCIL_SESSION {\n        bigint session_id PK\n        bigint user_id FK\n        datetime started_at\n        datetime ended_at\n        text agent_dialogue_summary\n        text user_interventions\n    }\n\n    AGENT_TURNS {\n        bigint turn_id PK\n        bigint session_id FK\n        string agent_name\n        text dialogue_text\n        int turn_number\n        datetime created_at\n    }\n", "")
    new_content = new_content.replace("    USERS ||--o{ INNER_COUNCIL_SESSION : participates\n    INNER_COUNCIL_SESSION ||--o{ AGENT_TURNS : contains\n", "")
    new_content = new_content.replace("이너 카운슬 세션, ", "")
    
    # 3.2.1 챗봇 대화방 통합 흐름도 내 Mermaid 다이어그램 교체
    pattern_flow = re.compile(r"#### 3\.2\.1  챗봇 대화방 통합 흐름도.*?##### 세부 단계별 로직 설명", re.DOTALL)
    replacement_flow = """#### 3.2.1  챗봇 대화방 통합 흐름도 (Mermaid)

아래 다이어그램은 1:1 대화방의 오케스트레이션 및 데이터 제어 흐름입니다.

```mermaid
flowchart TD
    classDef user fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef engine fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef agent fill:#efebe9,stroke:#5d4037,stroke-width:2px;
    classDef db fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef output fill:#fffde7,stroke:#fbc02d,stroke-width:2px;

    User([사용자 발화 입력]):::user
    TurnCheck{대화 턴 수 검사}:::engine
    
    BasicFlow[1~3턴: 탐색 구간]:::engine
    GPT_Basic[③ 페르소나 에이전트\\n- 다정한 기본 안부 및 탐색 질문]:::agent
    
    ActiveFlow[4턴 이상: 분석 및 RAG 구간]:::engine
    
    Agent_Analysis["① 분석 에이전트\\n(KcELECTRA + XGBoost)"]:::agent
    Agent_Context["② 기억 에이전트\\n(Neo4j LTM & RAG Index)"]:::agent
    Agent_MBTI["④ MBTI 에이전트\\n(대화 기반 MBTI 4축 추정)"]:::agent
    
    Emo_Class[사용자 감정 강도 분류\\n(6대 정서 클래스)]:::engine
    Scale_Est[6종 임상 척도 점수 추정\\n(PHQ-9, GAD-7 등)]:::engine
    RAG_Query[Neo4j Vector Index\\n- 심리이론 RAG 청크 쿼리]:::db
    LTM_Query[Neo4j LTM Graph\\n- 과거 사건/인맥 맥락 쿼리]:::db
    
    Mapper[공감 매핑 모듈\\n- 4대 공감 반응 결정\\nencourage / sad / angry / plan]:::engine
    
    GPT_Persona["③ 페르소나 에이전트\\n(GPT-4o-mini)\\n- 어투/공감모드/RAG/LTM/MBTI 합성"]:::agent
    Tea_BGM[추천 엔진\\n- 정서 맞춤 차 & BGM 매핑]:::engine
    
    Render([최종 화면 출력\\n- 말풍선, 표정 애니메이션\\n- 차 추천 카드 & BGM 링크]):::output
    
    EndCheck{대화 세션 종료}:::engine
    SecretCheck{시크릿챗 활성화?}:::engine
    Destroy[메모리 세션 즉시 파기\\n- DB/LTM 미기록]:::db
    UpdateDB[정형 데이터 PostgreSQL 저장\\n- Neo4j LTM 인과 그래프 업데이트\\n- 오늘의 마음 카드 발행]:::db

    User --> TurnCheck
    TurnCheck -- "1 ~ 3턴" --> BasicFlow
    BasicFlow --> GPT_Basic
    GPT_Basic --> Render
    
    TurnCheck -- "4턴 이상" --> ActiveFlow
    ActiveFlow --> Agent_Analysis
    ActiveFlow --> Agent_Context
    ActiveFlow --> Agent_MBTI
    
    Agent_Analysis --> Emo_Class
    Agent_Analysis --> Scale_Est
    Emo_Class & Scale_Est --> Mapper
    
    Agent_Context --> RAG_Query
    Agent_Context --> LTM_Query
    
    RAG_Query & LTM_Query & Agent_MBTI & Mapper --> GPT_Persona
    GPT_Persona --> Tea_BGM
    Tea_BGM --> Render
    
    Render --> EndCheck
    EndCheck --> SecretCheck
    SecretCheck -- "Yes (비저장)" --> Destroy
    SecretCheck -- "No (일반)" --> UpdateDB
    Destroy & UpdateDB --> Finish([세션 완전 종료]):::user
```

##### 세부 단계별 로직 설명"""
    
    new_content, count_diag = re.subn(pattern_flow, replacement_flow, new_content)
    if count_diag > 0:
        print("Replaced 3.2.1 Flow diagram in 시스템 설계서 via Regex")
        
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)

def clean_individual_screen():
    path = os.path.join(docs_dir, "[개별] 화면설계서_김한솔.md")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    pattern = re.compile(r"## 5\. SCR-004 이너 카운슬.*", re.DOTALL)
    new_content, count = re.subn(pattern, "", content)
    if count > 0:
        print("Deleted SCR-004 section in 개별 화면설계서 via Regex")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
    else:
        print("FAILED to delete SCR-004 in 개별 화면설계서 via Regex")

def clean_individual_erd():
    path = os.path.join(docs_dir, "[개별] ERD_김한솔.md")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 이너 카운슬 테이블 선언 및 관계 선언 제거
    new_content = content.replace("    INNER_COUNCIL_SESSION {\n        uuid    council_id PK\n        uuid    session_id FK\n        int     total_turns\n        int     total_tokens\n        bool    force_stopped\n        text    summary_card\n        datetime started_at\n        datetime ended_at\n    }\n\n    AGENT_TURN {\n        uuid    turn_id PK\n        uuid    council_id FK\n        string  agent_name\n        text    content\n        int     token_count\n        int     turn_index\n        datetime created_at\n    }\n", "")
    new_content = new_content.replace("    CHAT_SESSION ||--o| INNER_COUNCIL_SESSION : \"triggers\"\n    INNER_COUNCIL_SESSION ||--o{ AGENT_TURN : \"has\"\n", "")
    
    # 엔티티 상세설명 지우기
    pattern_desc = re.compile(r"### INNER_COUNCIL_SESSION.*?### TEA_RECOMMENDATION", re.DOTALL)
    new_content, count = re.subn(pattern_desc, "### TEA_RECOMMENDATION", new_content)
    if count > 0:
        print("Replaced INNER_COUNCIL_SESSION desc in 개별 ERD via Regex")
        
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)

clean_requirements()
clean_comprehensive_plan()
clean_system_design()
clean_individual_screen()
clean_individual_erd()
print("All cleanup done.")

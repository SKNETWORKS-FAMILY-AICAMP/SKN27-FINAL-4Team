import re
import os

docs_dir = r"c:\dev\project\SKN27-FINAL-4Team\docs"

def replace_in_file(file_path, replacements):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    modified = content
    for target, replacement in replacements:
        # 개행 문자 정규화 (\r\n -> \n)
        target_norm = target.replace("\r\n", "\n")
        content_norm = modified.replace("\r\n", "\n")
        if target_norm in content_norm:
            content_norm = content_norm.replace(target_norm, replacement.replace("\r\n", "\n"))
            modified = content_norm
            print(f"Replaced target in {os.path.basename(file_path)}")
        else:
            # 부분 매핑 시도 또는 에러 로그
            print(f"Target NOT found in {os.path.basename(file_path)}")
            # 상세 디버깅을 위해 앞부분 50자 출력
            print(f"Expected start: {target_norm[:100]}")
    
    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(modified)

# 1. 요구사항 정의서 개정
reqs_path = os.path.join(docs_dir, "[통합] 요구사항 정의서.md")
reqs_replacements = [
    # REQ-F-008 교체
    (
        "| **REQ-F-008** | 이너 카운슬 회의 | *사용자로서, 나를 위해 여러 캐릭터들이 머리를 맞대고 진심으로 고민해 주길 바란다.*<br>시스템은 사용자가 원하여 직접 수동으로 요청할 때에만 캐릭터 3종이 사용자의 고민에 대해 대화하는 이너 카운슬 회의방 연출을 제공해야 한다.<br>**이너 카운슬 발동 조건 (모두 충족 시에만 버튼 활성화)**:<br>① 하루 1회 제한 (날짜 기준 자정 리셋)<br>② 현재 세션 내 최소 5턴 이상 대화 완료<br>③ 사용자 보유 캐릭터 3명 전부 해금 완료<br>④ 메인 캐릭터 친밀도 Lv.2 이상 달성 | S | MVP+ |",
        "| **REQ-F-008** | MBTI 성향 추정 | *사용자로서, 나의 대화 어조와 문체에서 나의 MBTI 성향이 어떻게 변화하고 있는지 은밀하게 추정받아 분석 결과를 보고 싶다.*<br>시스템은 대화가 4번째 턴 이상 진행될 때, 사용자의 텍스트 표현(문체, 감정 단어 사용 빈도 등)을 바탕으로 MBTI 4축(E/I, S/N, T/F, J/P) 성향 가중치를 백엔드에서 간접 추정하여 데이터베이스에 누적하고, 마음 리포트 발송 시 이를 시각화하여 표현해야 한다. | M | MVP |"
    ),
    # UCLA-3 외로움 교체
    (
        "| **UCLA-3 (외로움)** | 사회적 고립, 대화 부족 | **내러티브 치료 (외재화 및 대안적 이야기)** | 이너 카운슬 (다중에이전트 3:1 대화방), 리텐션 안부 이메일 | 고립도 수치 상승 시 이너 카운슬 회의방 입장 트리거 노출 |",
        "| **UCLA-3 (외로움)** | Social Isolation, 대화 부족 | **내러티브 치료 (외재화 및 대안적 이야기)** | 캐릭터의 안부 편지 배너, MBTI 성향 변화 피드백 | 고립도 수치 상승 시 캐릭터의 안부 편지 트리거 노출 |"
    ),
    # 3.2.2 이너 카운슬 명세 교체
    (
        "### 3.2.2 다중 에이전트 기반 이너 카운슬(Inner Council) 설계 명세\n시스템은 캐릭터 간의 실시간 토의 및 조율 과정에서 다음의 다중 에이전트 제어 규칙을 준수해야 한다.\n1.  **발동 트리거 조건**:\n    *   **사용자 수동 기동**: 사용자가 대화방 내의 \"이너 카운슬 회의 시작\" 버튼을 직접 터치하여 가동을 요청할 때에만 실시간 오버레이로 시작된다. (자동 발동 및 백그라운드 자동 기동은 지원하지 않는다.)\n2.  **캐릭터별 페르소나 및 심리이론 매핑**:\n    *   **해온 (위로 Agent)**: 내러티브 치료를 적용해 사용자의 아픔을 무조건적으로 수용하고 감정을 지지한다. 문제를 유저 밖으로 끄집어내는 외재화 기법을 발화에 강제 적용한다.\n    *   **그릉 (직면 Agent)**: 인지행동치료(CBT)를 적용해 사용자의 극단적 왜곡(과도한 일반화, 흑백논리)에 부드러운 반론을 던지고 인지 재구성 질문을 수행한다.\n    *   **달콩 (코치 Agent)**: 수용전념치료(ACT)를 적용해 감정 수용 후 유저가 가치를 두고 실천할 수 있는 10분 내외의 소소한 행동 활성화 미션(Commitment Action)을 제안한다.\n3.  **LangGraph 턴 제어 및 조율 가드레일**:\n    *   에이전트 간 무한 루프 방지 및 API 요금 제어를 위해, 이너 카운슬 회의는 **최대 3턴(Turn) 및 총 1500토큰 상한선** 이내로 조율 에이전트(Orchestrator)가 논의를 강제 정돈해야 한다.\n    *   최종 조율 에이전트는 캐릭터들의 대화 결과를 요약하여 하나의 '합의된 위로 결과 요약 카드' 구조물로 빌드해 출력해야 한다.\n4.  **사용자 인터랙션 (관전 및 개입)**:\n    *   시스템은 유저가 캐릭터들이 채팅창에서 서로 대화하고 논의하는 과정을 지켜보는 '관전 뷰'를 제공해야 한다.\n    *   시스템은 유저가 중간에 한마디를 입력(\"나도 그렇게 생각해\", \"너무 잔소리하지 마\")해 개입할 시, 그 입력 텍스트를 LangGraph Context에 주입하여 다음 에이전트들의 대화 방향에 동적으로 반영하도록 해야 한다.",
        "### 3.2.2 다중 에이전트 기반 오케스트레이션 설계 명세 (Multi-Agent Orchestration)\n시스템은 1:1 대화 성능(Latency)과 비용 최적화를 위해, 다중 에이전트 간의 무한 루프 토론을 배제하고 아래의 역할 분화형 오케스트레이션 설계를 준수해야 한다.\n1.  **Supervisor 에이전트 (State 라우터)**:\n    *   사용자 메시지 입력을 모니터링하여 대화 상태(State)와 턴 수를 체크하고, 다음으로 호출할 에이전트(분석, 기억, MBTI, 추천, 페르소나)를 라우팅한다.\n2.  **분석 에이전트 (Analysis Agent)**:\n    *   KcELECTRA와 XGBoost를 통해 사용자의 감정 강도를 파악하고, 6종 임상 척도를 추정하여 PostgreSQL에 저장한다.\n3.  **기억 에이전트 (Memory Agent)**:\n    *   Neo4j Graph DB를 쿼리하여 사용자의 인과적 장기 기억(LTM)과 RAG 이론 지식을 인출하여 Supervisor에 반환한다.\n4.  **MBTI 에이전트 (MBTI Agent)**:\n    *   대화 4턴 이상 시, 사용자의 텍스트 입력 내 단어 선택 빈도와 말투를 기반으로 MBTI 4축 가중치(E/I, S/N, T/F, J/P)를 실시간 추정하여 DB에 누적한다.\n5.  **페르소나 발화 에이전트 (Persona Agent)**:\n    *   Supervisor가 전달한 분석 지표, RAG 이론 스니펫, 장기 기억(LTM), MBTI 성향 추정 결과 및 BGM/차 정보를 종합해 고유 캐릭터(해온, 그릉, 달콩) 페르소나 어투와 이모티콘 표정이 일치된 최종 발화를 생성한다."
    ),
    # REQ-F-008 AC 교체
    (
        "4.  **REQ-F-008 (이너 카운슬)**: 이너 카운슬 그룹 대화방 기동 시, LangGraph 오케스트레이터의 턴 제어에 따라 3인 캐릭터 에이전트가 순차 응답하며, 총 1,200토큰 이내에 대화 요약 카드를 조율 출력할 것.",
        "4.  **REQ-F-008 (MBTI 성향 추정)**: 대화 4턴 이상 진행 시, 백엔드 MBTI 에이전트가 사용자의 구어체 문맥에서 MBTI 4축 성향 점수를 산출하여 DB에 정상 저장하고 마음 리포트 발송 시 분석 텍스트와 함께 연동 표출할 것."
    ),
    # REQ-NF-006 교체
    (
        "PostgreSQL (관계형 DB)**: 사용자 계정, 대화 세션, 메시지, 감정분석 결과, 척도 점수, 이너 카운슬 세션, 차 추천 이력",
        "PostgreSQL (관계형 DB)**: 사용자 계정, 대화 세션, 메시지, 감정분석 결과, 척도 점수, 차 추천 이력"
    ),
    # REQ-NF-007 교체
    (
        "5. **이너 카운슬 토큰 캡**: 캐릭터별 개별 발화 `max_tokens = 150` 제한 및 전체 이너 카운슬 1회 기동 시 **합산 최대 1,200토큰** 도달 시 조율 에이전트(Orchestrator)가 세션을 강제 종료하고 정리 요약을 출력해야 함.",
        "5. **MBTI 추정 주기**: 대화 세션 종료 시, 최종 누적 세션 벡터를 기반으로 MBTI 추정을 확정하며 세션 종료 시까지는 비동기식 실시간 가중치 백그라운드 큐로 처리해 응답 지연을 방지할 것."
    )
]

# 2. 종합 기획안 개정
plan_path = os.path.join(docs_dir, "[통합] 종합 기획안.md")
plan_replacements = [
    # 초록 부분 이너 카운슬 언급 변경
    (
        "나를 기억하는 캐릭터 친구들(이너 카운슬)이 붙잡는 **비의료 마음 웰니스 웹앱**",
        "나를 기억하고 어투/성향을 미러링하는 캐릭터 친구들(빈틈사이)이 붙잡는 **비의료 마음 웰니스 웹앱**"
    ),
    (
        "다중 에이전트(LangGraph)·RAG·자체 감정분류 모델로 구현하며",
        "다중 에이전트 오케스트레이션·RAG·자체 감정분류 모델로 구현하며"
    ),
    (
        "| **포함 (In)** | 정서·자기이해·관계 위로, 캐릭터 대화, KcELECTRA 감정분석, KoNLPy 형태소 분석, 6척도 추정, 마음 리포트, 메모리, 이너 카운슬 |",
        "| **포함 (In)** | 정서·자기이해·관계 위로, 캐릭터 대화, KcELECTRA 감정분석, KoNLPy 형태소 분석, 6척도 추정, 마음 리포트, 메모리, MBTI 추정 |"
    ),
    (
        "이너 카운슬 + 안전 가드레일)",
        "MBTI 추정 + 안전 가드레일)"
    ),
    (
        "### 4.2 차별화 핵심 요소: 마음 리포트와 이너 카운슬",
        "### 4.2 차별화 핵심 요소: 마음 리포트와 MBTI 성향 추정"
    ),
    (
        "*   **UCLA-3 (외로움)**: 고립 위험군 판정 시 홈 화면에 이너 카운슬(다중에이전트 3:1) 대화방 입장 티켓을 선제 발송하고 리텐션 안부 알림 주기를 단축합니다.",
        "*   **UCLA-3 (외로움)**: 고립 위험군 판정 시 홈 화면에 캐릭터의 안부 편지 배너와 MBTI 성향 변화 피드백을 우선 노출하고 리텐션 안부 알림 주기를 단축합니다."
    ),
    (
        "| **UCLA-3 (외로움)** | 사회적 고립, 대화 부족 | **내러티브 치료 (외재화 및 대안적 이야기)** | 이너 카운슬 (다중에이전트 3:1 대화방), 리텐션 안부 이메일 | 고립도 수치 상승 시 이너 카운슬 회의방 입장 트리거 노출 |",
        "| **UCLA-3 (외로움)** | 사회적 고립, 대화 부족 | **내러티브 치료 (외재화 및 대안적 이야기)** | 캐릭터의 안부 편지 배너, MBTI 성향 변화 피드백 | 고립도 수치 상승 시 캐릭터의 안부 편지 트리거 노출 |"
    ),
    (
        "[4. 이너 카운슬] 조건부 발동 ➔ 3개 에이전트 그룹 대화방 ➔ 사용자의 관전 및 개입",
        "[4. MBTI 성향 추정] ➔ 대화 성향/문체 실시간 추정 ➔ 마음 리포트 결과 카드 반영"
    ),
    (
        "6.  **데이터셋 연계형 챗봇 3대 특화 기능**",
        "6.  **데이터셋 연계형 챗봇 3대 특화 기능 (이너 카운슬 제외 및 MBTI 대체)"
    ),
    (
        "- 다중 에이전트 LangGraph 기반 이너 카운슬      - 38일의 한정된 MVP 빌드 타임라인",
        "- 다중 에이전트 기반 오케스트레이션 & MBTI       - 38일의 한정된 MVP 빌드 타임라인"
    ),
    (
        "*   **3단계: 통합 및 안전망 구축 (~6주차)**: LangGraph 다중 에이전트 이너 카운슬 결합.",
        "*   **3단계: 통합 및 안전망 구축 (~6주차)**: 다중 에이전트 오케스트레이션 및 안전 가드레일 결합."
    ),
    # 7번 단락 전체 (LangGraph 이너 카운슬 명세) 교체
    (
        "## 7. 멀티에이전트 아키텍처 (LangGraph)\n\n우리의 서비스는 여러 AI가 유기적으로 작동하는 **다중 에이전트(Multi-Agent) 시스템**이다. LangGraph를 사용하여 에이전트 간의 턴을 제어한다.\n\n```\n                  [LangGraph Orchestrator]\n                             │\n      ┌───────────────────────┼───────────────────────┐\n      ▼                       ▼                       ▼\n[해온 Agent]             [그릉이 Agent]          [달콩이 Agent]\n Persona: 위로           Persona: 직면           Persona: 코치\n 역할: 정서 수용          역할: 인지 왜곡 제기      역할: 행동 넛지 제안\n      │                       │                       │\n      └───────────────────────┼───────────────────────┘\n                              ▼\n                   [정리 및 조율 Agent]\n            - 캐릭터들 간의 대화 요약\n            - 중복 발언 및 급격한 대화 탈출 제어\n            - 최종 위로 요약 카드 구조물 생성\n```\n\n*   **비용 및 토큰 제어 가드레일 (Token Budgeting)**:\n    *   **1:1 대화 제약**: 사용자 1회 입력 최대 한글 300자 제한, 프롬프트 메모리 10개 턴 슬라이딩 윈도우 제한, 요약 기억(Memory) 최대 3개 및 RAG 지식 노드 최대 2개 주입 (합계 500토큰 이하), 캐릭터 답변 생성 시 `max_tokens = 250`으로 강제 바인딩.\n    *   **이너 카운슬 제약**: 무분별한 에이전트 간 무한 루프 및 API 과도 호출을 방지하기 위해 **캐릭터별 개별 발화 최대 150토큰**, **1회 세션당 총 1,200토큰 상한선**을 설정합니다. 조율 에이전트가 이 한계 도달 시 세션을 즉시 차단하고 요약 결과지를 도출합니다.",
        "## 7. 멀티에이전트 아키텍처 (오케스트레이션)\n\n우리의 서비스는 여러 AI가 유기적으로 작동하는 **다중 에이전트(Multi-Agent) 시스템**입니다. 사용자 대화의 응답 속도와 API 비용 최적화를 위해 실시간 3인 토의방을 배제하고, 역할이 극도로 분화된 에이전트 간의 **병렬 파이프라인(Parallel Pipeline)** 구조를 채택했습니다.\n\n```\n                  [Supervisor 에이전트]\n                             │\n      ┌───────────────────────┼───────────────────────┐\n      ▼                       ▼                       ▼\n[분석 에이전트]          [기억/RAG 에이전트]       [MBTI 에이전트]\n- 감정/척도 추정         - Neo4j LTM 및 RAG      - 4축 성향 추정\n      │                       │                       │\n      └───────────────────────┼───────────────────────┘\n                              ▼\n                   [페르소나 발화 에이전트]\n             - GPT-4o-mini 최종 응답 합성\n             - 캐릭터 어투(해온/그릉/달콩) 및 표정 이모티콘 렌더링\n```\n\n*   **비용 및 토큰 제어 가드레일 (Token Budgeting)**:\n    *   **1:1 대화 제약**: 사용자 1회 입력 최대 한글 300자 제한, 프롬프트 메모리 최근 10개 메시지 턴 슬라이딩 윈도우 제한.\n    *   **Memory & RAG Injection**: 요약 기억 최대 3개, RAG 심리 이론 지식 노드는 최대 2개로 제약 (합산 500토큰 이하).\n    *   **MBTI 추정 제약**: 대화 턴 수가 4턴 이상인 세션 종료 시점에만 최종 MBTI 4축 성향 값을 누적 계산하여, 실시간 API 과도 호출을 차단합니다."
    ),
    # 6.1 흐름도에서 이너 카운슬 관련 분기 삭제 (우리가 위에 작성했던 다이어그램 코드로 대체)
    # 6.1의 흐름도는 Markdown 코드 내부의 Mermaid 블록이므로 따로 찾아서 교체해줄 것
]

# 3. 시스템 설계서 개정
sys_path = os.path.join(docs_dir, "[통합] 시스템 설계서.md")
sys_replacements = [
    # 이너 카운슬 시퀀스 다이어그램 단락 삭제
    (
        "### 3.4 이너 카운슬 회의 (SCR-004)\n```mermaid\nsequenceDiagram\n    actor U as 사용자\n    participant FE as 웹앱\n    participant API as Django Backend\n    participant LG as LangGraph 에이전트\n    participant C1 as 캐릭터1 (해온 - 위로)\n    participant C2 as 캐릭터2 (그릉 - 직면)\n    participant C3 as 캐릭터3 (달콩 - 코치)\n    participant DB as PostgreSQL\n    Note over API: 주간 리포트 발송 혹은 정서 이상치 탐지 시 조건부 자동 가동\n    API->>LG: 이너 카운슬 프로세스 기동 (사용자 대화 요약 RAG 주입)\n    LG->>C1: 해온 에이전트 턴 가동\n    C1-->>LG: \"요즘 많이 우울한 날씨네요. 조급해하지 않게 기운을 불어넣을게요.\"\n    LG->>C2: 그릉 에이전트 턴 가동\n    C2-->>LG: \"근데 사실 낮 시간에 방에만 머물고 있는 피하기 습관이 문제 아닐까?\"\n    LG->>C3: 달콩 에이전트 턴 가동\n    C3-->>LG: \"그럴수록 오늘은 10분이라도 산책을 하자고 캐릭터가 제안하는 게 좋아 보여!\"\n    Note over LG: 무제한 연산 방지를 위한 최대 3턴(Turn) 가드레일 작동\n    LG-->>API: 회의 대화 기록 요약 및 합의된 결과 도출\n    API->>DB: 이너 카운슬 요약 카드 보존\n    API-->>FE: 회의 애니메이션 렌더링 및 개입 인터랙션 활성화\n    FE-->>U: 사용자가 이너 카운슬 관전 및 한마디 개입 수행\n```",
        ""
    ),
    # ERD에서 이너 카운슬 테이블 삭제
    (
        "    INNER_COUNCIL_SESSION {\n        bigint session_id PK\n        bigint user_id FK\n        datetime started_at\n        datetime ended_at\n        text agent_dialogue_summary\n        text user_interventions\n    }\n\n    AGENT_TURNS {\n        bigint turn_id PK\n        bigint session_id FK\n        string agent_name\n        text dialogue_text\n        int turn_number\n        datetime created_at\n    }",
        ""
    ),
    (
        "    USERS ||--o{ INNER_COUNCIL_SESSION : participates\n    INNER_COUNCIL_SESSION ||--o{ AGENT_TURNS : contains",
        ""
    )
]

# 4. 개별 시퀀스다이어그램 개정
seq_path = os.path.join(docs_dir, "[개별] 시퀀스다이어그램_김한솔.md")
seq_replacements = [
    # 이너카운슬 시나리오 2 삭제
    (
        "## 시나리오 2. 이너 카운슬 플로우 (SCR-004)\n\n```mermaid\nsequenceDiagram\n    actor User as 사용자\n    participant FE as Frontend (SCR-004)\n    participant Orch as LangGraph Orchestrator\n    participant Haeon as 해온 Agent (내러티브)\n    participant Geulung as 그릉 Agent (CBT)\n    participant Dalkong as 달콩 Agent (ACT)\n    participant DB as PostgreSQL\n\n    User->>FE: 이너 카운슬 버튼 클릭 (수동 발동)\n    FE->>Orch: POST /inner-council/start (session_id, context)\n    Orch->>DB: INNER_COUNCIL_SESSION 생성\n\n    Note over Orch,Dalkong: LangGraph 턴 제어 시작 (최대 3턴 / 1,200토큰 상한)\n\n    Orch->>Haeon: 사용자 고민 컨텍스트 전달\n    Haeon-->>Orch: 위로·외재화 발화 (max_tokens=150)\n    Orch->>DB: AGENT_TURN 기록 (turn_index=1)\n    Orch-->>FE: 해온 발화 스트리밍\n    FE-->>User: 해온 말풍선 + 이미지 이모티콘 표시\n\n    Orch->>Geulung: 해온 발화 + 컨텍스트 전달\n    Geulung-->>Orch: 직면·인지재구성 발화 (max_tokens=150)\n    Orch->>DB: AGENT_TURN 기록 (turn_index=2)\n    Orch-->>FE: 그릉 발화 스트리밍\n    FE-->>User: 그릉 말풍선 + 이미지 이모티콘 표시\n\n    Orch->>Dalkong: 이전 발화 + 컨텍스트 전달\n    Dalkong-->>Orch: 코치·행동미션 발화 (max_tokens=150)\n    Orch->>DB: AGENT_TURN 기록 (turn_index=3)\n    Orch-->>FE: 달콩 발화 스트리밍\n    FE-->>User: 달콩 말풍선 + 이미지 이모티콘 표시\n\n    alt 사용자 개입\n        User->>FE: 나도 한마디 입력\n        FE->>Orch: POST /inner-council/intervene (user_input)\n        Orch->>Orch: LangGraph Context에 사용자 입력 주입\n        Note over Orch: 다음 에이전트 발화 방향 동적 반영\n    end\n\n    Orch->>Orch: 토큰 합산 확인 (1,200 초과 or 3턴 완료)\n    Orch->>DB: 합의 요약 카드 생성 + INNER_COUNCIL_SESSION 종료\n    Orch-->>FE: 합의된 위로 요약 카드 반환\n    FE-->>User: 요약 카드 표시 + SCR-003 복귀\n    DB->>DB: 요약 데이터 → 마음 리포트 + LTM 반영\n```",
        ""
    )
]

# 5. 개별 화면설계서 개정
screen_path = os.path.join(docs_dir, "[개별] 화면설계서_김한솔.md")
screen_replacements = [
    # 이너카운슬 버튼 명세 지우기
    (
        " / **이너 카운슬 버튼** (수동 발동, SCR-004 진입, REQ-F-008)",
        ""
    ),
    # 5. SCR-004 이너카운슬 내용 지우기
    (
        "## 5. SCR-004 이너 카운슬 (Inner Counsel)\n\n| Page Title | **이너 카운슬 (Inner Counsel)** | Screen ID | **SCR-004** |\n| :--- | :--- | :--- | :--- |\n| **Author** | 김한솔 / 4팀 | **Date** | 2026.06.21 |\n| **Screen Path** | 2 홈 > 2.1 대화 > 2.1.1 이너 카운슬 (SCR-004) |\n\n### [1] 와이어프레임 & 기능 정의\n\n| UI 와이어프레임 (Mockup) | 기능 정의서 (Description) |\n| :---: | :--- |\n| <img src=\"../assets/inner_council_ui_mockup.png\" width=\"420px\"><br><br>**그림 2. SCR-004 이너 카운슬 UI 시안** | **① 이너 카운슬 가동 헤더**<br>\"캐릭터들이 당신에 대해 이야기하는 중\" 타이틀 표시.<br>사용자가 SCR-003 내 버튼을 수동으로 클릭할 때에만 실시간 가동 (자동 발동·백그라운드 기동 금지, REQ-F-008).<br><br>**② 3열 캐릭터 대화 회의 영역**<br>해온(위로·내러티브), 그릉(직면·CBT), 달콩(코치·ACT) 3에이전트 토론을 3열 배치로 노출.<br>각 에이전트 발화 시 캐릭터별 전용 이미지 이모티콘 (메모·분석·코치 표정)으로 전환.<br>LangGraph 오케스트레이터가 에이전트 간 발화 순서 조율.<br><br>**③ 개입 및 지켜보기 컨트롤**<br>나도 한마디 개입하기 입력 창: 사용자 입력을 LangGraph Context에 주입, 다음 에이전트 발화 방향에 동적 반영.<br>지켜보기 버튼: 캐릭터 토의 관전 모드 유지.<br><br>**④ 백엔드 제어 및 위기 필터**<br>무한 루프 방지 및 API 비용 제어를 위해 최대 3턴 / 합산 1,200토큰 상한 적용 (REQ-NF-007).<br>상한 도달 시 오케스트레이터가 세션 강제 종료 후 합의된 위로 요약 카드 출력.<br>대화 중 위기 척도 감지 시 즉시 루프 중단 및 위로 발화 전환. |",
        ""
    )
]

# 6. 개별 ERD 개정
erd_path = os.path.join(docs_dir, "[개별] ERD_김한솔.md")
erd_replacements = [
    # 이너카운슬 테이블들 제거
    (
        "    INNER_COUNCIL_SESSION {\n        uuid    council_id PK\n        uuid    session_id FK\n        int     total_turns\n        int     total_tokens\n        bool    force_stopped\n        text    summary_card\n        datetime started_at\n        datetime ended_at\n    }\n\n    AGENT_TURN {\n        uuid    turn_id PK\n        uuid    council_id FK\n        string  agent_name\n        text    content\n        int     token_count\n        int     turn_index\n        datetime created_at\n    }",
        ""
    ),
    (
        "    CHAT_SESSION ||--o| INNER_COUNCIL_SESSION : \"triggers\"\n    INNER_COUNCIL_SESSION ||--o{ AGENT_TURN : \"has\"",
        ""
    ),
    # 엔티티 상세설명 지우기
    (
        "### INNER_COUNCIL_SESSION\n| 컬럼 | 설명 |\n| :--- | :--- |\n| `total_tokens` | 합산 토큰 사용량 (1,200 상한, REQ-NF-007) |\n| `force_stopped` | 토큰 상한 도달로 강제 종료 여부 |\n| `summary_card` | 3에이전트 합의 요약 카드 텍스트 |\n\n### AGENT_TURN\n| 컬럼 | 설명 |\n| :--- | :--- |\n| `agent_name` | haeon / geulung / dalkong |\n| `token_count` | 개별 발화 토큰 수 (max_tokens=150) |\n| `turn_index` | 발화 순서 인덱스 |",
        ""
    )
]

# 치환 실행
replace_in_file(reqs_path, reqs_replacements)
replace_in_file(plan_path, plan_replacements)
replace_in_file(sys_path, sys_replacements)
replace_in_file(seq_path, seq_replacements)
replace_in_file(screen_path, screen_replacements)
replace_in_file(erd_path, erd_replacements)

print("All file updates completed.")

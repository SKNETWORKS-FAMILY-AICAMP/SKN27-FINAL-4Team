```mermaid
flowchart TD
    A["① 진입 · 온보딩<br/>네이버 로그인 · 캐릭터 선택 · 프로필"] --> B["② 홈 · 기능 허브"]

    B --> C["마음 대화 · 챗봇<br/>감정분석 · TTS · MBTI 유도"]
    B --> D["카드 운세 · 타로<br/>RAG 카드 해석"]
    B --> E["마음 캘린더<br/>감정 기록 · 조회"]
    B --> F["마이페이지<br/>프로필 · 자가척도"]

    C --> G[("④ 데이터 저장 · PostgreSQL<br/>대화 · 감정 라벨 · 활동 · 프로필 · 19개 테이블")]
    D --> G
    E --> G
    F --> G

    G --> H["⑤ 마음 리포트<br/>감정 흐름 · 키워드 · 실천 추천"]
    G --> I["⑥ MBTI 성향 분석<br/>월간 배치 · 다중 LLM 점수화"]

    H --> J["⑦ 사용자에게 환원 → 재방문"]
    I --> J
    J -. "선순환" .-> B

    classDef core fill:#E4EFEA,stroke:#1F6E5E,stroke-width:2px,color:#14352c;
    classDef step fill:#F4EEE3,stroke:#D8CBB6,stroke-width:1.5px,color:#2E2A26;
    class C,H,I,J core;
    class A,B,D,E,F,G step;
    
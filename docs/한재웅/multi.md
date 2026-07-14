
```mermaid
flowchart TD
    START["사용자 요청<br/>GET /api/report/generate/"] --> VIEW["MindReportGenerateAPIView<br/>views.py"]

    VIEW --> AUTH{"인증 사용자 여부"}
    AUTH -->|"인증됨"| USER["request.user 사용"]
    AUTH -->|"미인증 테스트 상태"| FIRSTUSER["DB 첫 번째 user 사용"]
    FIRSTUSER --> USER

    USER --> PERIOD["리포트 대상 기간 계산<br/>주간 기본 + 월말 주간이면 월간도 생성"]

    PERIOD --> WAG1["1. 데이터 조회·기준 충족 판단 에이전트<br/>collection.py + criteria_service.py"]
    WAG1 --> W1["주간 사용자 메시지 수 조회<br/>ChatMessage role=user"]
    W1 --> W2{"주간 기준 충족?<br/>5개 이상"}

    W2 -->|"미충족"| WFB["데이터 부족 보완 에이전트<br/>fallback_service.py"]
    WFB --> WFB1["UserProfile 조회<br/>age / gender / hobbies / interests"]
    WFB1 --> WFB2["FallbackWebAgent<br/>트렌드 콘텐츠·환기 활동 추천"]
    WFB2 --> WFB3["부족 데이터용 fallback 리포트 생성"]
    WFB3 --> SAVE_FB_W["MindReport 저장<br/>is_fallback=True"]

    W2 -->|"충족"| FLOW_W["MindReportFlowService.run<br/>period_type=week"]

    FLOW_W --> AG1W["1. 데이터 조회·기준 충족 판단 에이전트<br/>MindReportDataCollector"]
    AG1W --> COLDATA_W["기간 내 source_messages 수집<br/>collect_source_messages"]
    COLDATA_W --> ELIG_W["생성 기준 재검증<br/>eligibility 포함"]

    ELIG_W --> AG2W["2. 감정 점수화·시계열 분석·감정패턴 분류 에이전트<br/>scoring.py + emotion_flow.py"]
    AG2W --> SCORE_W["일자별 감정 점수화<br/>MindReportScoringService"]
    SCORE_W --> FLOW_ANALYSIS_W["시계열 감정 흐름 분석<br/>analyze_emotion_flow"]
    FLOW_ANALYSIS_W --> PATTERN_W{"감정 패턴 분류"}

    PATTERN_W -->|"score_upward"| UP_W["점수 상향<br/>회복 유지 방향"]
    PATTERN_W -->|"score_maintenance"| MAINTAIN_W{"점수 유지 세부 유형"}
    PATTERN_W -->|"score_volatile"| VOL_W["감정 변동성<br/>리듬 안정화 방향"]
    PATTERN_W -->|"score_downward"| DOWN_W["점수 하향<br/>부담 완화 방향"]

    MAINTAIN_W -->|"green_maintenance"| GREEN_W["초록 유지<br/>긍정 루틴 유지"]
    MAINTAIN_W -->|"gray_maintenance"| GRAY_W["회색 유지<br/>환기 활동 추가"]
    MAINTAIN_W -->|"red_maintenance"| RED_W["빨강 유지<br/>부담 낮은 회복"]

    UP_W --> ALT_W["흐름별 대안 후보 구성<br/>build_alternative_plan"]
    GREEN_W --> ALT_W
    GRAY_W --> ALT_W
    RED_W --> ALT_W
    VOL_W --> ALT_W
    DOWN_W --> ALT_W

    ALT_W --> AG3W["3. 원인 키워드 도출·분류 에이전트<br/>keyword_candidates.py + cause_keywords.py"]
    AG3W --> KEY_W["키워드 후보 추출<br/>MindReportKeywordExtractor"]
    KEY_W --> CAUSE_W["스트레스·이완 원인 분류<br/>MindReportCauseClassifier"]
    CAUSE_W --> LABEL_W["라벨 표시 정책 결정<br/>apply_label_display_policy"]

    LABEL_W --> AG4W["4. 분석 근거 문장·실천 대안 생성 에이전트<br/>narrative.py + alternatives.py"]
    AG4W --> NARR_W["분석 문장 생성<br/>MindReportNarrativeGenerator"]
    NARR_W --> FORMAT_W["프론트 포맷 변환<br/>format_for_frontend"]
    FORMAT_W --> AG5W["5. 리포트 검증 에이전트<br/>validation.py 신규 추가"]

    AG5W --> DV_W["데이터 검증<br/>기간·기준·근거 메시지 존재 확인"]
    AG5W --> AV_W["분석 검증<br/>점수 흐름·패턴·키워드 근거 확인"]
    AG5W --> SV_W["안전성 검증<br/>진단 단정·위험 신호·개인정보 확인"]
    AG5W --> FV_W["출력 형식 검증<br/>프론트 필드·타입·빈 값 확인"]

    DV_W --> VR_W{"검증 결과"}
    AV_W --> VR_W
    SV_W --> VR_W
    FV_W --> VR_W

    VR_W -->|"passed"| SAVE_W["MindReport 저장<br/>is_fallback=False"]
    VR_W -->|"needs_revision"| REV_W["수정 요청 생성<br/>문제 항목 전달"]
    REV_W --> AG4W
    VR_W -->|"blocked"| SAFE_W["안전 fallback 리포트 생성"]
    SAFE_W --> SAVE_FB_W

    PERIOD --> MONTH_CHECK{"이번 주가 월말 주간인가?"}
    MONTH_CHECK -->|"아니오"| RETURN
    MONTH_CHECK -->|"예"| MAG1["월간 데이터 조회·기준 충족 판단 에이전트"]
    MAG1 --> M1["월간 사용자 메시지 수 조회"]
    M1 --> M2{"월간 기준 충족?<br/>20개 이상"}

    M2 -->|"미충족"| MFB["월간 데이터 부족 보완 에이전트<br/>fallback_service.py"]
    MFB --> MFB1["UserProfile + MBTI 정보 조회"]
    MFB1 --> MFB2["FallbackWebAgent<br/>월간용 환기 활동 추천"]
    MFB2 --> MFB3["월간 fallback 리포트 생성"]
    MFB3 --> SAVE_FB_M["MindReport 저장<br/>is_fallback=True"]

    M2 -->|"충족"| FLOW_M["MindReportFlowService.run<br/>period_type=month"]
    FLOW_M --> MAG2["월간 1~4번 에이전트 동일 실행<br/>수집 → 감정분석 → 키워드분류 → 문장생성"]
    MAG2 --> MAG5["월간 리포트 검증 에이전트"]
    MAG5 --> MVR{"검증 결과"}
    MVR -->|"passed"| SAVE_M["MindReport 저장<br/>is_fallback=False"]
    MVR -->|"needs_revision"| MREV["수정 요청 생성"]
    MREV --> MAG2
    MVR -->|"blocked"| SAFE_M["안전 fallback 리포트 생성"]
    SAFE_M --> SAVE_FB_M

    SAVE_W --> RETURN["Response 반환<br/>reports 배열"]
    SAVE_FB_W --> RETURN
    SAVE_M --> RETURN
    SAVE_FB_M --> RETURN

    RETURN --> UI["Vue 마음 리포트 화면"]
    UI --> OUT1["감정 일기"]
    UI --> OUT2["스트레스 원인 라벨"]
    UI --> OUT3["이완 원인 라벨"]
    UI --> OUT4["분석 근거 문장"]
    UI --> OUT5["실천 대안"]
    UI --> OUT6["저장·공유"]

    MEM[("사용자 프로필·UserMemory")] -.참조.-> WFB1
    MEM -.개인화 참조.-> AG4W

    WEB[("검색 API / Web Agent")] -.데이터 부족 보완.-> WFB2
    WEB -.데이터 부족 보완.-> MFB2

    VDB[("심리이론 Vector DB<br/>추후 확장")] -.근거 검색.-> AG4W
    VDB -.근거 검색.-> MAG2
    ```
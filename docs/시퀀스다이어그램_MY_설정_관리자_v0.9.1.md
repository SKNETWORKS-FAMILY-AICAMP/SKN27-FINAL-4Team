# 시퀀스 다이어그램 설계안 v2

최신 요구사항 정의서 v8과 기존 HWPX 원문을 함께 반영한 개편안이다. 기존 HWPX의 핵심 맥락인 `마이페이지 메인 -> 프로필/리포트/개인 분석/설정 이동`과 `대화기록 기반 MBTI/취향 분석 파이프라인`은 유지하고, v8 요구사항에 맞지 않는 이전 항목은 제외했다.

## 개편 기준

- 유지: 마이페이지 메인 메뉴, 프로필 조회/수정, 리포트 보관함 연결, MBTI/취향 분석의 대화기록 기반 처리 흐름.
- 보강: 정적 방 일러스트 배경 위 클릭 가능 아티팩트, 키보드 포커스, 작은 화면 대체 메뉴, 로딩 실패 재시도, 빈 상태 안내, 커뮤니티, 웹 설정, 최소 관리자 운영.
- 제외: 시크릿챗 기본 설정, 결과카드 공개범위/외부 공유 설정, 상세 캐릭터 프롬프트 버전 관리, 서비스 지표 대시보드, 상세 모델 드리프트 모니터링.
- 원칙: 사용자가 별도 분석 요청을 누르는 구조가 아니라, 분석 화면 진입 시 최신 결과를 보여주고 필요할 때 시스템이 자동 갱신한다.

## 1. 정적 방 일러스트 기반 메인 메뉴 및 기능 진입

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Web as 웹 클라이언트
    participant Auth as 인증 서비스
    participant My as 마이페이지 서비스
    participant Route as 라우터
    participant Page as 대상 페이지

    User->>Web: 마이페이지 진입
    Web->>Auth: 로그인 세션 확인
    Auth-->>Web: 세션 유효
    Web->>My: 메인 메뉴 배경과 아티팩트 매핑 요청
    My-->>Web: 정적 방 일러스트, 클릭 가능 영역, 대체 메뉴 정보
    Web-->>User: 정적 아이소메트릭 방 이미지 표시
    Web-->>User: 이미지 위에 프로필, 리포트, MBTI, 취향, 설정 핫스팟 배치

    alt 작은 화면 또는 이미지 조작이 어려운 환경
        Web-->>User: 동일 기능을 목록 또는 그리드 메뉴로 함께 제공
    end

    User->>Web: 아티팩트 클릭 또는 키보드 선택
    Web-->>User: 선택/호버/포커스 피드백 표시
    Web->>Route: 대상 페이지 이동 요청
    Route->>Page: 페이지 로딩

    alt 로딩 성공
        Page-->>Route: 준비 완료
        Route-->>Web: 페이지 전환 완료
        Web-->>User: 선택한 기능 페이지 표시
    else 로딩 실패
        Page-->>Route: 로딩 실패
        Route-->>Web: 오류 상태 반환
        Web-->>User: 오류 메시지와 재시도 버튼 표시
    end
```

## 2. 프로필 조회 및 수정

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Web as 웹 클라이언트
    participant Profile as 프로필 서비스
    participant Onboarding as 온보딩 데이터
    participant Personalize as 대화 개인화 서비스
    participant DB as PostgreSQL

    User->>Web: 프로필 페이지 진입
    Web->>Profile: 프로필 조회 요청
    Profile->>Onboarding: 온보딩 기준 항목 조회
    Onboarding-->>Profile: 이름, 캐릭터, MBTI, 성별, 나이, 상태, 키워드, 관심 분야, 취미
    Profile-->>Web: 항목별 프로필 데이터
    Web-->>User: 프로필 목록과 수정 가능 항목 표시

    opt 수정 가능한 항목 변경
        User->>Web: 항목 수정 후 저장
        Web->>Profile: 수정값 저장 요청
        Profile->>Profile: 온보딩 기준과 충돌 여부 검증
        alt 검증 성공
            Profile->>DB: 프로필 변경 저장
            Profile->>Personalize: 대화 개인화 설정 즉시 갱신
            Personalize-->>Profile: 반영 완료
            Profile-->>Web: 저장 완료
            Web-->>User: 변경된 프로필 즉시 표시
        else 검증 실패
            Profile-->>Web: 실패 사유 반환
            Web-->>User: 수정 실패 안내
        end
    end
```

## 3. 리포트 보관함 연결

마음리포트의 주간·월간 캘린더, 일별 대표 감정 이모지, 리포트 상세 조회, 발급 기준, 공유 기능은 마음리포트 모듈 정책을 따른다. 마이페이지는 진입 동선과 초기 연결 상태만 담당한다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Web as 웹 클라이언트
    participant My as 마이페이지 서비스
    participant Report as 마음리포트 모듈

    User->>Web: 리포트 보관함 아티팩트 선택
    Web->>My: 보관함 진입 가능 여부 확인
    My->>Report: 보관함 초기 상태 요청

    alt 보관함 데이터 있음
        Report-->>My: 보관함 페이지 진입 정보
        My-->>Web: 이동 가능 상태 반환
        Web-->>User: 마음리포트 보관함 페이지 표시
    else 리포트 없음
        Report-->>My: 빈 상태
        My-->>Web: 빈 상태 안내와 생성 유도 문구
        Web-->>User: 빈 상태 안내 표시
    else 조회 실패
        Report-->>My: 조회 오류
        My-->>Web: 오류 메시지와 재시도 정보
        Web-->>User: 오류 안내 및 재시도 버튼 표시
    end
```

## 4. 개인 분석 결과 표시 및 자동 갱신

MBTI 분석과 취향 분석은 사용자가 별도 분석 버튼을 누르지 않는다. 각 분석 페이지에 들어가면 최신 저장 결과를 먼저 보여주고, 결과가 없거나 갱신 조건을 충족하면 백그라운드 분석을 실행한다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Web as 웹 클라이언트
    participant Analysis as 개인 분석 서비스
    participant DB as PostgreSQL
    participant Queue as 분석 큐
    participant Worker as 분석 워커
    participant Policy as 표현 정책 필터

    User->>Web: MBTI 또는 취향 분석 페이지 진입
    Web->>Analysis: 분석 대시보드 데이터 요청
    Analysis->>DB: 최신 분석 결과와 갱신 상태 조회

    alt 최신 결과 있음
        DB-->>Analysis: 저장된 결과와 근거 리포트
        Analysis->>Policy: 비의료 참고 정보 문구 검토
        Policy-->>Analysis: 표시 가능한 문구
        Analysis-->>Web: 대시보드 데이터 반환
        Web-->>User: 분석 결과 표시
    else 결과 없음 또는 갱신 필요
        DB-->>Analysis: 결과 없음 또는 만료 상태
        Analysis->>Queue: 자동 분석 작업 등록
        Analysis-->>Web: 준비 중 상태와 다음 갱신 조건
        Web-->>User: 분석 준비 중 안내 표시
        Queue-->>Worker: 분석 작업 전달
        Worker->>DB: 분석 결과와 근거 저장
    else 데이터 부족
        DB-->>Analysis: 분석 기준 미충족
        Analysis-->>Web: 분석 불가 사유와 다음 갱신 가능 조건
        Web-->>User: 분석 불가 안내 표시
    end
```

## 5. MBTI 분석 워커 파이프라인

HWPX의 상세 파이프라인을 유지하되, 화면용 시퀀스에서는 처리 단계를 한눈에 볼 수 있는 수준으로 묶었다.

```mermaid
sequenceDiagram
    participant Worker as MBTI 분석 워커
    participant Chat as 자유형 대화기록
    participant DB as PostgreSQL
    participant ML as ML 모델
    participant Vec as pgvector/VectorDB
    participant Graph as GraphDB
    participant LLM as LLM 설명 생성기
    participant Policy as 표현 정책 필터

    Worker->>Chat: 기간별 일반 자유형 대화기록 조회
    Chat-->>Worker: 대화 로그
    Worker->>Worker: 사용자 발화 추출 및 전처리
    Worker->>DB: 원문 발화와 전처리 메타데이터 저장

    Worker->>ML: 성향 신호 탐지 및 4축 점수 추정
    ML-->>Worker: 성향 신호, E/I, S/N, T/F, J/P 점수
    Worker->>Vec: 발화 임베딩 저장
    Worker->>Graph: User-Period-Utterance-Signal-Axis-Evidence 관계 저장
    Worker->>DB: 축별 점수와 최근 MBTI 유사 성향 저장

    Worker->>Vec: 유사 근거 발화 검색
    Vec-->>Worker: 유사 발화 후보
    Worker->>Graph: 근거 관계 탐색
    Graph-->>Worker: 근거 관계
    Worker->>LLM: 근거 기반 자기이해 설명 생성
    LLM-->>Worker: 근거 리포트 초안
    Worker->>Policy: 진단명, 질병명, 위험 등급 표현 제거
    Policy-->>Worker: 안전한 참고 문구
    Worker->>DB: 최종 성향, 변화 경향, 근거 리포트, 방사형 그래프 데이터 저장
```

## 6. 취향 및 선호 분석 워커 파이프라인

```mermaid
sequenceDiagram
    participant Worker as 취향 분석 워커
    participant Chat as 자유형 대화기록
    participant DB as PostgreSQL
    participant ML as ML/통계/Rule 엔진
    participant Vec as pgvector/VectorDB
    participant Graph as GraphDB
    participant LLM as LLM 리포트 생성기
    participant Policy as 표현 정책 필터

    Worker->>Chat: 기간별 자유형 대화기록 조회
    Chat-->>Worker: 대화 로그
    Worker->>Worker: 사용자 발화 추출 및 전처리
    Worker->>DB: 원문 발화 저장
    Worker->>ML: 발화 유형, 관심 주제, 감정 반응, 선호 표현, 콘텐츠 취향 추출
    ML-->>Worker: 신호 추출 결과
    Worker->>Vec: 발화 임베딩 저장
    Worker->>Graph: 사용자-발화-신호-주제-감정-취향 관계 저장

    Worker->>Worker: 유사 신호 통합 및 반복성·최근성·강도 점수화
    Worker->>DB: 사용자 취향 프로파일 저장
    Worker->>Graph: 사용자-프로파일-근거 관계 저장
    Worker->>Vec: 유사 근거 발화 검색
    Vec-->>Worker: 유사 근거
    Worker->>LLM: 근거 기반 취향 리포트 생성
    LLM-->>Worker: 리포트 초안
    Worker->>Policy: 자기이해와 생활 제안 중심 문구 검토
    Policy-->>Worker: 표시 가능한 문구
    Worker->>DB: 최근 관심사, 선호 경향, 변화 추이, 근거 리포트 저장
```

## 7. 커뮤니티 자유게시판 및 신고

```mermaid
sequenceDiagram
    actor User as 가입 사용자
    participant Web as 웹 클라이언트
    participant Community as 커뮤니티 서비스
    participant Safety as 안전 안내/신고 서비스
    participant DB as PostgreSQL

    User->>Web: 자유게시판 진입
    Web->>Community: 게시글 목록 요청
    Community->>DB: 제목, 작성자 닉네임, 작성일, 댓글 수 조회
    DB-->>Community: 게시글 목록
    Community-->>Web: 목록 반환
    Web-->>User: 자유게시판 목록 표시

    opt 게시글 작성
        User->>Web: 제목과 본문 입력
        Web-->>User: 개인정보·민감 상담 내용 공개 주의 안내
        Web->>Community: 게시글 저장 요청
        Community->>DB: 게시글 저장
        Community-->>Web: 작성 완료
    end

    opt 댓글 작성 또는 신고
        User->>Web: 댓글 작성 또는 신고 선택
        alt 댓글 작성
            Web->>Community: 댓글 저장 요청
            Community->>DB: 댓글 저장
        else 신고
            Web->>Safety: 게시글/댓글 신고 접수
            Safety->>DB: 관리자 확인 대상 상태로 저장
            Safety-->>Web: 신고 접수 완료
        end
    end
```

## 8. 사용자간 1:1 웹 채팅

```mermaid
sequenceDiagram
    actor User as 사용자
    actor Peer as 상대 사용자
    participant Web as 웹 클라이언트
    participant Chat as 사용자간 채팅 서비스
    participant Safety as 차단/신고 서비스
    participant DB as PostgreSQL

    User->>Web: 1:1 채팅 시작
    Web->>Chat: 대화방 생성 또는 조회
    Chat->>DB: 차단 상태와 기존 대화 확인
    alt 차단 상태 아님
        DB-->>Chat: 대화 가능
        Chat-->>Web: 대화 목록, 메시지 상태, 읽음 여부
        Web-->>User: 채팅 화면 표시
        User->>Web: 메시지 입력
        Web->>Chat: 메시지 전송
        Chat->>DB: 메시지와 전송 시간 저장
        Chat-->>Peer: 새 메시지 전달
    else 차단 상태
        DB-->>Chat: 대화 제한
        Chat-->>Web: 채팅 제한 상태
        Web-->>User: 차단으로 인한 제한 안내
    end

    opt 차단 또는 신고
        User->>Web: 상대 차단 또는 메시지 신고
        Web->>Safety: 차단/신고 처리 요청
        Safety->>DB: 차단 목록 또는 신고 상태 저장
        Safety-->>Web: 처리 결과
    end

    Web-->>User: 위기 상담·의료 판단 대체 불가 안내 표시
```

## 9. 설정 페이지

최신 요구사항은 설정을 웹 계정·전역 UI 설정 중심으로 재정리한다. 다른 기능의 입력값을 설정에서 직접 수정하지 않고, 필요 시 해당 기능 화면으로 이동 안내만 제공한다.

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Web as 웹 클라이언트
    participant Settings as 설정 서비스
    participant Session as 세션 서비스
    participant Community as 커뮤니티 서비스
    participant DB as PostgreSQL

    User->>Web: 설정 페이지 진입
    Web->>Settings: 계정 기본 정보와 설정값 조회
    Settings->>DB: 로그인 계정, 닉네임, 가입 방식, 가입일, 언어, 테마, 접근성 조회
    DB-->>Settings: 설정 데이터
    Settings-->>Web: 설정 화면 데이터
    Web-->>User: 계정 정보와 설정 항목 표시

    opt 언어·테마·접근성 변경
        User->>Web: 언어, 테마, 글자 크기, 애니메이션 최소화, 고대비 변경
        Web->>Settings: 설정 저장 요청
        alt 저장 성공
            Settings->>DB: 로그인 계정 기준 설정 저장
            Settings-->>Web: 저장 완료
            Web->>Web: 새로고침 없이 공통 UI에 즉시 반영
            Web-->>User: 완료 토스트 표시
        else 저장 실패
            Settings-->>Web: 오류 원인과 재시도 정보
            Web-->>User: 오류 메시지와 재시도 안내
        end
    end

    opt 세션 또는 차단 사용자 관리
        User->>Web: 최근 접속 이력/차단 사용자 목록 조회
        Web->>Session: 브라우저 세션 조회 또는 종료 요청
        Web->>Community: 차단 사용자 목록 조회 또는 해제 요청
        Session-->>Web: 세션 처리 결과
        Community-->>Web: 차단 처리 결과
        Web-->>User: 변경 결과 표시
    end

    opt 설정값 초기화
        User->>Web: 설정값 초기화 요청
        Web-->>User: 초기화 대상과 복구 가능 여부 안내
        User->>Web: 초기화 확인
        Web->>Settings: 기본값 복원 요청
        Settings->>DB: 언어, 테마, 접근성, 화면 표시 방식 기본값 저장
        Settings-->>Web: 초기화 완료
        Web->>Web: 현재 화면에 즉시 반영
    end
```

## 10. 계정 탈퇴 및 데이터 삭제

```mermaid
sequenceDiagram
    actor User as 사용자
    participant Web as 웹 클라이언트
    participant Account as 계정 서비스
    participant DB as PostgreSQL
    participant Graph as GraphDB
    participant Vec as pgvector/VectorDB
    participant Mail as 이메일 서비스

    User->>Web: 계정 탈퇴 요청
    Web->>Account: 탈퇴 전 안내 요청
    Account-->>Web: 삭제 대상과 복구 불가 안내
    Web-->>User: 대화기록, 결과카드, 메모리, 개인화 설정, 웹 설정값 삭제 안내
    User->>Web: 최종 탈퇴 확인

    Web->>Account: 탈퇴 처리 요청
    Account->>DB: 계정 상태 변경 및 연결 데이터 삭제
    Account->>Graph: 사용자 관련 관계 삭제
    Account->>Vec: 사용자 발화 임베딩 삭제
    opt 이메일 확인 필요
        Account->>Mail: 탈퇴 확인 안내 발송
        Mail-->>Account: 발송 결과
    end
    Account-->>Web: 탈퇴 완료
    Web-->>User: 삭제 완료 화면 표시
```

## 11. 관리자 접근 및 회원 처리

```mermaid
sequenceDiagram
    actor Admin as 관리자
    participant AdminWeb as 관리자 화면
    participant Auth as 관리자 인증 서비스
    participant Member as 회원 관리 서비스
    participant Audit as 작업 이력
    participant DB as PostgreSQL

    Admin->>AdminWeb: 관리자 로그인
    AdminWeb->>Auth: 일반 사용자와 분리된 관리자 인증
    Auth-->>AdminWeb: 관리자 권한 확인
    AdminWeb->>Audit: 로그인 이력 기록
    AdminWeb-->>Admin: 관리자 메뉴 표시

    Admin->>AdminWeb: 회원 목록 조회·검색
    AdminWeb->>Member: 회원 ID, 닉네임, 가입일, 최근 접속일, 상태 조건 전달
    Member->>DB: 회원 목록 조회
    DB-->>Member: 회원 목록
    Member->>Member: 개인정보 기본 마스킹 및 최소 항목만 구성
    Member->>Audit: 조회 작업 기록
    Member-->>AdminWeb: 회원 목록 반환

    opt 계정 상태 또는 탈퇴 요청 처리
        Admin->>AdminWeb: 활성, 일시 정지, 탈퇴 처리 상태 변경
        AdminWeb->>Member: 처리 사유와 상태 변경 요청
        Member->>DB: 계정 상태 변경
        Member->>Audit: 처리 사유와 처리 일시 기록
        Member-->>AdminWeb: 처리 완료
    end

    AdminWeb-->>Admin: 민감 대화 원문은 노출하지 않음
```

## 12. 관리자 안전·오류·커뮤니티 확인

```mermaid
sequenceDiagram
    actor Admin as 관리자
    participant AdminWeb as 관리자 화면
    participant Ops as 운영 확인 서비스
    participant Safety as 안전 이벤트 서비스
    participant Report as 분석/리포트 모듈
    participant Community as 커뮤니티 서비스
    participant DB as PostgreSQL

    Admin->>AdminWeb: 운영 확인 메뉴 진입
    AdminWeb->>Ops: 안전 이벤트, 분석 오류, 신고 내역 요약 요청

    Ops->>Safety: 위기 신호 감지 이벤트 조회
    Safety-->>Ops: 감지 유형과 사용자 안내 처리 상태
    Ops->>Report: 감정 분석, 척도 추정, 마음리포트 성공·실패 상태 조회
    Report-->>Ops: 모듈별 오류 상태와 재처리 필요 여부
    Ops->>Community: 신고된 게시글, 댓글, 1:1 메시지 조회
    Community-->>Ops: 신고 사유와 처리 상태
    Ops-->>AdminWeb: 운영 확인 목록 반환
    AdminWeb-->>Admin: 원본 대화와 민감 분석값 없이 상태만 표시

    opt 확인 또는 처리
        Admin->>AdminWeb: 이벤트 확인 완료 또는 신고 처리
        AdminWeb->>Ops: 확인 완료, 숨김 처리, 신고 반려 요청
        Ops->>DB: 처리 상태 저장
        Ops-->>AdminWeb: 처리 결과
    end
```

## 13. 관리자 콘텐츠·공지 관리

```mermaid
sequenceDiagram
    actor Admin as 관리자
    participant AdminWeb as 관리자 화면
    participant Content as 콘텐츠 관리 서비스
    participant Preview as 미리보기/금칙어 검사
    participant Notice as 공지 서비스
    participant DB as PostgreSQL

    Admin->>AdminWeb: 기본 콘텐츠 등록·수정·비활성화
    AdminWeb->>Content: 운세 콘텐츠, 결과카드 문구 템플릿, 안전 안내 문구 전달
    Content->>Preview: 미리보기와 금칙어 확인 요청
    Preview-->>Content: 검수 결과
    alt 검수 통과
        Content->>DB: 콘텐츠 저장
        Content-->>AdminWeb: 저장 완료
    else 검수 실패
        Content-->>AdminWeb: 수정 필요 항목 반환
    end

    Admin->>AdminWeb: 공지 또는 점검 안내 등록·수정·삭제
    AdminWeb->>Notice: 노출 기간, 제목, 내용, 영향 범위 전달
    alt 서비스 이용 제한이 있는 점검 안내
        Notice->>DB: 점검 안내 저장
    else 일반 공지
        Notice->>DB: 서비스 공지 저장
    end
    Notice-->>AdminWeb: 처리 완료
```

## 요구사항 부합 메모

- `F-MY-001 정적 방 일러스트 기반 메인 메뉴`: 정적 아이소메트릭 방 이미지, 이미지 위 클릭 가능 아티팩트, 클릭/키보드 선택, 포커스 피드백, 작은 화면 목록·그리드 대체 메뉴, 로딩 실패 재시도를 포함한다.
- `F-MY-002 프로필 조회`: 온보딩 정보 기준 조회와 수정 후 마이페이지·대화 개인화 즉시 반영을 포함한다.
- `F-MY-003 리포트 보관함 연결`: 마음리포트 모듈 내부 정책을 침범하지 않고, 마이페이지 담당인 진입 동선·빈 상태·오류 재시도만 포함한다.
- `F-MY-004 대화기록 기반 MBTI 성향 추정 및 경향 분석`: HWPX의 MBTI 분석 파이프라인을 유지하되 화면 표시 흐름과 워커 흐름을 분리했다.
- `F-MY-005 대화기록 기반 취향 및 선호 경향 분석`: HWPX의 취향 분석 파이프라인을 유지하고 데이터 부족 안내를 추가했다.
- `F-COM-001 자유게시판 글 목록·작성`, `F-COM-002 게시글 상세·댓글·신고`, `F-COM-003 사용자간 1:1 웹 채팅`: 게시판, 댓글, 신고, 채팅, 차단을 반영했다.
- `F-SET-001 계정 기본 정보 조회`, `F-SET-002 언어·테마 설정`, `F-SET-003 화면 접근성 설정`, `F-SET-004 로그인 세션 관리`, `F-SET-005 설정값 초기화`, `F-SET-006 커뮤니티 차단 사용자 관리`, `F-SET-007 계정 탈퇴·데이터 삭제`, `NF-SET-001 설정 즉시 반영`: 웹 설정 중심으로 반영했고, v8에 없는 시크릿챗 기본 설정은 제외했다.
- `F-ADM-001 회원 목록 조회·검색`, `F-ADM-002 계정 상태·탈퇴 요청 처리`, `F-ADM-003 안전 이벤트 확인`, `F-ADM-004 분석·리포트 오류 확인`, `F-ADM-005 커뮤니티 신고 내역 확인`, `F-ADM-006 기본 콘텐츠 관리`, `F-ADM-007 공지·점검 안내 등록`, `F-ADM-008 관리자 접근 및 작업 이력 확인`: 최소 관리자 운영 범위로 재구성했고, 민감 대화 원문과 개인별 민감 분석값은 관리자 화면에 노출하지 않도록 했다.

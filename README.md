# 🍀 빈틈사이 (Bintheum-Sai)
> **"편하게 털어놓는 수다 같지만, 사실은 정밀한 마음 케어."**  
> 사용자가 캐릭터와 편하게 일상 대화를 나누는 동안, 백엔드의 **숨은 척도 엔진**이 6종 임상 척도를 추정하고 다정한 위로 카드와 맞춤형 웰니스 솔루션을 제공하는 **비의료 개인 맞춤형 웰니스 케어 플랫폼**입니다.

---

## 🛠️ 개발 환경 (Tech Stack)
- **Language**: Python 3.12
- **Backend Framework**: Django
- **Agent Orchestrator**: LangGraph (Multi-Agent System)
- **Database**: 
  - **PostgreSQL**: 트랜잭션, 회원, 대화 로그, 척도 채점 이력 보관

---

## 📂 프로젝트 폴더 구조 (Directory Structure)

```text
SKN27-FINAL-4Team/
|-- .env.example                     # 환경 변수 템플릿
|-- .gitignore                       # Git 제외 파일 설정
|-- README.md                        # 본 프로젝트 메인 리드미
|-- docker-compose.yml               # PostgreSQL 컨테이너 인프라 구성
|-- ai/                              # 🧠 AI 모델 학습 및 가중치 관리 공간
|   `-- README.md
|-- app/                             # 💻 Django 웹 서비스 애플리케이션 소스 코드
|   |-- Dockerfile
|   |-- README.md
|   `-- backend/requirements.txt      # 백엔드 의존성 패키지
|-- data/                            # 📊 모델 검증 및 안전성 테스트셋 데이터 보관
|   |-- safety_redteam_set.json      # 극단 신호 탐지용 안전 가드레일 레드팀셋
|   `-- scale_gold_set.json          # 간접 척도 추정 알고리즘 검증용 골드셋
|-- docs/                            # 📑 프로젝트 기획 및 설계 산출물 (정본)
|   |-- README.md
|   |-- [기획] WBS_양식_27기_4팀.xlsx
|   |-- [통합] WBS 계획서.md
|   |-- [통합] 시스템 설계서.md
|   |-- [통합] 요구사항 정의서.md
|   |-- [통합] 종합 기획안.md
|   |-- [통합] 화면설계서 명세.md
|   `-- 학습 결과서 — 감정분류 (KcELECTRA).md
|-- etl/                             # 🔄 데이터 전처리 및 초기 마이그레이션(ETL) 스크립트
|   |-- README.md
|   |-- load_scales_to_postgres.py   # 임상 척도 질문 문항 로더
|   `-- seed_postgres_static_data.py # PostgreSQL 초기 정적 마스터 데이터 적재
|-- prompts/                         # 📝 캐릭터 에이전트별 시스템 프롬프트 정의
|   |-- dalkong_prompt.json          # 달콩이 (코치형 / ACT 기반)
|   |-- greung_prompt.json           # 그릉이 (직면형 / 마음챙김 기반)
|   `-- haeon_prompt.json            # 해온이 (위로형 / 내러티브 기반)
|-- storage/                         # 📦 로컬 데이터셋 및 정적 리소스 보관함
|   |-- README.md
|   `-- 마시는_차_추천_데이터셋.json     # 64종 힐링 차 원천 메타데이터
`-- test/                            # 🧪 개별 프로토타이핑 및 기능 단위 테스트 공간
    |-- README.md
    `-- 감성대화_토큰나이저.ipynb
```

---

## ⚙️ 주요 디렉토리 상세 역할

### 1. `ai/` (AI & ML)
- KcELECTRA 기반 실시간 감정 분류 모델 파인튜닝 코드 및 최종 가중치 모델이 위치합니다.
- 사용자의 대화 맥락에서 6종 임상 척도를 추정하기 위한 머신러닝(XGBoost) 파이프라인과 특징 추출 모듈을 다룹니다.

### 2. `app/` (Django Backend Service)
- Django 기반의 RESTful API 서버입니다.
- 사용자 관리, 온보딩 흐름 제어, 실시간 챗봇 API 세션 관리, 이너 카운슬 LangGraph 오케스트레이션이 이루어지는 서비스의 심장부입니다.

### 3. `data/` (Dataset Validation & Safety)
- 챗봇 답변의 부적절하거나 유해한 표현을 걸러내기 위한 자체 **안전 레드팀셋**과, 6대 임상 척도의 정교한 간접 예측 보정을 수행하기 위한 **척도 골드셋**이 수록되어 있습니다.

### 4. `docs/` (System Design & Plan)
- 팀의 협업 프로세스를 관리하기 위한 WBS, PM 산출물(기획안, 요구사항 정의서, 화면설계서 명세) 및 시스템 아키텍처 다이어그램(Master ERD 및 시퀀스 흐름 마블링 마크다운)이 모여 있습니다.

### 5. `etl/` (Extract-Transform-Load Pipelines)
- 원천 JSON/CSV 데이터셋을 PostgreSQL 구조적 테이블로 정제하여 가공 적재하기 위한 초기 설정용 자동화 스크립트 집합입니다.

### 6. `prompts/` (Persona Prompt Engine)
- 다중 에이전트(LangGraph)로 구동되는 개별 캐릭터(해온이, 그릉이, 달콩이)의 개성 있는 말투, 특화 심리 이론 개입 규칙을 정의해 둔 System Prompt 파일들입니다.

### 7. `storage/` (Resources & Metadata)
- 외부 API 통신을 최소화하기 위해 플랫폼 내부에 내장한 64종 힐링 차의 성분, 카페인 함유 유무, 알레르기 유발 항원 등의 정적 메타데이터를 통합 보관합니다.

### 8. `test/` (Sandbox & Test Bed)
- 본격적인 모델 배포 전 데이터 토큰화 효율성 검증, 데이터셋 병합 분석 및 개별 프로토타입 작성용 주피터 노트북 샌드박스입니다.
# 🍀 빈틈사이 (Bintheum-Sai)
> **"편하게 털어놓는 수다 같지만, 사실은 정밀한 마음 케어."**  
> 사용자가 캐릭터와 편하게 일상 대화를 나누는 동안, 백엔드의 **숨은 척도 엔진**이 6종 임상 척도를 추정하고 다정한 위로 카드와 맞춤형 웰니스 솔루션을 제공하는 **비의료 개인 맞춤형 웰니스 케어 플랫폼**입니다.

---

## 🛠️ 개발 환경 (Tech Stack)
- **Language**: Python 3.12
- **Backend Framework**: Django
- **Agent Orchestrator**: LangGraph (Multi-Agent System)
- **Database**: PostgreSQL (트랜잭션, 회원, 대화 로그, 척도 채점 이력 보관)
- **Frontend**: Vue 3 + Vite

---

## 📂 프로젝트 폴더 구조 (Directory Structure)

```text
SKN27-FINAL-4Team/
|-- .env                             # 환경 변수 (로컬 전용 — git 제외)
|-- .gitignore                       # Git 제외 파일 설정
|-- README.md                        # 본 프로젝트 메인 리드미
|-- ai/                              # 🧠 LangGraph 에이전트 및 AI 모델 작업 공간
|   |-- agents/                      # 멀티에이전트 노드, 페르소나, 상태, LLM 설정
|   |-- emotion/                     # KcELECTRA + XGBoost 감정분류 파이프라인
|   |-- experiments/                 # 감정분류 개선 실험 노트북 및 결과
|   `-- scale/                       # 6종 임상 척도 간접 추정 모듈
|-- app/                             # 💻 Django 웹 서비스 애플리케이션
|   |-- Dockerfile
|   |-- backend/                     # Django REST API 서버 (챗봇, 인증, 온보딩 등)
|   `-- frontend/                    # Vue 3 + Vite 프론트엔드
|-- docs/                            # 📑 프로젝트 기획 및 설계 산출물
|   |-- 김한솔팀장/                   # 팀장 개별 문서
|   |-- 박송원/                       # 팀원 개별 문서
|   |-- 한재웅/                       # 팀원 개별 문서
|   `-- 화면설계서/                   # 전체 화면설계서
|-- etl/                             # 🔄 데이터 파이프라인 및 ETL 작업 공간
|   |-- data/                        # AI 학습 데이터셋 (AI Hub 파생물은 repo 미포함)
|   |-- datasets/                    # MBTI 등 원천 데이터셋
|   |-- scripts/                     # 데이터 처리 스크립트
|   |-- seed_postgres_static_data.py # PostgreSQL 정적 기초 데이터 시딩
|   `-- load_scales_to_postgres.py   # 심리 척도 6종 DB 적재
|-- storage/                         # 📦 인프라 설정 파일 보관
|   |-- docker-compose.yml           # PostgreSQL 컨테이너 구성 (루트에 복사해서 사용)
|   `-- DDL_MY_설정_관리자_insert_target_v0.9.1.sql
|-- test/                            # 🧪 팀원별 테스트 및 실험 공간
|   |-- hansol/                      # 김한솔
|   |-- jaewung/                     # 한재웅
|   |-- seongjin/                    # 성진
|   `-- songwon/                     # 박송원
```

---

## ⚙️ 주요 디렉토리 상세 역할

### 1. `ai/` (AI & ML)
- **agents/** : LangGraph 기반 멀티에이전트 시스템. 포리(pori)·까미(kkami)·토토(toto)·여울(yeoul) 4개 캐릭터 페르소나와 노드, 상태 관리가 위치합니다.
- **emotion/** : KcELECTRA 임베딩 + XGBoost 분류기 기반 실시간 감정분류 모델. 학습·추론·산출물(artifacts/)이 위치합니다.
- **scale/** : PHQ-9, GAD-7 등 6종 임상 척도 간접 추정 모듈입니다.

### 2. `app/` (Django Backend + Vue Frontend)
- Django REST API 서버와 Vue 3 + Vite 프론트엔드로 구성됩니다.
- 챗봇 세션, 사용자 인증, 온보딩, 마이페이지, 마음 리포트, 타로 등 서비스 앱이 위치합니다.

### 3. `docs/` (System Design & Plan)
- 팀 협업 산출물(기획안, 요구사항 정의서, 화면설계서 명세)과 팀원별 개별 설계 문서가 위치합니다.

### 4. `etl/` (Extract-Transform-Load Pipelines)
- 원천 데이터를 PostgreSQL에 적재하는 ETL 스크립트와 AI 학습 데이터셋이 위치합니다.

### 5. `storage/` (Infrastructure)
- `docker-compose.yml`을 루트에 복사해 `docker compose up -d --build`로 실행하세요.

### 6. `test/` (Sandbox)
- 팀원별 프로토타이핑 및 기능 단위 테스트 공간입니다.

---

## 🚀 실행 방법

```bash
# 1. storage/docker-compose.yml을 루트로 복사
cp storage/docker-compose.yml .

# 2. 환경 변수 설정
cp app/backend/.env.example app/backend/.env  # API 키 입력

# 3. Docker 실행
docker compose up -d --build
```

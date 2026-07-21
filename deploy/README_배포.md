# 빈틈사이 AWS 배포 가이드 (2026-07-21)

강사 견본 `django_on_aws`(ECR→ECS+CodeBuild) 패턴을 우리 스택에 맞춘 절차서.
콘솔 작업 순서대로 따라가면 된다. 리전은 전부 **서울(ap-northeast-2)**.

## 구조

```
[사용자] → ALB(:80) → ECS 태스크 [nginx(:80) → 프론트 dist 정적 서빙
                                          └→ /api·/admin·/media → gunicorn(:8000)]
                                   │
                     RDS PostgreSQL(pgvector) ── 원본 데이터
                     Neo4j AuraDB Free ───────── 그래프 장기 기억
                     S3 ──────────────────────── 감정모델 산출물(기동 시 다운로드)
                     SSM Parameter Store ─────── 시크릿(.env 대체)
```

## 0. 로컬 검증 (배포 전 반드시)

```bash
# 저장소 루트에서 — 프론트 빌드 포함 통합 이미지
docker build -f deploy/Dockerfile -t binteumsai .
docker run --rm -p 8080:80 --env-file app/backend/.env \
  -e PG_HOST=host.docker.internal -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_USER=neo4j -e NEO4J_PASSWORD=binteumsai_graph \
  -e ALLOWED_HOSTS='*' binteumsai
# http://localhost:8080 접속 → 로그인·채팅·기억 패널 확인
```

## 1. ECR — 이미지 저장소

콘솔 → ECR → 리포지토리 생성: `binteumsai-ecr` (프라이빗).
(buildspec.yml의 `IMAGE_REPO_NAME`과 이름 일치 필수)

## 2. S3 — 감정모델 산출물

1. 버킷 생성 (예: `binteumsai-artifacts`) — 퍼블릭 차단 유지
2. `ai/emotion/artifacts/` 내용물 업로드 (KcELECTRA 파인튜닝 폴더 artifacts_ft 포함 시 통째로)
3. 태스크 롤(아래 6번)에 이 버킷 `s3:GetObject`/`s3:ListBucket` 권한 부여

## 3. RDS — PostgreSQL + pgvector

1. RDS → 데이터베이스 생성 → PostgreSQL 15 이상, 버스터블(db.t3.micro~small)
2. DB 이름 `wellness_db`, 마스터 사용자/비밀번호 기록
3. 보안 그룹: ECS 태스크의 보안 그룹에서 5432 인바운드 허용 (퍼블릭 액세스 불필요)
4. 생성 후 쿼리 에디터/psql로: `CREATE EXTENSION IF NOT EXISTS vector;`

## 4. Neo4j — AuraDB Free (관리형, 무료)

1. https://neo4j.com/cloud/aura 에서 Free 인스턴스 생성 (AWS 서울 리전 선택 가능)
2. 접속 URI(`neo4j+s://xxxx.databases.neo4j.io`)와 비밀번호 기록
3. 별도 초기화 작업 없음 (제약조건은 앱이 기동 시 자동 생성)
- 대안: EC2 t3.small에 `docker run neo4j:5` (Free 한도 초과 시)

## 5. SSM Parameter Store — 시크릿

`app/backend/.env`의 값들을 SecureString으로 등록 (이름 예: `/binteumsai/OPENAI_API_KEY`).
**필수 목록** — 콘솔 태스크 정의에서 secrets로 주입:

| 이름 | 비고 |
|---|---|
| DJANGO_SECRET_KEY | 새로 생성 권장 |
| OPENAI_API_KEY | LLM·TTS·마음카드 |
| PG_PASSWORD | RDS 마스터 비번 |
| NEO4J_PASSWORD | AuraDB 비번 |
| NAVER_CLIENT_ID / NAVER_CLIENT_SECRET | OAuth |
| KAKAO_CLIENT_ID / KAKAO_CLIENT_SECRET | OAuth |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | OAuth |
| OPENWEATHERMAP_API_KEY | 날씨 |

## 6. ECS — 클러스터·태스크·서비스·ALB

1. 클러스터 생성 (Fargate)
2. **태스크 정의**: 컨테이너명 `binteumsai-container`(buildspec과 일치),
   이미지 = ECR URI, 포트 80, **CPU 1 vCPU / 메모리 4GB 이상**(KcELECTRA 로드)
3. 태스크 롤: S3 읽기(2번 버킷) + SSM 파라미터 읽기 권한
4. 환경변수 (secrets 외 평문 environment):

```
DEBUG=False
ALLOWED_HOSTS=<ALB DNS 이름>            # 예: binteumsai-alb-xxx.ap-northeast-2.elb.amazonaws.com
FRONTEND_BASE_URL=http://<ALB DNS 이름>  # 같은 도메인 (프론트·백 통합 서빙)
PG_HOST=<RDS 엔드포인트>
PG_PORT=5432
PG_DB=wellness_db
PG_USER=postgres
NEO4J_URI=neo4j+s://<AuraDB 호스트>
NEO4J_USER=neo4j
EMOTION_ARTIFACT_DIR=/artifacts
S3_ARTIFACTS_URI=s3://binteumsai-artifacts/artifacts
NAVER_REDIRECT_URI=http://<ALB DNS>/api/user/naver/callback   # 실제 콜백 경로로
KAKAO_REDIRECT_URI=... / GOOGLE_REDIRECT_URI=...              # 동일 요령
TTS_PROVIDER=openai   # 비용 아끼려면 off
```

5. **ALB** 생성 → 대상 그룹(IP, 포트 80, 헬스체크 경로 `/api/characters/` 등 200 나오는 경로) → 서비스 생성 시 연결
6. 서비스 생성 (원하는 태스크 수 1) → 기동 로그에서 migrate·collectstatic·산출물 동기화 확인

## 7. CodePipeline — CI/CD

1. CodeBuild 프로젝트: 소스 GitHub(이 저장소), **Buildspec 경로 `deploy/buildspec.yml`**,
   환경: 특권(privileged) 모드 ✔(docker build), 롤에 ECR 푸시 권한
2. CodePipeline: 소스(GitHub, dev 브랜치) → 빌드(위 프로젝트) → 배포(ECS, imagedefinitions.json)
3. dev에 머지될 때마다 자동 재배포되는지 커밋 한 번으로 확인

## 8. OAuth 콜백 갱신 (마지막)

네이버/카카오/구글 개발자 콘솔에서 콜백 URL에 ALB 주소 추가.
데모 안정성을 위해 발표 리허설 전에 실URL로 로그인 1회 검증.

## 자주 터지는 것

- **태스크 메모리 부족으로 재시작 반복** → 4GB 미만이면 KcELECTRA 로드에서 OOM
- **ALB 헬스체크 실패로 태스크 킬** → 기동(모델 다운로드+migrate)이 느리므로
  헬스체크 유예(health check grace period) 180초 이상 줄 것
- **CORS/CSRF** → 프론트·백이 같은 도메인이라 기본적으로 문제 없음.
  도메인 분리 시에만 CSRF_TRUSTED_ORIGINS 추가 필요
- **정적 파일 404** → collectstatic은 run.sh가 자동 실행 — nginx alias 경로와
  STATIC_ROOT(`staticfiles/`)가 일치하는지 확인

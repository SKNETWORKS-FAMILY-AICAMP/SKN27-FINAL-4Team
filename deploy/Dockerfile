# ── 빈틈사이 운영 이미지 (AWS ECS 배포용, 2026-07-21) ──────────────────
# 강사 견본(django_on_aws)의 nginx+gunicorn 단일 컨테이너 패턴에 프론트 빌드를 얹음.
# 빌드는 반드시 저장소 루트에서:  docker build -f deploy/Dockerfile -t binteumsai .
#
# 개발 환경은 기존 docker-compose.yml + app/Dockerfile 그대로 — 이 파일은 배포 전용.

# ── 1단계: Vue 프론트 빌드 ────────────────────────────────────────────
FROM node:20-alpine AS front
WORKDIR /fe
COPY app/frontend/package*.json ./
RUN npm ci
COPY app/frontend ./
RUN npm run build          # → /fe/dist

# ── 2단계: Django + gunicorn + nginx ─────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    nginx build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# 의존성 먼저 (레이어 캐싱) — 운영 전용으로 gunicorn·boto3 추가
COPY app/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r /tmp/requirements.txt gunicorn boto3

# 소스 — 개발 compose의 볼륨 마운트 구조(/app, /ai, /etl)를 그대로 재현
COPY app /app
COPY ai /ai
COPY etl /etl

# 프론트 빌드 산출물 + nginx 설정 + 기동 스크립트
COPY --from=front /fe/dist /srv/frontend
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/run.sh /run.sh
COPY deploy/s3_sync.py /s3_sync.py
RUN chmod +x /run.sh && rm -f /etc/nginx/sites-enabled/default

# 감정모델 산출물은 이미지에 굽지 않는다(깃이그노·488MB) — 기동 시 S3에서 동기화.
# S3_ARTIFACTS_URI 미설정이면 LLM 폴백으로 동작 (앱 설계상 안전).
ENV EMOTION_ARTIFACT_DIR=/artifacts

EXPOSE 80
CMD ["/run.sh"]

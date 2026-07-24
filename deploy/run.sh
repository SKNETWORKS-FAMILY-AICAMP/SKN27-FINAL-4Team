#!/bin/sh
# 빈틈사이 운영 기동 (강사 견본 run.sh 패턴 + 우리 스택 추가분)
set -e

# ── 감정모델 산출물 (선택) — S3_ARTIFACTS_URI 설정 시 동기화 ──
# 실패해도 죽지 않는다: 앱은 산출물 없으면 LLM 폴백으로 동작.
if [ -n "$S3_ARTIFACTS_URI" ]; then
    echo "[run] 감정모델 산출물 동기화: $S3_ARTIFACTS_URI -> ${EMOTION_ARTIFACT_DIR:-/artifacts}"
    python /s3_sync.py "$S3_ARTIFACTS_URI" "${EMOTION_ARTIFACT_DIR:-/artifacts}" \
        || echo "[run] 산출물 다운로드 실패 — LLM 폴백으로 계속"
fi

cd /app/backend
mkdir -p media staticfiles   # .dockerignore로 이미지에서 빠진 폴더 — 없으면 TTS 첫 저장 실패

python manage.py migrate --no-input
python manage.py load_tarot_data
python manage.py collectstatic --no-input

# gunicorn은 내부 8000, 외부는 nginx 80이 받아 프록시
# ★워커 1 고정 이유: 시크릿챗 대화가 프로세스 RAM 캐시에 산다 — 워커 2개면
# 턴마다 다른 프로세스로 가서 맥락 증발. 늘리려면 캐시를 Redis로 옮긴 뒤에.
gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers "${GUNICORN_WORKERS:-1}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout 180 &

nginx -g 'daemon off;'

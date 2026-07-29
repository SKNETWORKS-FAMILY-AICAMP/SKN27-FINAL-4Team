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
# 마음카드 마스터 데이터(그림체 8종·날씨/장소/행동 카탈로그 310건 등).
# 없으면 scene의 available_styles가 빈 배열이라 이미지 생성이 422로 죽는다.
# 화면은 그림체를 하드코딩해 보여주므로 UI만으로는 고장이 안 보인다 (2026-07-29 실측).
# load_tarot_data와 같이 update_or_create라 매 기동 반복 실행해도 안전하다.
python manage.py import_emotion_card_data
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

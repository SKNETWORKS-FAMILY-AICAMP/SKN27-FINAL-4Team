# 웰니스 챗봇 백엔드 (Django + LangGraph) — v6.0
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# 의존성 먼저 설치 (레이어 캐싱)
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    -r /tmp/requirements.txt

# 소스 복사 (개발 시에는 docker-compose의 ./app:/app 볼륨이 덮어씀)
COPY . /app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

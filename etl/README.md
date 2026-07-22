# etl/ — 데이터 파이프라인 및 ETL 작업 공간

크롤링, 전처리, DB 적재 스크립트와 학습 데이터셋이 위치합니다.

## 폴더 구조

| 폴더/파일 | 역할 |
|---|---|
| `data/` | AI 학습용 데이터셋 — KcELECTRA 학습 정제본, 평가셋 (AI Hub 파생물은 repo 미포함) |
| `datasets/` | MBTI 및 기타 원천 데이터셋 모음 |
| `embedding/` | 임베딩 생성 관련 스크립트 |
| `onboarding/` | 온보딩 데이터 처리 스크립트 |
| `onboarding_data/` | 온보딩 원천 데이터 |
| `scripts/` | 기타 데이터 처리 보조 스크립트 |
| `seed_postgres_static_data.py` | PostgreSQL 정적 기초 데이터 시딩 (PERSONAS, EXPRESSION_ASSETS 등) |
| `load_scales_to_postgres.py` | 심리 척도 6종 DB 적재 (PHQ-9, GAD-7, PHQ-15, RSES, UCLA-3, SPANE) |

## 실행 순서 (처음 세팅할 때)

```bash
# 1. 정적 기초 데이터 먼저
python seed_postgres_static_data.py

# 2. 척도 데이터
python load_scales_to_postgres.py
```

> 루트 `.env` 파일에 DB 접속 정보가 있어야 실행됩니다.

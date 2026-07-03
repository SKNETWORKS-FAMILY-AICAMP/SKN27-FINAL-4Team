# ETL 스크립트

DB 적재 및 초기 데이터 세팅 스크립트 모음입니다.

---

## 파일별 설명

| 파일 | 대상 DB | 내용 |
|---|---|---|
| `seed_postgres_static_data.py` | PostgreSQL | PERSONAS, EXPRESSION_ASSETS 등 정적 기초 데이터 시딩 |
| `load_scales_to_postgres.py` | PostgreSQL | 심리 척도 JSON 파일을 DB에 적재 — PHQ-9, GAD-7, PHQ-15, RSES, UCLA-3, SPANE 6종 |

---

## 실행 순서 (처음 세팅할 때)

```bash
# 1. 정적 기초 데이터 먼저
python seed_postgres_static_data.py

# 2. 척도 데이터
python load_scales_to_postgres.py
```

> 루트 `.env` 파일에 DB 접속 정보가 있어야 실행됩니다.

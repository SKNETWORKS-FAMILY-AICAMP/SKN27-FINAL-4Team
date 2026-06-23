# 데이터 수집하는 공간 (벡터db)

DB 적재 및 초기 데이터 세팅 스크립트 모음입니다.

---

## 파일별 설명

| 파일 | 대상 DB | 내용 |
|---|---|---|
| `load_ltm_sample_to_neo4j.py` | Neo4j | 장기기억(LTM) 샘플 데이터 적재 — User, LifeEvent, CognitiveThought, EmotionState, CoreBelief 노드 생성 |
| `load_scales_to_postgres.py` | PostgreSQL | 심리 척도 JSON 파일을 DB에 적재 — PHQ-9, GAD-7, PHQ-15, RSES, UCLA-3, SPANE 6종 |
| `load_tea_metadata_etl.py` | (API 수집) | 차(茶) 64종 메타데이터 수집 스크립트 — 감정별(우울/불안/분노 등) 카테고리로 분류 |
| `load_tea_to_neo4j.py` | Neo4j | `storage/마시는_차_추천_데이터셋.json`을 Neo4j에 적재 |
| `load_theories_to_vector_db.py` | PostgreSQL + Neo4j | 심리이론 마크다운 파일을 청크로 파싱 후 벡터 DB에 적재 |
| `seed_postgres_static_data.py` | PostgreSQL | PERSONAS, EXPRESSION_ASSETS 등 정적 기초 데이터 시딩 |

---

## 실행 순서 (처음 세팅할 때)

```bash
# 1. 정적 기초 데이터 먼저
python seed_postgres_static_data.py

# 2. 척도 데이터
python load_scales_to_postgres.py

# 3. 차 데이터 (Neo4j)
python load_tea_to_neo4j.py

# 4. 심리이론 (벡터 DB)
python load_theories_to_vector_db.py

# 5. LTM 샘플
python load_ltm_sample_to_neo4j.py
```

> `.env` 파일에 DB 접속 정보가 있어야 실행됩니다.

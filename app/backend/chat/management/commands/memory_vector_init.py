# -*- coding: utf-8 -*-
"""벡터 의미 검색 초기화 (2026-07-12) — 1회 실행.

사용법: python manage.py memory_vector_init

하는 일:
1. Neo4j 벡터 인덱스 생성 (Event.embedding, 768차원, cosine) — 없을 때만
2. 백필: embedding 없는 기존 Event 노드 전부에 임베딩 부착
3. 검증: 샘플 질의로 의미 검색이 실제로 도는지 확인

선행: uv pip install sentence-transformers  (최초 실행 시 모델 ~440MB 다운로드)
"""
from django.core.management.base import BaseCommand

from chat import embedder
from chat import graph_memory_v2_base as graph_memory   # v1 철거 (2026-07-21)


class Command(BaseCommand):
    help = '벡터 의미 검색 초기화 — 인덱스 생성 + 기존 기억 백필'

    def handle(self, *args, **opts):
        if not graph_memory.is_enabled():
            self.stderr.write('Neo4j 비활성 — .env NEO4J_* 확인')
            return
        if not embedder.is_available():
            self.stderr.write('임베딩 모델 로드 실패 — sentence-transformers 설치 확인:\n'
                              '  uv pip install sentence-transformers')
            return

        drv = graph_memory._get_driver()
        idx = graph_memory.VEC_INDEX
        dim = embedder.EMBED_DIM

        with drv.session() as s:
            # ① 인덱스 생성 (idempotent)
            s.run(
                f'CREATE VECTOR INDEX {idx} IF NOT EXISTS '
                'FOR (e:Event) ON (e.embedding) '
                'OPTIONS {indexConfig: {`vector.dimensions`: $dim, '
                '`vector.similarity_function`: "cosine"}}', dim=dim)
            self.stdout.write(f'① 벡터 인덱스 "{idx}" 준비 완료 (dim={dim}, cosine)')

            # ② 백필 — embedding 없는 이벤트 전부
            rows = s.run(
                'MATCH (e:Event) WHERE e.embedding IS NULL AND e.name IS NOT NULL '
                'RETURN elementId(e) AS eid, e.name AS name').data()
            self.stdout.write(f'② 백필 대상: {len(rows)}개')
            done = 0
            for r in rows:
                vec = embedder.embed(r['name'])
                if not vec:
                    continue
                s.run('MATCH (e:Event) WHERE elementId(e) = $eid SET e.embedding = $vec',
                      eid=r['eid'], vec=vec)
                done += 1
            self.stdout.write(f'   임베딩 부착: {done}/{len(rows)}')

            # ③ 검증 — 인덱스 온라인 대기 후 샘플 질의
            s.run('CALL db.awaitIndexes(60)')
            qvec = embedder.embed('저번에 당첨됐던 거 기억나?')
            hits = s.run(
                f'CALL db.index.vector.queryNodes("{idx}", 3, $vec) '
                'YIELD node, score RETURN node.name AS name, round(score, 3) AS score',
                vec=qvec).data()
            self.stdout.write('③ 샘플 질의 "저번에 당첨됐던 거 기억나?" →')
            for h in hits:
                self.stdout.write(f"   {h['score']}  {h['name']}")
            self.stdout.write('\n완료 — 이제 의미 검색이 활성화됐습니다.')

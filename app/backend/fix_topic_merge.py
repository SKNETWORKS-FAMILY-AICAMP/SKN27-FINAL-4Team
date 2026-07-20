# -*- coding: utf-8 -*-
"""Topic 어휘 분열 병합 (2026-07-20) — 동의어 노드('직장')를 정식 카테고리('일')로 흡수.
실측: 일 6 vs 직장 6으로 분열, 약속·일상 등 목록 밖 어휘 발생 → 14종 확정에 맞춰 정리.
실행: python manage.py shell -c "exec(open('fix_topic_merge.py', encoding='utf-8').read())"
팀 공유용 — 각자 로컬 그래프에도 한 번 실행 권장.
"""
from chat import graph_memory_v2_base as g
from chat.memory_config import TOPIC_CATEGORIES, TOPIC_SYNONYMS

with g._get_driver().session() as s:
    merged = 0
    for syn, canon in TOPIC_SYNONYMS.items():
        row = s.run('MATCH (t:Topic {name:$syn}) RETURN count(t) AS c', syn=syn).single()
        if not row or not row['c']:
            continue
        # ABOUT·IN_CATEGORY 간선을 정식 노드로 옮기고 동의어 노드 삭제
        s.run('MATCH (t:Topic {name:$syn}) MERGE (c:Topic {name:$canon}) '
              'WITH t, c '
              'OPTIONAL MATCH (e)-[r:ABOUT]->(t) '
              'FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | '
              '  MERGE (e)-[:ABOUT]->(c)) '
              'WITH t, c '
              'OPTIONAL MATCH (x)-[r2:IN_CATEGORY]->(t) '
              'FOREACH (_ IN CASE WHEN x IS NULL THEN [] ELSE [1] END | '
              '  MERGE (x)-[:IN_CATEGORY]->(c)) '
              'DETACH DELETE t', syn=syn, canon=canon)
        print(f'  병합: {syn} → {canon}')
        merged += 1
    print(f'완료 — {merged}건 병합')
    print('\n정리 후 Topic 목록:')
    for r in s.run('MATCH (t:Topic) OPTIONAL MATCH (e:Event)-[:ABOUT]->(t) '
                   'RETURN t.name AS n, count(e) AS c ORDER BY c DESC').data():
        mark = '★카테고리' if r['n'] in TOPIC_CATEGORIES else '잎(구체)'
        print(f"  {r['n']}: 사건 {r['c']}건 ({mark})")

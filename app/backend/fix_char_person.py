# -*- coding: utf-8 -*-
"""캐릭터 자기참조 오염 청소 (2026-07-20, 일회용) — 포리·까미·토토·여울이
Person으로 저장된 것 전부 삭제 (관계·INVOLVES 포함).
실행: python manage.py shell -c "exec(open('fix_char_person.py', encoding='utf-8').read())"
"""
from chat import graph_memory_v2_base as g

with g._get_driver().session() as s:
    n = s.run(
        "MATCH (p:Person) WHERE p.name =~ '(포리|까미|토토|여울)(야|아|님|씨)?' "
        'DETACH DELETE p RETURN count(*) AS n').single()['n']
    print(f'캐릭터 Person 노드 {n}건 삭제 (호격 변형 포함)')
    rows = s.run('MATCH (u:User)-[:RELATES_TO|HAS_EVENT]->() '
                 'MATCH (p:Person) RETURN DISTINCT p.name AS n LIMIT 20').data()
    print('남은 인물:', [r['n'] for r in rows])

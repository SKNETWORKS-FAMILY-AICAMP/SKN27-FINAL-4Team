# -*- coding: utf-8 -*-
"""V2 그래프 기반 기억 보관함 서비스.

기억은 ``User``에 연결된 사실에서 출발한다. 같은 원문 작성 시각(또는 원문을
가리키는 episode 식별자)에 생성된 Event·관계·취향과 그 연결 맥락을 하나의
단위로 묶는다. ``Episode``는 존재할 때 원문과 작성 시각을 보강할 뿐, 기억을
노출하기 위한 필수 조건이 아니다.
"""
from collections import OrderedDict

from .constants import MEMORY_ID_PREFIXES


def _decrypt_source(value):
    """Episode.text 복호화 — 그래프에 Fernet으로 저장돼 있다 (2026-07-21).

    'enc:v1:' 접두사가 없는 값(암호화 도입 이전 데이터)은 decrypt가 그대로
    돌려주므로 기존 기억도 계속 보인다. 키가 없으면 안내 문구가 나온다.
    """
    if not value:
        return ''
    from chat.crypto_fields import decrypt
    return decrypt(value)


from .introduction import (
    build_memory_introduction,
    build_memory_title,
)
from .queries import (
    DELETE_CAUSAL_LINKS_QUERY,
    DELETE_EVENT_CONTEXT_QUERY,
    DELETE_EVENT_FACTS_QUERY,
    DELETE_ORPHAN_CONTEXT_QUERY,
    DELETE_ORPHAN_EVENTS_QUERY,
    DELETE_PREFERENCE_FACTS_QUERY,
    DELETE_RELATION_FACTS_QUERY,
    DELETE_SOURCE_QUERY,
    EVENT_CONTEXT_QUERY,
    FIND_EVENT_ORIGIN_QUERY,
    FIND_MEMORY_EVENTS_QUERY,
    FIND_MEMORY_ORIGIN_QUERY,
    FIND_ORPHAN_EVENTS_QUERY,
    MEMORY_UNITS_QUERY,
    PREFERENCE_CONTEXT_QUERY,
    RELATION_CONTEXT_QUERY,
    RESTORE_EVENT_FACTS_QUERY,
)


def _clean_list(values):
    return [value for value in (values or []) if value not in (None, '')]


def _clean_maps(values, required_key):
    return [
        value for value in (values or [])
        if isinstance(value, dict) and value.get(required_key) not in (None, '')
    ]


def _clean_graph_items(values):
    return [
        value for value in (values or [])
        if isinstance(value, dict) and value.get('node_id')
    ]


def _first_value(*values):
    return next((value for value in values if value not in (None, '')), '')


def _resolve_unit_saved_at(unit):
    """가장 신뢰도 높은 그래프 메타데이터에서 기억 작성 시각을 찾는다."""
    if unit.get('saved_at'):
        return unit['saved_at'], unit.get('saved_at_source') or 'fact'

    source_created_at = (
        unit.get('graph', {}).get('source', {}).get('properties', {})
        .get('created_at')
    )
    if source_created_at:
        return source_created_at, 'episode'

    for event in unit.get('events', []):
        event_graph = event.get('graph', {})
        value = _first_value(
            event.get('created_at'),
            event_graph.get('node', {}).get('properties', {}).get('created_at'),
            event_graph.get('has_event', {}).get('properties', {}).get('created_at'),
            event_graph.get('has_event', {}).get('properties', {}).get('valid_from'),
            event_graph.get('records', {}).get('properties', {}).get('created_at'),
        )
        if value:
            return value, 'event'

    for category in ('relations', 'preferences'):
        for fact in unit.get(category, []):
            edge_properties = fact.get('graph', {}).get('edge', {}).get('properties', {})
            value = _first_value(
                fact.get('valid_from'),
                edge_properties.get('created_at'),
                edge_properties.get('valid_from'),
            )
            if value:
                return value, 'fact'

    return '', 'unknown'


def _normalise_event(record):
    dates = _clean_maps(record.get('dates'), 'date')
    if record.get('occurs_start') and not any(
            item.get('date') == record['occurs_start'] for item in dates):
        dates.insert(0, {
            'date': record['occurs_start'],
            'role': 'start' if record.get('occurs_end') else 'on',
        })
    if record.get('occurs_end') and not any(
            item.get('date') == record['occurs_end'] for item in dates):
        dates.append({'date': record['occurs_end'], 'role': 'end'})

    return {
        'id': record.get('event_id'),
        'key': record.get('event_key'),
        'name': record.get('event_name'),
        'cause': record.get('cause_text'),
        'salience': record.get('salience'),
        'created_at': record.get('event_created_at'),
        'recall_count': record.get('recall_count'),
        'suppressed': record.get('suppressed'),
        'occurs_start': record.get('occurs_start'),
        'occurs_end': record.get('occurs_end'),
        'dates': dates,
        'places': _clean_list(record.get('places')),
        'topics': _clean_list(record.get('topics')),
        'people': _clean_maps(record.get('people'), 'name'),
        'causes': _clean_maps(record.get('causes'), 'name'),
        'graph': {
            'node': {
                'id': record.get('event_node_id'),
                'labels': ['Event'],
                'properties': record.get('event_properties') or {},
            },
            'has_event': {
                'id': record.get('has_event_edge_id'),
                'type': 'HAS_EVENT',
                'properties': record.get('has_event_properties') or {},
            },
            'records': {
                'id': record.get('records_edge_id'),
                'type': 'RECORDS' if record.get('records_edge_id') else None,
                'properties': record.get('records_properties') or {},
            },
            'dates': _clean_graph_items(record.get('date_graph')),
            'places': _clean_graph_items(record.get('place_graph')),
            'topics': _clean_graph_items(record.get('topic_graph')),
            'people': _clean_graph_items(record.get('person_graph')),
            'causes': _clean_graph_items(record.get('cause_graph')),
        },
    }


def _consolidate_graph(unit):
    """중첩된 조회 결과를 소비하기 쉬운 nodes/edges 그래프로도 제공한다."""
    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    def add_node(node):
        node_id = (node or {}).get('id')
        if not node_id or node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        nodes.append({
            'id': node_id,
            'labels': (node or {}).get('labels') or [],
            'properties': (node or {}).get('properties') or {},
        })

    def add_edge(edge, from_id, to_id, *, edge_id_key='id',
                 edge_type_key='type', properties_key='properties'):
        edge = edge or {}
        edge_id = edge.get(edge_id_key)
        edge_type = edge.get(edge_type_key)
        if not edge_id or not edge_type or edge_id in seen_edges:
            return
        seen_edges.add(edge_id)
        edges.append({
            'id': edge_id,
            'type': edge_type,
            'from': from_id,
            'to': to_id,
            'properties': edge.get(properties_key) or {},
        })

    root = unit['graph']['user']
    source = unit['graph']['source']
    add_node(root)
    add_node(source)

    for event in unit['events']:
        event_graph = event['graph']
        event_node = event_graph['node']
        add_node(event_node)
        add_edge(event_graph['has_event'], root.get('id'), event_node.get('id'))
        add_edge(event_graph['records'], source.get('id'), event_node.get('id'))

        for category in ('dates', 'places', 'topics', 'causes'):
            for item in event_graph[category]:
                context_node = {
                    'id': item.get('node_id'),
                    'labels': item.get('labels') or [],
                    'properties': item.get('node') or {},
                }
                add_node(context_node)
                add_edge(
                    item,
                    event_node.get('id'),
                    context_node.get('id'),
                    edge_id_key='edge_id',
                    edge_type_key='edge_type',
                    properties_key='edge',
                )

        for item in event_graph['people']:
            person_node = {
                'id': item.get('node_id'),
                'labels': item.get('labels') or [],
                'properties': item.get('node') or {},
            }
            add_node(person_node)
            add_edge(
                item,
                event_node.get('id'),
                person_node.get('id'),
                edge_id_key='edge_id',
                edge_type_key='edge_type',
                properties_key='edge',
            )
            add_edge(
                item,
                root.get('id'),
                person_node.get('id'),
                edge_id_key='user_edge_id',
                edge_type_key='user_edge_type',
                properties_key='user_edge',
            )

    for relation in unit['relations']:
        relation_graph = relation['graph']
        add_node(relation_graph['node'])
        add_edge(
            relation_graph['edge'],
            root.get('id'),
            relation_graph['node'].get('id'),
        )

    for preference in unit['preferences']:
        preference_graph = preference['graph']
        add_node(preference_graph['node'])
        add_edge(
            preference_graph['edge'],
            root.get('id'),
            preference_graph['node'].get('id'),
        )

    unit['graph']['nodes'] = nodes
    unit['graph']['edges'] = edges


def serialise_units(memory_records, event_records, relation_records, preference_records):
    units = OrderedDict()
    for record in memory_records:
        memory_id = record.get('memory_id')
        if not memory_id:
            continue
        units[memory_id] = {
            'memory_id': memory_id,
            'saved_at': record.get('saved_at') or '',
            'saved_at_source': (
                'episode' if record.get('saved_at') and record.get('has_source')
                else 'fact' if record.get('saved_at')
                else 'unknown'
            ),
            #  Episode.text는 Fernet으로 암호화돼 저장된다(graph_memory_v2_base:_store).
            #  접두사 'enc:v1:'가 없는 기존 데이터는 decrypt가 그대로 통과시킨다 → 무중단.
            'source_text': _decrypt_source(record.get('source_text')),
            'has_source': bool(record.get('has_source')),
            'graph': {
                'user': {
                    'id': record.get('user_node_id'),
                    'labels': ['User'],
                    'properties': record.get('user_properties') or {},
                },
                'source': {
                    'id': record.get('source_node_id'),
                    'labels': ['Episode'] if record.get('has_source') else [],
                    'properties': record.get('source_properties') or {},
                },
            },
            'events': [],
            'relations': [],
            'preferences': [],
        }

    for record in event_records:
        unit = units.get(record.get('memory_id'))
        if unit is not None and record.get('event_name'):
            unit['events'].append(_normalise_event(record))

    for record in relation_records:
        unit = units.get(record.get('memory_id'))
        if unit is not None and record.get('name'):
            unit['relations'].append({
                'name': record.get('name'),
                'relation': record.get('relation'),
                'valid_from': record.get('valid_from'),
                'valid_to': record.get('valid_to'),
                'end_reason': record.get('end_reason'),
                'graph': {
                    'node': {
                        'id': record.get('person_node_id'),
                        'labels': record.get('person_labels') or ['Person'],
                        'properties': record.get('person_properties') or {},
                    },
                    'edge': {
                        'id': record.get('relation_edge_id'),
                        'type': record.get('relation_edge_type') or 'RELATES_TO',
                        'properties': record.get('relation_properties') or {},
                    },
                },
            })

    for record in preference_records:
        unit = units.get(record.get('memory_id'))
        if unit is not None and record.get('topic'):
            unit['preferences'].append({
                'topic': record.get('topic'),
                'polarity': record.get('polarity'),
                'valid_from': record.get('valid_from'),
                'valid_to': record.get('valid_to'),
                'end_reason': record.get('end_reason'),
                'graph': {
                    'node': {
                        'id': record.get('topic_node_id'),
                        'labels': record.get('topic_labels') or ['Topic'],
                        'properties': record.get('topic_properties') or {},
                    },
                    'edge': {
                        'id': record.get('preference_edge_id'),
                        'type': record.get('preference_edge_type') or 'PREFERS',
                        'properties': record.get('preference_properties') or {},
                    },
                },
            })

    memories = []
    for unit in units.values():
        _consolidate_graph(unit)
        unit['saved_at'], unit['saved_at_source'] = _resolve_unit_saved_at(unit)
        unit['has_created_at'] = bool(unit['saved_at'])
        unit['introduction'] = build_memory_introduction(unit)
        people = {}
        event_names = []
        dates = []
        relation_names = []

        for event in unit['events']:
            if event.get('name'):
                event_names.append(event['name'])
            if event.get('occurs_start'):
                dates.append(event['occurs_start'])
            for person in event['people']:
                people[person['name']] = person
        for relation in unit['relations']:
            people.setdefault(relation['name'], {
                'name': relation['name'],
                'relation': relation.get('relation'),
            })
            if relation.get('relation'):
                relation_names.append(relation['relation'])

        memories.append({
            'id': f"memory:{unit['memory_id']}",
            'title': build_memory_title(unit),
            'content': unit['introduction']['text'],
            'saved_at': unit['saved_at'],
            'created_at': unit['saved_at'],
            'has_created_at': unit['has_created_at'],
            'created_at_source': unit['saved_at_source'],
            'type': 'memory',
            'raw_date': dates[0] if dates else '',
            'raw_people': list(people.values()),
            'raw_relation': ', '.join(dict.fromkeys(relation_names)),
            'raw_events': event_names,
            'context': unit,
        })
    memories.sort(
        key=lambda memory: (
            bool(memory['created_at']),
            str(memory['created_at']),
        ),
        reverse=True,
    )
    return memories


def load_memory_units(session, uid):
    memory_records = session.run(MEMORY_UNITS_QUERY, uid=uid).data()
    memory_ids = [
        record.get('memory_id') for record in memory_records
        if record.get('memory_id')
    ]
    if not memory_ids:
        return []

    event_records = session.run(
        EVENT_CONTEXT_QUERY, uid=uid, memory_ids=memory_ids).data()
    relation_records = session.run(
        RELATION_CONTEXT_QUERY, uid=uid, memory_ids=memory_ids).data()
    preference_records = session.run(
        PREFERENCE_CONTEXT_QUERY, uid=uid, memory_ids=memory_ids).data()
    return serialise_units(
        memory_records, event_records, relation_records, preference_records)


def find_memory_origin(tx, uid, memory_id):
    kind, separator, value = memory_id.partition(':')
    if not separator:
        kind, value = 'memory', memory_id

    if kind in MEMORY_ID_PREFIXES:
        row = tx.run(
            FIND_MEMORY_ORIGIN_QUERY,
            uid=uid, origin=value,
        ).single()
    elif kind == 'event':
        row = tx.run(
            FIND_EVENT_ORIGIN_QUERY,
            uid=uid, key=value,
        ).single()
    else:
        return None
    if not row:
        return None
    return {
        'memory_id': row.get('memory_id'),
        'has_source': bool(row.get('has_source')),
    }


def delete_memory_unit(tx, uid, memory_id):
    origin = find_memory_origin(tx, uid, memory_id)
    if not origin or not origin.get('memory_id'):
        return None
    origin_id = origin['memory_id']

    event_rows = tx.run(
        FIND_MEMORY_EVENTS_QUERY,
        uid=uid, origin=origin_id,
    ).data()
    event_ids = [row.get('id') for row in event_rows if row.get('id')]
    event_keys = [row.get('key') for row in event_rows if row.get('key')]

    # User에 직접 연결된 사실은 같은 원문 식별자/작성 시각에 속한 것만 지운다.
    tx.run(
        DELETE_EVENT_FACTS_QUERY,
        uid=uid, origin=origin_id,
    )
    tx.run(
        DELETE_RELATION_FACTS_QUERY,
        uid=uid, origin=origin_id,
    )
    tx.run(
        DELETE_PREFERENCE_FACTS_QUERY,
        uid=uid, origin=origin_id,
    )

    # Event 주변 맥락도 원문 식별자나 같은 작성 시각으로 연결된 관계만 정리한다.
    tx.run(
        DELETE_EVENT_CONTEXT_QUERY,
        uid=uid, origin=origin_id,
    )

    # BECAUSE_OF에는 원문 속성이 없으므로 같은 기억 단위 안의 Event끼리 연결된
    # 인과관계만 제거한다.
    tx.run(
        DELETE_CAUSAL_LINKS_QUERY,
        uid=uid, event_ids=event_ids, event_keys=event_keys,
    )

    if origin['has_source']:
        tx.run(
            DELETE_SOURCE_QUERY,
            uid=uid, origin=origin_id,
        )

    # 최초 원문이 삭제됐더라도 같은 Event를 기록한 다음 원문이 남아 있으면
    # User 루트를 유지해 후속 기억이 목록에서 사라지지 않게 한다.
    tx.run(
        RESTORE_EVENT_FACTS_QUERY,
        uid=uid,
        event_ids=event_ids,
        event_keys=event_keys,
    )

    # 다른 원문이나 User 사실에서 더 이상 참조하지 않는 Event만 제거한다.
    orphan_event_rows = tx.run(
        FIND_ORPHAN_EVENTS_QUERY,
        uid=uid, event_ids=event_ids, event_keys=event_keys,
    ).data()
    orphan_event_ids = [
        row.get('id') for row in orphan_event_rows if row.get('id')
    ]
    orphan_event_keys = [
        row.get('key') for row in orphan_event_rows if row.get('key')
    ]
    tx.run(
        DELETE_ORPHAN_EVENTS_QUERY,
        uid=uid,
        event_ids=orphan_event_ids,
        event_keys=orphan_event_keys,
    )
    deleted_event_count = len(orphan_event_rows)

    # Episode 관계와 고아 Event를 제거한 뒤, 다른 기억에서 공유하지 않는 맥락
    # 노드만 삭제한다. User 및 아직 연결된 공유 노드는 건드리지 않는다.
    tx.run(DELETE_ORPHAN_CONTEXT_QUERY)

    return {
        'memory_id': origin_id,
        'had_source': origin['has_source'],
        'event_count': len(event_rows),
        'deleted_event_count': deleted_event_count,
        'event_keys': event_keys,
    }

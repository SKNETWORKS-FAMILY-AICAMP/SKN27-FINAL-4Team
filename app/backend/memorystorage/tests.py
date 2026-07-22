from unittest import mock

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from memorystorage import views


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return self._rows

    def single(self):
        return self._rows[0] if self._rows else None


class _ReadSession:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def run(self, query, **params):
        self.calls.append((query, params))
        return _Result(next(self.results))


class _WriteTx:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if 'source.id IS NOT NULL AS has_source' in query:
            return _Result([{
                'memory_id': 'ep_test',
                'has_source': True,
            }])
        if 'RETURN DISTINCT event.id AS id' in query:
            return _Result([
                {'id': 'ev_1', 'key': '제주여행'},
                {'id': 'ev_2', 'key': '여행준비'},
            ])
        if 'RETURN DISTINCT e.id AS id' in query:
            return _Result([
                {'id': 'ev_1', 'key': '제주여행'},
                {'id': 'ev_2', 'key': '여행준비'},
            ])
        return _Result([])


class _WriteSession:
    def __init__(self, tx):
        self.tx = tx

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_write(self, callback):
        return callback(self.tx)


class _Driver:
    def __init__(self, session):
        self._session = session

    def session(self):
        return self._session


class MemoryUnitSerialisationTests(SimpleTestCase):
    def test_groups_connected_v2_context_by_memory_origin(self):
        memories = views._serialise_units(
            [{
                'memory_id': 'ep_1',
                'saved_at': '2026-07-20T10:00:00',
                'source_text': '준호와 제주 여행을 가기로 했어.',
                'has_source': True,
                'user_node_id': '4:user:7',
                'user_properties': {'uid': 7},
                'source_node_id': '4:episode:1',
                'source_properties': {
                    'id': 'ep_1',
                    'uid': 7,
                    'text': '준호와 제주 여행을 가기로 했어.',
                    'created_at': '2026-07-20T10:00:00',
                },
            }],
            [{
                'memory_id': 'ep_1',
                'event_id': 'ev_1',
                'event_key': '제주여행',
                'event_name': '제주 여행',
                'cause_text': None,
                'top_emotion': '기쁨',
                'salience': 1.0,
                'event_created_at': '2026-07-20T10:00:00',
                'recall_count': 2,
                'suppressed': None,
                'occurs_start': '2026-07-21',
                'occurs_end': None,
                'event_node_id': '4:event:1',
                'event_properties': {
                    'id': 'ev_1',
                    'uid': 7,
                    'key': '제주여행',
                    'name': '제주 여행',
                    'recall_count': 2,
                    'embedding': [0.1, 0.2],
                },
                'has_event_edge_id': '5:has-event:1',
                'has_event_properties': {
                    'valid_from': '2026-07-20T10:00:00',
                    'valid_to': None,
                    'created_at': '2026-07-20T10:00:00',
                    'episode': 'ep_1',
                },
                'records_edge_id': '5:records:1',
                'records_properties': {},
                'dates': [{'date': '2026-07-21', 'role': 'on'}],
                'places': ['제주'],
                'topics': ['여행'],
                'people': [{'name': '준호', 'relation': '친구'}],
                'emotions': [{'type': '기쁨', 'score': 0.9}],
                'causes': [],
                'date_graph': [{
                    'node_id': '4:date:1',
                    'labels': ['Date'],
                    'node': {'date': '2026-07-21'},
                    'edge_id': '5:on:1',
                    'edge_type': 'ON',
                    'edge': {
                        'role': 'on',
                        'episode': 'ep_1',
                        'created_at': '2026-07-20T10:00:00',
                    },
                }],
                'place_graph': [],
                'topic_graph': [],
                'person_graph': [],
                'emotion_graph': [],
                'cause_graph': [],
            }],
            [{
                'memory_id': 'ep_1',
                'name': '준호',
                'relation': '친구',
                'valid_from': '2026-07-20T10:00:00',
                'valid_to': None,
                'end_reason': None,
                'person_node_id': '4:person:1',
                'person_properties': {
                    'uid': 7,
                    'key': '준호',
                    'name': '준호',
                },
                'relation_edge_id': '5:relates-to:1',
                'relation_properties': {
                    'relation': '친구',
                    'episode': 'ep_1',
                },
            }],
            [{
                'memory_id': 'ep_1',
                'topic': '여행',
                'polarity': '호',
                'valid_from': '2026-07-20T10:00:00',
                'valid_to': None,
                'end_reason': None,
                'topic_node_id': '4:topic:1',
                'topic_properties': {'name': '여행'},
                'preference_edge_id': '5:prefers:1',
                'preference_properties': {
                    'polarity': '호',
                    'episode': 'ep_1',
                },
            }],
        )

        self.assertEqual(len(memories), 1)
        memory = memories[0]
        self.assertEqual(memory['id'], 'memory:ep_1')
        self.assertEqual(memory['type'], 'memory')
        self.assertEqual(memory['saved_at'], '2026-07-20T10:00:00')
        self.assertEqual(memory['raw_events'], ['제주 여행'])
        self.assertEqual(memory['raw_people'][0]['name'], '준호')
        self.assertNotIn('raw_emotions', memory)
        self.assertIn(
            '2026년 7월 21일에 친구 준호와 제주에서 ‘제주 여행’을 '
            '함께하기로 했던 기억이에요.',
            memory['content'],
        )
        self.assertIn(
            '이 계획은 여행과 관련되어 있었어요.',
            memory['content'],
        )
        self.assertNotIn('emotions', memory['context']['events'][0])
        self.assertNotIn('준호는 친구로 기억하고 있어요.', memory['content'])
        self.assertIn('평소 여행을 좋아하는 취향도 함께 기억하고 있어요.', memory['content'])
        self.assertNotIn('당시에는', memory['content'])
        self.assertNotIn('\n\n원문\n', memory['content'])
        self.assertEqual(
            memory['context']['introduction']['text'], memory['content'])
        self.assertEqual(
            memory['context']['introduction']['original_text'],
            '준호와 제주 여행을 가기로 했어.',
        )
        graph = memory['context']['graph']
        self.assertEqual(graph['user']['properties']['uid'], 7)
        self.assertEqual(graph['source']['properties']['id'], 'ep_1')
        event_graph = memory['context']['events'][0]['graph']
        self.assertEqual(
            event_graph['node']['properties']['embedding'], [0.1, 0.2])
        self.assertEqual(
            event_graph['has_event']['properties']['episode'], 'ep_1')
        self.assertEqual(event_graph['records']['type'], 'RECORDS')
        self.assertEqual(
            event_graph['dates'][0]['edge']['created_at'],
            '2026-07-20T10:00:00',
        )
        relation_graph = memory['context']['relations'][0]['graph']
        self.assertEqual(
            relation_graph['edge']['properties']['relation'], '친구')
        preference_graph = memory['context']['preferences'][0]['graph']
        self.assertEqual(
            preference_graph['edge']['properties']['polarity'], '호')
        self.assertEqual(
            {node['labels'][0] for node in graph['nodes']},
            {'User', 'Episode', 'Event', 'Date', 'Person', 'Topic'},
        )
        self.assertEqual(
            {edge['type'] for edge in graph['edges']},
            {'RECORDS', 'HAS_EVENT', 'ON', 'RELATES_TO', 'PREFERS'},
        )
        has_event = next(
            edge for edge in graph['edges'] if edge['type'] == 'HAS_EVENT')
        self.assertEqual(has_event['from'], '4:user:7')
        self.assertEqual(has_event['to'], '4:event:1')

    def test_recovers_missing_saved_at_from_event_metadata(self):
        created_at = '2026-07-21T11:35:57'
        memories = views._serialise_units(
            [{
                'memory_id': 'legacy-event',
                'saved_at': '',
                'source_text': '',
                'has_source': False,
            }],
            [{
                'memory_id': 'legacy-event',
                'event_id': 'ev_legacy',
                'event_name': '프로젝트 상담',
                'event_created_at': created_at,
                'dates': [],
                'places': [],
                'topics': [],
                'people': [],
                'emotions': [],
                'causes': [],
            }],
            [],
            [],
        )

        self.assertEqual(memories[0]['created_at'], created_at)
        self.assertTrue(memories[0]['has_created_at'])
        self.assertEqual(memories[0]['created_at_source'], 'event')
        self.assertEqual(memories[0]['context']['saved_at'], created_at)


class StructuredIntroductionTests(SimpleTestCase):
    def test_cause_phrase_keeps_existing_korean_connector(self):
        self.assertEqual(
            views._cause_lead({'cause': '연속 야근 때문에'}),
            '연속 야근 때문에 ',
        )

    def test_connects_multiple_events_with_shared_timeline(self):
        introduction = views._memory_introduction({
            'source_text': '',
            'events': [
                {
                    'name': '회사 발표',
                    'occurs_start': '2026-07-21',
                    'occurs_end': None,
                    'dates': [],
                    'places': ['회사'],
                    'topics': ['업무'],
                    'people': [{'name': '박준호', 'relation': '팀장'}],
                    'causes': [],
                    'cause': None,
                    'graph': {'has_event': {'properties': {}}},
                },
                {
                    'name': '지갑 분실',
                    'occurs_start': '2026-07-21',
                    'occurs_end': None,
                    'dates': [],
                    'places': ['퇴근길'],
                    'topics': ['일상'],
                    'people': [],
                    'causes': [],
                    'cause': None,
                    'graph': {'has_event': {'properties': {}}},
                },
            ],
            'relations': [],
            'preferences': [],
        })

        self.assertIn(
            '2026년 7월 21일에 팀장 박준호와 회사에서 ‘회사 발표’를 '
            '함께하기로 했던 기억이에요. 이 계획은 업무와 관련되어 있었어요. '
            '같은 날, 퇴근길에서 있었던 ‘지갑 분실’에 대한 기억이에요.',
            introduction['text'],
        )
        self.assertNotIn(
            '업무와 관련되어 있었어요. 2026년',
            introduction['text'],
        )

    def test_uses_connected_context_without_repetitive_sentences(self):
        source = (
            '연속 야근 때문에 지쳐서 2026년 8월 3일부터 8월 5일까지 '
            '대학 동기이자 절친인 민지와 제주 애월로 휴가를 가기로 했어.'
        )
        introduction = views._memory_introduction({
            'source_text': source,
            'events': [
                {
                    'name': '연속 야근',
                    'occurs_start': None,
                    'occurs_end': None,
                    'dates': [],
                    'places': [],
                    'topics': ['건강'],
                    'people': [],
                    'top_emotion': 'sadness',
                    'emotions': [
                        {'type': 'sadness', 'score': 0.76},
                        {'type': 'normal', 'score': 0.08},
                    ],
                    'causes': [],
                    'cause': None,
                    'graph': {'has_event': {'properties': {}}},
                },
                {
                    'name': '제주 애월 휴가',
                    'occurs_start': '2026-08-03',
                    'occurs_end': '2026-08-05',
                    'dates': [],
                    'places': ['제주 애월'],
                    'topics': ['취미'],
                    'people': [{'name': '민지', 'relation': '친구'}],
                    'top_emotion': 'flutter',
                    'emotions': [
                        {'type': 'flutter', 'score': 0.55},
                        {'type': 'worry', 'score': 0.35},
                        {'type': 'normal', 'score': 0.1},
                    ],
                    'causes': [{'name': '연속 야근'}],
                    'cause': '연속 야근 때문에 지쳐서',
                    'graph': {'has_event': {'properties': {}}},
                },
            ],
            'relations': [{
                'name': '민지',
                'relation': '친구',
                'valid_to': None,
            }],
            'preferences': [
                {'topic': '조용한 바다 산책', 'polarity': '호'},
                {'topic': '재즈 음악', 'polarity': '호'},
                {'topic': '붐비는 관광지', 'polarity': '오'},
            ],
        })

        text = introduction['text']
        self.assertTrue(
            text.startswith(
                '연속 야근 때문에 지쳐서, 2026년 8월 3일부터 '
                '2026년 8월 5일까지 친구 민지와 제주 애월에서 '
                '‘제주 애월 휴가’를 함께하기로 했던 기억이에요.'
            )
        )
        self.assertIn('이 계획은 취미와 관련되어 있었어요.', text)
        self.assertNotIn('감정', text)
        self.assertNotIn('설렘', text)
        self.assertNotIn('걱정', text)
        self.assertNotIn('‘연속 야근’에 대해 이야기했던 기억이에요.', text)
        self.assertNotIn('민지는 친구로 기억하고 있어요.', text)
        self.assertIn(
            '평소 조용한 바다 산책과 재즈 음악을 좋아하고, '
            '붐비는 관광지는 선호하지 않는 취향도 함께 기억하고 있어요.',
            text,
        )
        self.assertNotIn('\n\n원문\n', text)
        self.assertEqual(introduction['original_text'], source)
        self.assertNotIn('\n', introduction['narrative_text'])
        self.assertEqual(len(introduction['events']), 2)

    def test_handles_relation_preference_and_empty_shapes(self):
        relation_only = views._memory_introduction({
            'source_text': '',
            'events': [],
            'relations': [{
                'name': '민수',
                'relation': '직장 동료',
                'valid_to': None,
            }],
            'preferences': [],
        })
        self.assertEqual(
            relation_only['text'], '민수는 직장 동료로 기억하고 있어요.')

        preference_only = views._memory_introduction({
            'source_text': '',
            'events': [],
            'relations': [],
            'preferences': [{
                'topic': '게임',
                'polarity': '호',
                'valid_to': '2026-07-01',
            }],
        })
        self.assertEqual(
            preference_only['text'],
            '과거의 취향이었던 게임은 지금은 종료된 기록이에요.',
        )

        empty = views._memory_introduction({
            'source_text': '',
            'events': [],
            'relations': [],
            'preferences': [],
        })
        self.assertEqual(empty['text'], '대화에서 저장된 기억이에요.')

        source_only = views._memory_introduction({
            'source_text': '요즘 새로운 취미를 찾고 있어.',
            'events': [],
            'relations': [],
            'preferences': [],
        })
        self.assertEqual(
            source_only['text'],
            '대화에서 남긴 내용을 기억하고 있어요.',
        )
        self.assertEqual(
            source_only['original_text'],
            '요즘 새로운 취미를 찾고 있어.',
        )

    def test_keeps_original_below_sparse_event_story(self):
        introduction = views._memory_introduction({
            'source_text': '연속 야근',
            'events': [{
                'name': '연속 야근',
                'occurs_start': None,
                'occurs_end': None,
                'dates': [],
                'places': [],
                'topics': [],
                'people': [],
                'top_emotion': None,
                'emotions': [],
                'causes': [],
                'cause': None,
                'graph': {'has_event': {'properties': {}}},
            }],
            'relations': [],
            'preferences': [],
        })
        self.assertEqual(
            introduction['text'],
            '‘연속 야근’에 대해 이야기했던 기억이에요.',
        )
        self.assertEqual(introduction['original_text'], '연속 야근')


class MemoryVaultApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = mock.Mock(id=7, is_authenticated=True)

    def test_list_reports_driver_unavailable_instead_of_empty_vault(self):
        request = self.factory.get('/api/mymemory/memories/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(views, 'get_memory_driver', return_value=None):
            response = views.memory_vault_list(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['memories'], [])
        self.assertIn('detail', response.data)

    def test_list_uses_user_linked_source_as_memory_unit(self):
        session = _ReadSession([
            [{
                'memory_id': 'ep_1',
                'saved_at': '2026-07-20T10:00:00',
                'source_text': '제주 여행을 가기로 했어.',
                'has_source': True,
            }],
            [{
                'memory_id': 'ep_1',
                'event_id': 'ev_1',
                'event_key': '제주여행',
                'event_name': '제주 여행',
                'cause_text': None,
                'top_emotion': None,
                'salience': 1.0,
                'occurs_start': None,
                'occurs_end': None,
                'dates': [],
                'places': ['제주'],
                'topics': ['여행'],
                'people': [],
                'emotions': [],
                'causes': [],
            }],
            [],
            [],
        ])
        request = self.factory.get('/api/mymemory/memories/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(
                views, 'get_memory_driver',
                return_value=_Driver(session)):
            response = views.memory_vault_list(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['memories'][0]['id'], 'memory:ep_1')
        self.assertEqual(len(session.calls), 4)
        self.assertIn('user:User', session.calls[0][0])
        self.assertIn('source:Episode', session.calls[0][0])
        self.assertNotIn('EVOKED', session.calls[1][0])
        self.assertIn('properties(event)', session.calls[1][0])
        self.assertIn('properties(has_event)', session.calls[1][0])
        self.assertIn('properties(records)', session.calls[1][0])
        self.assertIn('properties(on_rel)', session.calls[1][0])
        self.assertIn('properties(at_rel)', session.calls[1][0])
        self.assertIn('properties(about_rel)', session.calls[1][0])
        self.assertIn('properties(involves_rel)', session.calls[1][0])
        self.assertNotIn('properties(evoked)', session.calls[1][0])
        self.assertIn('properties(cause_rel)', session.calls[1][0])
        self.assertIn('RELATES_TO', session.calls[2][0])
        self.assertIn('properties(rel)', session.calls[2][0])
        self.assertIn('PREFERS', session.calls[3][0])
        self.assertIn('properties(pref)', session.calls[3][0])

    def test_list_keeps_user_memory_when_episode_is_missing(self):
        authored_at = '2026-07-20T10:00:00'
        session = _ReadSession([
            [{
                'memory_id': authored_at,
                'saved_at': authored_at,
                'source_text': '',
                'has_source': False,
            }],
            [{
                'memory_id': authored_at,
                'event_id': 'ev_1',
                'event_key': '제주여행',
                'event_name': '제주 여행',
                'cause_text': None,
                'top_emotion': '기쁨',
                'salience': 1.0,
                'occurs_start': '2026-07-21',
                'occurs_end': None,
                'dates': [{'date': '2026-07-21', 'role': 'on'}],
                'places': ['제주'],
                'topics': ['여행'],
                'people': [],
                'emotions': [{'type': '기쁨', 'score': 0.9}],
                'causes': [],
            }],
            [{
                'memory_id': authored_at,
                'name': '준호',
                'relation': '친구',
                'valid_from': authored_at,
                'valid_to': None,
                'end_reason': None,
            }],
            [],
        ])
        request = self.factory.get('/api/mymemory/memories/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(
                views, 'get_memory_driver',
                return_value=_Driver(session)):
            response = views.memory_vault_list(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['memories'][0]['id'],
            f'memory:{authored_at}',
        )
        self.assertEqual(
            response.data['memories'][0]['context']['source_text'], '')
        self.assertEqual(
            response.data['memories'][0]['raw_events'], ['제주 여행'])
        self.assertEqual(
            response.data['memories'][0]['raw_people'][0]['name'], '준호')
        statements = '\n'.join(query for query, _ in session.calls)
        self.assertNotIn('MERGE (episode', statements)
        self.assertNotIn('SET fact.episode', statements)
        self.assertIn('fact.created_at', statements)

    def test_list_includes_relation_and_preference_nodes(self):
        session = _ReadSession([
            [
                {
                    'memory_id': 'relates_1',
                    'saved_at': '',
                    'source_text': '',
                    'has_source': False,
                    'user_node_id': '4:user:7',
                    'user_properties': {'uid': 7},
                },
                {
                    'memory_id': 'preference_legacy_2',
                    'saved_at': '',
                    'source_text': '',
                    'has_source': False,
                    'user_node_id': '4:user:7',
                    'user_properties': {'uid': 7},
                },
            ],
            [],
            [{
                'memory_id': 'relates_1',
                'name': '민수',
                'relation': '직장 동료',
                'valid_from': None,
                'valid_to': None,
                'end_reason': None,
                'person_node_id': '4:person:1',
                'person_labels': ['Person'],
                'person_properties': {
                    'uid': 7,
                    'key': '민수',
                    'name': '민수',
                    'relation': '직장 동료',
                },
                'relation_edge_id': '5:relates:1',
                'relation_edge_type': 'RELATES_TO',
                'relation_properties': {},
            }],
            [{
                'memory_id': 'preference_legacy_2',
                'topic': '조용한 음악',
                'polarity': '호',
                'valid_from': None,
                'valid_to': None,
                'end_reason': None,
                'topic_node_id': '4:preference:1',
                'topic_labels': ['Preference'],
                'topic_properties': {
                    'uid': 7,
                    'key': '조용한음악',
                    'name': '조용한 음악',
                },
                'preference_edge_id': '5:prefers:1',
                'preference_edge_type': 'PREFERS',
                'preference_properties': {},
            }],
        ])
        request = self.factory.get('/api/mymemory/memories/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(
                views, 'get_memory_driver',
                return_value=_Driver(session)):
            response = views.memory_vault_list(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['memories']), 2)
        self.assertEqual(
            response.data['memories'][0]['title'], '민수와의 관계')
        self.assertEqual(
            response.data['memories'][1]['title'], '조용한 음악 취향')
        relation_graph = response.data['memories'][0]['context']['graph']
        preference_graph = response.data['memories'][1]['context']['graph']
        self.assertIn(
            'RELATES_TO', {edge['type'] for edge in relation_graph['edges']})
        self.assertIn(
            'PREFERS', {edge['type'] for edge in preference_graph['edges']})
        statements = '\n'.join(query for query, _ in session.calls)
        self.assertIn("type(fact) = 'RELATES_TO'", statements)
        self.assertIn('preference:Preference', statements)

    def test_delete_removes_memory_owned_graph_and_orphan_context(self):
        tx = _WriteTx()
        request = self.factory.delete('/api/mymemory/memories/memory:ep_test/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(
                views, 'get_memory_driver',
                return_value=_Driver(_WriteSession(tx))):
            response = views.memory_vault_delete(request, 'memory:ep_test')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['deleted']['memory_id'], 'ep_test')
        self.assertTrue(response.data['deleted']['had_source'])
        self.assertEqual(response.data['deleted']['event_count'], 2)
        self.assertEqual(response.data['deleted']['deleted_event_count'], 2)
        statements = '\n'.join(query for query, _ in tx.calls)
        self.assertIn('fact:HAS_EVENT', statements)
        self.assertIn("type(fact) = 'RELATES_TO'", statements)
        self.assertIn('fact:PREFERS', statements)
        self.assertIn(
            "type(fact) IN ['ON', 'AT', 'ABOUT', 'INVOLVES', 'EVOKED']",
            statements,
        )
        self.assertIn('r:BECAUSE_OF', statements)
        self.assertIn('DETACH DELETE source', statements)
        self.assertIn(
            'NOT EXISTS { MATCH (:Episode {uid:$uid})-[:RECORDS]->(e) }',
            statements,
        )
        self.assertIn(
            'NOT EXISTS { MATCH (:User {uid:$uid})-[:HAS_EVENT]->(e) }',
            statements,
        )
        self.assertIn('DETACH DELETE e', statements)
        self.assertIn(
            'n:Person OR n:Date OR n:Place OR n:Topic OR n:Preference',
            statements,
        )
        self.assertIn('MERGE (user)-[fact:HAS_EVENT]->(event)', statements)

    def test_delete_without_episode_uses_user_fact_authored_at(self):
        authored_at = '2026-07-20T10:00:00'

        class NoSourceTx(_WriteTx):
            def run(self, query, **params):
                if 'source.id IS NOT NULL AS has_source' in query:
                    self.calls.append((query, params))
                    return _Result([{
                        'memory_id': authored_at,
                        'has_source': False,
                    }])
                return super().run(query, **params)

        tx = NoSourceTx()
        request = self.factory.delete(
            f'/api/mymemory/memories/memory:{authored_at}/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(
                views, 'get_memory_driver',
                return_value=_Driver(_WriteSession(tx))):
            response = views.memory_vault_delete(
                request, f'memory:{authored_at}')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['deleted']['had_source'])
        statements = '\n'.join(query for query, _ in tx.calls)
        self.assertIn('fact.created_at', statements)
        self.assertIn('fact.valid_from', statements)
        self.assertNotIn('DETACH DELETE source', statements)

    def test_delete_unknown_memory_returns_404(self):
        class MissingTx(_WriteTx):
            def run(self, query, **params):
                self.calls.append((query, params))
                return _Result([])

        tx = MissingTx()
        request = self.factory.delete('/api/mymemory/memories/memory:missing/')
        force_authenticate(request, user=self.user)

        with mock.patch.object(
                views, 'get_memory_driver',
                return_value=_Driver(_WriteSession(tx))):
            response = views.memory_vault_delete(request, 'memory:missing')

        self.assertEqual(response.status_code, 404)

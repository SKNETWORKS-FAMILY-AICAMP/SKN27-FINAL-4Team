# -*- coding: utf-8 -*-
"""기억 시스템 안전장치 단위 테스트 (2026-07-14) — 상호작용 버그 재발 방지 박제.

배경: 안전장치들(keep 보호·dedup 병합·종결 합성·벡터 만료·접지 게이트)은 각각은
옳아도 조합에서 사고가 났다 (S04 회귀 등 — 전부 실측으로 발견). 이 테스트는 그
사고들의 재현 조건을 고정해, 누가 코드를 고쳐도 과거 버그가 부활하면 즉시 알린다.

실행: python manage.py test chat   (DB·Neo4j·LLM 불필요 — 전부 mock)
"""
from unittest import TestCase, mock

from chat import graph_memory as gm
from ai.agents import answer_guard as ag


class _FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def data(self):
        return self.rows

    def single(self):
        return self.rows[0] if self.rows else None

    def consume(self):
        class C:
            counters = type('K', (), {'properties_set': 0})()
        return C()


def _make_session(vec_hit=None, run_log=None):
    class FS:
        def run(self, q, **p):
            if run_log is not None:
                run_log.append((q, p))
            if 'queryNodes' in q:
                if vec_hit and p.get('vec') and p.get('min', 0) <= vec_hit['score'] \
                        and vec_hit.get('key') not in (p.get('keep') or []):
                    return _FakeResult([vec_hit])
                return _FakeResult([])
            return _FakeResult([])

        def execute_write(self, fn):
            fn(self)   # tx 역할 겸용

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    return FS()


class CaptureGuardTests(TestCase):
    """_capture 경로의 안전장치 조합"""

    def setUp(self):
        self.captured = {}
        self.run_log = []
        patches = [
            mock.patch.object(gm, 'is_enabled', return_value=True),
            mock.patch.object(gm, '_store',
                              side_effect=lambda tx, uid, data, salience=1.0,
                              vectors=None, expired_vectors=None: self.captured.update(data)),
            mock.patch('chat.embedder.embed', return_value=[1.0, 0.0]),
            mock.patch('chat.embedder.is_available', return_value=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _capture_with(self, data, message, vec_hit=None):
        session = _make_session(vec_hit=vec_hit, run_log=self.run_log)
        with mock.patch.object(gm, '_get_driver',
                               return_value=type('D', (), {'session': lambda s: session})()), \
             mock.patch.object(gm, '_extract', return_value=data):
            gm._capture(1, message)

    def test_closure_synthesis_when_extractor_omits(self):
        """expired만 오면 종결 사건 합성 — '취소됐다'는 사실도 기억이어야 한다 (S02~S04)"""
        self._capture_with({'expired': [{'kind': 'event', 'name': '제주도 여행'}]},
                           '아 제주도 여행 취소됐어 ㅠㅠ')
        names = [e['name'] for e in self.captured.get('events', [])]
        self.assertIn('제주도 여행 취소', names)

    def test_closure_synthesis_skips_forget(self):
        """잊어줘 요청은 종결 기록도 남기지 않는다 (재노출 금지)"""
        self._capture_with({'expired': [{'kind': 'event', 'name': '복권 구매',
                                         'reason': '사용자 요청'}]}, '복권 산 거 잊어줘')
        self.assertFalse(self.captured.get('events'))

    def test_capture_survives_string_expired_entry(self):
        """추출기가 expired에 문자열을 섞어도 캡처 전체가 죽지 않는다 (S01 크래시)"""
        self._capture_with({'events': [{'name': '준호와 이별'}],
                            'expired': ['준호', {'kind': 'person', 'name': '준호'}]},
                           '나 준호랑 헤어졌어')
        self.assertTrue(self.captured.get('events'))

    def test_dedup_never_merges_closure_into_original(self):
        """종결 기록('~취소')은 유사해도 원본에 병합 금지 — 병합되면 keep 보호가
        만료 도장을 막는 S04 회귀"""
        data = {'events': [{'name': '영화 약속 취소'}],
                'expired': [{'kind': 'event', 'name': '영화 약속', 'reason': '취소'}]}
        self._capture_with(data, '영화 약속 깨졌어',
                           vec_hit={'key': '영화보기', 'name': '영화 보기', 'score': 0.95})
        self.assertEqual(self.captured['events'][0]['name'], '영화 약속 취소')

    def test_normal_dedup_still_merges(self):
        """정상 병합('발표 대박'≈'발표 잘함')은 유지"""
        data = {'events': [{'name': '발표 대박'}]}
        self._capture_with(data, '발표 대박이었어',
                           vec_hit={'key': '발표잘함', 'name': '발표 잘함', 'score': 0.95})
        self.assertEqual(self.captured['events'][0]['name'], '발표 잘함')


class VectorExpireTests(TestCase):
    """만료 벡터 4단 — 오폭 방어 3종"""

    def _store_with(self, expired, vec_hit, events=None):
        log = []
        session = _make_session(vec_hit=vec_hit, run_log=log)
        data = {'expired': expired}
        if events:
            data['events'] = events
        ev = {e['name']: [1.0, 0.0] for e in expired
              if isinstance(e, dict) and e.get('kind') == 'event'}
        gm._store(session, 1, data, expired_vectors=ev)
        return [q for q, p in log]

    def test_vector_expire_fires_above_threshold(self):
        """문자열 3단 전멸 + 유사도 0.70 ≥ 0.60 → 만료 도장"""
        qs = self._store_with([{'kind': 'event', 'name': '운동 레슨', 'reason': '취소'}],
                              {'key': '헬스pt등록', 'name': '헬스 PT 등록', 'score': 0.70})
        self.assertTrue(any('Event {key:$key}' in q for q in qs))

    def test_vector_expire_respects_threshold(self):
        """0.48 < 0.60 → 아무것도 만료하지 않는다 (미스는 현상 유지, 오폭은 재앙)"""
        qs = self._store_with([{'kind': 'event', 'name': '동창회', 'reason': '취소'}],
                              {'key': '회사발표준비', 'name': '회사 발표 준비', 'score': 0.48})
        self.assertFalse(any('Event {key:$key}' in q for q in qs))

    def test_vector_expire_excludes_this_turn(self):
        """방금 저장한 자기 종결 기록이 1등이어도 keep 필터로 자폭 방지"""
        qs = self._store_with([{'kind': 'event', 'name': '운동 레슨', 'reason': '취소'}],
                              {'key': gm._norm_key('운동 레슨 취소'),
                               'name': '운동 레슨 취소', 'score': 0.92},
                              events=[{'name': '운동 레슨 취소'}])
        self.assertFalse(any('Event {key:$key}' in q for q in qs))


class AnswerGuardTests(TestCase):
    """접지 검증 — 게이트·결정적 판정·무해 폴백"""

    def test_gate_skips_plain_answers(self):
        """평범한 답변은 LLM 0회로 통과 (비용 0)"""
        with mock.patch.object(ag, '_verify_llm') as v:
            ok, _ = ag.check_grounded('오늘 기분은 어때? 산책 갈까?', '- 로또 당첨', 'q')
        self.assertTrue(ok)
        v.assert_not_called()

    def test_gate_catches_both_word_orders(self):
        """'많이 얘기했' / '얘기를 많이 했' 어순 양쪽 발동 (5회차 어순 구멍)"""
        for a in ('한강 얘기 많이 했던 것 같아', '한강 자전거 얘기를 많이 했던 것 같아'):
            self.assertTrue(bool(ag._PAST_CLAIM.search(a))
                            or bool(ag._FREQ.search(a) and ag._TALK.search(a)), a)

    def test_gate_ignores_comfort_expressions(self):
        """'많이 힘들었겠다' 같은 위로 표현은 비발동"""
        with mock.patch.object(ag, '_verify_llm') as v:
            ok, _ = ag.check_grounded('많이 힘들었겠다, 괜찮아?', '', 'q')
        self.assertTrue(ok)
        v.assert_not_called()

    def test_frequency_without_insight_fails_deterministically(self):
        """빈도 주장 + [요즘 흐름] 없음 → LLM 없이 즉시 위반 (검증자 관대함 배제)"""
        with mock.patch.object(ag, '_verify_llm') as v:
            ok, off = ag.check_grounded('한강 얘기를 많이 했어', '- 한강 자전거 여행', 'q')
        self.assertFalse(ok)
        v.assert_not_called()

    def test_frequency_with_insight_goes_to_llm(self):
        """[요즘 흐름] 있으면 LLM 검증 경유 — 근거 있으면 통과"""
        with mock.patch.object(ag, '_verify_llm', return_value=None) as v:
            ok, _ = ag.check_grounded('회사 얘기 자주 했잖아',
                                      '- 요즘 흐름: 회사 일로 무거움', 'q')
        self.assertTrue(ok)
        v.assert_called_once()

    def test_verifier_failure_is_harmless(self):
        """검증 LLM이 죽어도 통과 처리 — 챗봇 흐름 무중단"""
        with mock.patch.object(ag, '_verify_llm', side_effect=RuntimeError('down')):
            ok, _ = ag.check_grounded('전에 말했잖아', '', 'q')
        self.assertTrue(ok)

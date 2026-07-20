# -*- coding: utf-8 -*-
"""v2 기본 스키마(graph_memory_v2_base) 가드 테스트 (2026-07-16).

v1에서 실측으로 잡은 사고들의 재현 조건을 v2에 그대로 박제 — §8-4 회귀 방지의 실행분.
실행: python manage.py test chat.test_memory_guards_v2_base  (DB·Neo4j·LLM 불필요 — mock)
"""
from unittest import TestCase, mock

from chat import graph_memory_v2_base as gmb


class _FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def data(self):
        return self.rows

    def single(self):
        return self.rows[0] if self.rows else None


class _FakeTx:
    """_store용 가짜 트랜잭션 — 쿼리 로그 + 무효화 후보 조회 응답."""

    def __init__(self, candidates=None):
        self.log = []
        self.candidates = candidates or []

    def run(self, q, **p):
        self.log.append((q, p))
        if 'RETURN coalesce(n.key' in q:
            return _FakeResult([{'k': k} for k in self.candidates])
        return _FakeResult([])


class ClosureSynthesisTests(TestCase):
    """종결 기록 합성 (§8-4-1) — 순수 함수라 직접 검증"""

    def _names(self, data, message):
        out = gmb._synthesize_closures(data, message)
        return [e['name'] for e in out.get('events', [])]

    def test_synthesis_when_extractor_omits(self):
        """invalidations만 오면 종결 사건 합성 — '취소됐다'도 기억이다 (S02~S04)"""
        names = self._names({'invalidations': [{'kind': 'event', 'name': '제주도 여행',
                                                'reason': '취소'}]},
                            '아 제주도 여행 취소됐어 ㅠㅠ')
        self.assertIn('제주도 여행 취소', names)

    def test_fragment_dropped_and_synthesis_proceeds(self):
        """E2E 부산·강릉 실측: 맹탕 파편('여행')은 버려지고 종결 기록은 합성"""
        names = self._names({'events': [{'name': '여행'}],
                             'invalidations': [{'kind': 'event', 'name': '강릉 여행',
                                                'reason': '취소'}]},
                            '아 근데 강릉 여행 취소됐어 ㅠㅠ')
        self.assertIn('강릉 여행 취소', names)
        self.assertNotIn('여행', names)   # 파편 저장 금지 (keep 오염 방지)

    def test_bare_restatement_of_target_dropped(self):
        """S02-off 실측 (2026-07-19): 취소 발화에서 원본 이름('제주도 여행')이 이벤트로
        재발행되면 keep 보호가 만료를 막는다 — 맨몸 재진술은 버리고 종결 기록만 남긴다"""
        out = gmb._synthesize_closures(
            {'events': [{'name': '제주도 여행 취소'}, {'name': '제주도 여행'}],
             'invalidations': [{'kind': 'event', 'name': '제주도 여행', 'reason': '취소'}]},
            '아 제주도 여행 취소됐어 ㅠㅠ')
        names = [e['name'] for e in out['events']]
        self.assertIn('제주도 여행 취소', names)
        self.assertNotIn('제주도 여행', names)   # 맨몸 재진술 제거 → keep 오염 차단

    def test_real_closure_event_not_duplicated(self):
        """추출기가 진짜 종결 사건을 직접 내면 합성 안 함 (중복 방지)"""
        names = self._names({'events': [{'name': '강릉 여행 취소'}],
                             'invalidations': [{'kind': 'event', 'name': '강릉 여행'}]},
                            '강릉 여행 취소됐어')
        self.assertEqual(names.count('강릉 여행 취소'), 1)

    def test_kind_variants_tolerated(self):
        """E2E 속초 3연속: kind가 'Event'·'여행'·생략이어도 합성 (관용)"""
        for kind in ('Event', '여행', None):
            inv = {'name': '양양 여행', 'reason': '취소'}
            if kind is not None:
                inv['kind'] = kind
            names = self._names({'invalidations': [inv]}, '양양 여행 취소됐어 ㅠㅠ')
            self.assertIn('양양 여행 취소', names, f'kind={kind!r}에서 합성 실패')

    def test_person_and_preference_skipped(self):
        """person·preference 명시 만료는 합성 안 함 (이별 사건은 추출기 몫)"""
        names = self._names({'events': [{'name': '민수와 이별'}],
                             'invalidations': [{'kind': 'person', 'name': '민수',
                                                'reason': '이별'}]},
                            '민수랑 헤어졌어')
        self.assertEqual(names, ['민수와 이별'])

    def test_closure_word_not_doubled(self):
        """이름에 이미 종결어('그만두기')가 있으면 그대로 — '그만두기 그만둠' 방지 (S03)"""
        names = self._names({'invalidations': [{'kind': 'event',
                                                'name': '편의점 알바 그만두기'}]},
                            '편의점 알바 그만뒀어')
        self.assertIn('편의점 알바 그만두기', names)
        self.assertFalse(any('그만두기 그만둠' in n for n in names))

    def test_mid_name_stem_does_not_block_synthesis(self):
        """'퇴사 면담 예정'(어간이 중간·미래 일정)은 종결 사건이 아니다 — 끝단 앵커.
        이 사건이 있어도 다른 대상의 종결 합성은 진행돼야 한다"""
        names = self._names({'events': [{'name': '퇴사 면담 예정'}],
                             'invalidations': [{'kind': 'event', 'name': '헬스장 등록',
                                                'reason': '취소'}]},
                            '헬스장 등록 취소했어. 다음 주에 퇴사 면담 예정이야')
        self.assertIn('헬스장 등록 취소', names)
        self.assertIn('퇴사 면담 예정', names)   # 미래 일정은 그대로 살아있어야

    def test_forget_skips_synthesis(self):
        """잊어줘 요청은 종결 기록도 남기지 않는다 (재노출 금지, §8-4-4)"""
        names = self._names({'invalidations': [{'kind': 'event', 'name': '복권 구매',
                                                'forget': True,
                                                'reason': '사용자 요청'}]},
                            '복권 산 거 잊어줘')
        self.assertEqual(names, [])

    def test_survives_string_invalidation_entry(self):
        """추출기가 invalidations에 문자열을 섞어도 죽지 않는다 (S01 크래시)"""
        names = self._names({'events': [{'name': '준호와 이별'}],
                             'invalidations': ['준호', {'kind': 'person', 'name': '준호'}]},
                            '나 준호랑 헤어졌어')
        self.assertEqual(names, ['준호와 이별'])


class StoreInvalidationTests(TestCase):
    """_store 무효화 — §8-4-2 매칭 안전 + §8-4-4 잊어줘 분리 + keep 보호"""

    def _set_queries(self, tx):
        return [(q, p) for q, p in tx.log if 'SET r.valid_to=$today' in q]

    def test_token_and_matching_no_broad_expiry(self):
        """'강릉 여행' 만료가 '부산 여행'을 못 건드린다 — 전체 토큰 AND (포항 광역 오폭)"""
        tx = _FakeTx(candidates=['강릉여행', '부산여행'])
        gmb._store(tx, 1, {'invalidations': [{'kind': 'event', 'name': '강릉 여행',
                                              'reason': '취소'}]}, {}, '강릉 여행 취소됐어')
        stamped = [p['tk'] for q, p in self._set_queries(tx)]
        self.assertEqual(stamped, ['강릉여행'])

    def test_keep_protects_this_turn_closure(self):
        """방금 저장한 종결 기록('강릉 여행 취소')은 만료 대상에서 제외 — 자폭 방지"""
        tx = _FakeTx(candidates=['강릉여행', '강릉여행취소'])
        gmb._store(tx, 1, {'events': [{'name': '강릉 여행 취소'}],
                           'invalidations': [{'kind': 'event', 'name': '강릉 여행',
                                              'reason': '취소'}]}, {}, '강릉 여행 취소됐어')
        stamped = [p['tk'] for q, p in self._set_queries(tx)]
        self.assertIn('강릉여행', stamped)
        self.assertNotIn('강릉여행취소', stamped)

    def test_forget_person_suppresses_involved_events(self):
        """잊어줘(인물) → 그 인물이 얽힌 사건까지 재노출 금지 (F02 실측: '소개팅' 되노출)"""
        tx = _FakeTx(candidates=['현우'])
        gmb._store(tx, 1, {'invalidations': [{'kind': 'relation', 'name': '현우',
                                              'forget': True}]}, {}, '현우 얘기는 잊어줘')
        self.assertTrue(any('INVOLVES' in q and 'e.suppressed=true' in q
                            for q, p in tx.log))

    def test_cancel_person_does_not_suppress_events(self):
        """이별(supersede)은 역사 보존 — 인물 관련 사건을 건드리지 않는다"""
        tx = _FakeTx(candidates=['준호'])
        gmb._store(tx, 1, {'invalidations': [{'kind': 'relation', 'name': '준호',
                                              'reason': '이별'}]}, {}, '준호랑 헤어졌어')
        self.assertFalse(any('INVOLVES' in q and 'e.suppressed=true' in q
                             for q, p in tx.log))

    def test_forget_marks_suppressed_supersede_does_not(self):
        """잊어줘 → suppressed 재노출 금지 / 취소 → 역사 보존 (§8-4-4 분리)"""
        tx = _FakeTx(candidates=['복권구매'])
        gmb._store(tx, 1, {'invalidations': [{'kind': 'event', 'name': '복권 구매',
                                              'forget': True}]}, {}, '복권 산 거 잊어줘')
        forget_qs = self._set_queries(tx)
        self.assertTrue(any('n.suppressed=true' in q for q, p in forget_qs))
        self.assertEqual(forget_qs[0][1]['reason'], '사용자 요청')

        tx2 = _FakeTx(candidates=['강릉여행'])
        gmb._store(tx2, 1, {'invalidations': [{'kind': 'event', 'name': '강릉 여행',
                                               'reason': '취소'}]}, {}, '강릉 여행 취소됐어')
        cancel_qs = self._set_queries(tx2)
        self.assertFalse(any('n.suppressed=true' in q for q, p in cancel_qs))


class StoreDateTests(TestCase):
    """C1 — 기간 사건(occurs)·ON{role}·부활"""

    def test_revive_on_future_date(self):
        """같은 key + 미래 날짜 재등록 → valid_to 해제 (§8-4-3 부활)"""
        tx = _FakeTx()
        gmb._store(tx, 1, {'events': [{'name': '제주 여행', 'date': '2099-01-01'}]},
                   {}, '제주 다시 가기로 했어!')
        self.assertTrue(any('SET r.valid_to=null' in q for q, p in tx.log))

    def test_no_revive_without_date(self):
        """date 없는 회고성 언급은 부활 금지"""
        tx = _FakeTx()
        gmb._store(tx, 1, {'events': [{'name': '제주 여행', 'date': ''}]},
                   {}, '예전에 제주 갔었잖아')
        self.assertFalse(any('SET r.valid_to=null' in q for q, p in tx.log))

    def test_period_event_gets_role_edges_and_occurs(self):
        """기간 사건 → ON{role:start}+ON{role:'end'} 두 가닥 + occurs_* 속성 동시 기록"""
        tx = _FakeTx()
        gmb._store(tx, 1, {'events': [{'name': '부산 여행', 'date': '2099-07-20',
                                       'date_end': '2099-07-23'}]}, {}, '20~23일 부산 가')
        ev_q, ev_p = next((q, p) for q, p in tx.log if 'MERGE (e:Event' in q)
        self.assertEqual(ev_p['ds'], '2099-07-20')
        self.assertEqual(ev_p['de'], '2099-07-23')
        roles = [p.get('role') for q, p in tx.log if '[r:ON {role:$role}]' in q]
        self.assertEqual(roles, ['start'])
        self.assertTrue(any("role:'end'" in q for q, p in tx.log))

    def test_single_day_event_role_on(self):
        """하루짜리 사건 → role:'on' 한 가닥"""
        tx = _FakeTx()
        gmb._store(tx, 1, {'events': [{'name': '병원 방문', 'date': '2099-07-20'}]},
                   {}, '20일에 병원 가')
        roles = [p.get('role') for q, p in tx.log if '[r:ON {role:$role}]' in q]
        self.assertEqual(roles, ['on'])
        self.assertFalse(any("role:'end'" in q for q, p in tx.log))


class NormShapeTests(TestCase):
    """추출 JSON 형식 정규화 — 단일 객체 사고 박제 (2026-07-16 실측: 62% 붕괴 원인)"""

    def test_single_dict_event_wrapped_to_list(self):
        """LLM이 events를 배열 없이 단일 객체로 내면 [dict]로 감싼다"""
        d = gmb._norm_shape({'events': {'name': '병원 방문', 'date': '2026-07-20'}})
        self.assertEqual(d['events'], [{'name': '병원 방문', 'date': '2026-07-20'}])

    def test_dict_preferences_no_key_leak(self):
        """preferences가 dict로 와도 키('topic','polarity')가 항목으로 새지 않는다"""
        d = gmb._norm_shape({'preferences': {'topic': '클라이밍', 'polarity': '호'}})
        self.assertEqual(d['preferences'], [{'topic': '클라이밍', 'polarity': '호'}])

    def test_garbage_field_dropped(self):
        """문자열·숫자 같은 쓰레기 형식은 빈 배열로"""
        d = gmb._norm_shape({'events': 'topic: 클라이밍', 'relations': 3})
        self.assertEqual(d['events'], [])
        self.assertEqual(d['relations'], [])

    def test_proper_lists_untouched(self):
        d = gmb._norm_shape({'events': [{'name': 'x'}], 'invalidations': []})
        self.assertEqual(d['events'], [{'name': 'x'}])


class DeriveInvalidationTests(TestCase):
    """만료 누락 역합성 — S03-off 실측 (추출이 종결 이벤트만 내고 invalidations 누락)"""

    def test_closure_event_without_invalidation_derives_target(self):
        d = gmb._derive_invalidations_from_closures(
            {'events': [{'name': '편의점 알바 그만둠'}]}, '편의점 알바 그만뒀어 사장이 진상이라')
        self.assertEqual(d['invalidations'],
                         [{'kind': 'event', 'name': '편의점 알바', 'forget': False}])

    def test_existing_invalidations_untouched(self):
        d = gmb._derive_invalidations_from_closures(
            {'events': [{'name': '제주 여행 취소'}],
             'invalidations': [{'kind': 'event', 'name': '제주 여행'}]}, '제주 여행 취소됐어')
        self.assertEqual(len(d['invalidations']), 1)
        self.assertEqual(d['invalidations'][0]['name'], '제주 여행')

    def test_total_extraction_miss_parses_from_message(self):
        """추출이 invalidations·종결 이벤트 둘 다 놓쳐도 발화에서 대상 파싱 (최후 방어)"""
        d = gmb._derive_invalidations_from_closures(
            {'events': []}, '나 편의점 알바 그만뒀어 사장이 너무 진상이라')
        self.assertEqual(d['invalidations'][0]['name'], '편의점 알바')

    def test_message_parse_strips_leading_fillers(self):
        """'아 제주도 여행 취소됐어' — 감탄사·1글자 조각은 대상에서 제외"""
        d = gmb._derive_invalidations_from_closures(
            {'events': []}, '아 제주도 여행 취소됐어 ㅠㅠ')
        self.assertEqual(d['invalidations'][0]['name'], '제주도 여행')

    def test_no_closure_phrase_no_derivation(self):
        """종결 발화가 아니면 유도 금지 — '퇴사 면담 예정' 같은 미래 일정 오폭 방지"""
        d = gmb._derive_invalidations_from_closures(
            {'events': [{'name': '퇴사 면담 예정'}]}, '다음 주에 퇴사 면담 있어')
        self.assertFalse(d.get('invalidations'))


class ForgetDemoteTests(TestCase):
    """forget 오분류 강등 — S05 실측 (2026-07-18): '취소됐어'를 forget:true로 오분류"""

    def test_cancel_without_forget_phrase_demoted(self):
        d = gmb._demote_unhinted_forget(
            {'invalidations': [{'kind': 'event', 'name': '운동 레슨', 'forget': True}]},
            '운동 레슨 취소됐어, 강사가 그만뒀대')
        self.assertFalse(d['invalidations'][0]['forget'])

    def test_explicit_forget_phrase_kept(self):
        for msg in ('복권 산 거 잊어줘', '그 얘긴 기억하지 마', '현우 기록 지워줘'):
            d = gmb._demote_unhinted_forget(
                {'invalidations': [{'kind': 'event', 'name': 'x', 'forget': True}]}, msg)
            self.assertTrue(d['invalidations'][0]['forget'], msg)


class ResolveInvalidationTests(TestCase):
    """만료 대상 해석 — 결정 매칭 실패 시 LLM 폴백 (S05 '운동 레슨'→'PT 첫 수업' 실측)"""

    def _drv(self, events):
        rows = [{'n': n} for n in events]

        class S:
            def run(self, q, **p):
                return _FakeResult(rows if 'HAS_EVENT' in q else [])

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return type('D', (), {'session': lambda s: S()})()

    def _with_fake_llm(self, content):
        import sys
        fake = mock.MagicMock()
        if content is not None:
            fake.get_llm.return_value.invoke.return_value = mock.Mock(content=content)
        return fake, mock.patch.dict(sys.modules, {
            'ai': mock.MagicMock(), 'ai.agents': mock.MagicMock(),
            'ai.agents.llm': fake})

    def test_token_match_short_circuits_llm(self):
        """결정 매칭이 잡으면 LLM 호출 0 (비용 0 경로)"""
        fake, patcher = self._with_fake_llm(None)
        with patcher:
            d = gmb._resolve_invalidations(
                self._drv(['강릉 여행']), 1,
                {'invalidations': [{'kind': 'event', 'name': '강릉 여행'}]})
        fake.get_llm.assert_not_called()
        self.assertEqual(d['invalidations'][0]['name'], '강릉 여행')

    def test_llm_fallback_resolves_paraphrase(self):
        """글자 0겹침('운동 레슨' vs 'PT 첫 수업') → LLM이 대상 해석"""
        fake, patcher = self._with_fake_llm('PT 첫 수업')
        with patcher:
            d = gmb._resolve_invalidations(
                self._drv(['PT 첫 수업', '지은 생일']), 1,
                {'invalidations': [{'kind': 'event', 'name': '운동 레슨'}]})
        self.assertEqual(d['invalidations'][0]['name'], 'PT 첫 수업')

    def test_llm_uncertain_keeps_original(self):
        """LLM이 '없음'이면 현상 유지 — 미스는 안전, 오폭은 재앙"""
        fake, patcher = self._with_fake_llm('없음')
        with patcher:
            d = gmb._resolve_invalidations(
                self._drv(['지은 생일']), 1,
                {'invalidations': [{'kind': 'event', 'name': '운동 레슨'}]})
        self.assertEqual(d['invalidations'][0]['name'], '운동 레슨')

    def test_llm_offlist_pick_ignored(self):
        """LLM이 목록에 없는 이름을 지어내면 무시 — 환각 주입 차단"""
        fake, patcher = self._with_fake_llm('헬스장 등록')
        with patcher:
            d = gmb._resolve_invalidations(
                self._drv(['지은 생일']), 1,
                {'invalidations': [{'kind': 'event', 'name': '운동 레슨'}]})
        self.assertEqual(d['invalidations'][0]['name'], '운동 레슨')


class CausalQuestionTests(TestCase):
    """인과 사슬 주입 게이트 (⑤) — '왜' 질문에만 열리는 결정적 게이트"""

    def test_causal_questions_detected(self):
        for q in ('나 요즘 왜 우울하지?', '이게 다 뭐 때문일까', '내가 힘든 이유가 뭘까'):
            self.assertTrue(gmb._causal_question(q), q)

    def test_plain_questions_not_causal(self):
        for q in ('나 다음 주에 뭐 있었지?', '우리 강아지 이름 기억나?', '오늘 날씨 좋다'):
            self.assertFalse(gmb._causal_question(q), q)


class CrisisGateTests(TestCase):
    """위기 게이트 — 위기 발화는 그래프에 박제하지 않는다 (v1 보안 자산)"""

    def test_crisis_turn_skips_capture_entirely(self):
        with mock.patch.object(gmb, '_get_driver') as drv, \
                mock.patch.object(gmb, '_extract') as ex:
            gmb._capture(1, '요즘 너무 힘들어서 다 끝내고 싶어', crisis=True)
        drv.assert_not_called()
        ex.assert_not_called()

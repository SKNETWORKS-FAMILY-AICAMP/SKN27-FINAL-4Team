# -*- coding: utf-8 -*-
"""memory_audit — 그래프 기억의 '실측' 커맨드 (2026-07-21)

배경:
  "2턴부터도 그래프만으로 대화가 되냐"는 질문에 대해, 그동안 근거로 든
  ① 봇 발화 없음 ② 지시어 복원 불가 ③ 최근 턴 대부분 미저장
  중 ①만 코드로 확인됐고 ②③은 추론이었다. 이 커맨드는 ③과 ①을 숫자로 만든다.
  (②는 대화 실험이 필요해 이 커맨드 범위 밖 — 아래 '측정 안 되는 것' 참고)

측정 항목:
  1. 사용자 턴 수 vs 그래프 Event 수 → 그래프 저장률(%)
  2. 그래프에 assistant 발화가 정말 0건인지 (capture_async 경로 확인)
  3. recall() 출력 길이 — 원문 N턴 대비 토큰 비교용

사용:
  docker compose exec web python manage.py memory_audit
  docker compose exec web python manage.py memory_audit --user 1
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = '그래프 기억 저장률·봇발화·recall 길이 실측'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, default=None,
                            help='특정 user_id만 측정 (미지정 시 전체 유저 순회)')

    def handle(self, *args, **opts):
        from chat.models import ChatMessage, ChatSession
        # 운영 스키마는 v2 — v1(graph_memory) 기준으로 재면 자가 휜다 (2026-07-21 실측:
        # KNOWS·valid_until은 v1 유물이라 Person 0명·유효율 100%로 오측정됐음)
        from chat import graph_memory_v2_base as gmem
        from chat import memory_backend

        w = self.stdout.write

        w('=' * 62)
        w(' 그래프 기억 실측 (memory_audit)')
        w('=' * 62)

        if not gmem.is_enabled():
            w(self.style.ERROR('Neo4j 비활성 — NEO4J_URI/USER/PASSWORD 확인 필요. 중단.'))
            return

        drv = gmem._get_driver()

        # 대상 유저 결정
        if opts['user']:
            uids = [opts['user']]
        else:
            uids = list(
                ChatSession.objects.exclude(user__isnull=True)
                .values_list('user_id', flat=True).distinct()
            )
        if not uids:
            w(self.style.WARNING('측정할 로그인 유저가 없음.'))
            return

        w(f'대상 유저: {len(uids)}명 {uids}\n')

        # ── 2. 그래프에 assistant 발화가 있는지 (전역 1회) ──
        #    Event는 사용자 발화에서만 추출되므로 0이어야 정상.
        #    Event에 role/speaker 속성 자체가 없다는 것도 같이 확인.
        with drv.session() as s:
            props = s.run(
                'MATCH (e:Event) WITH keys(e) AS k UNWIND k AS p '
                'RETURN DISTINCT p ORDER BY p'
            ).value()
        w('[Event 노드가 실제로 가진 속성 — 원문/화자 필드 유무 확인]')
        w(f'  {props}')
        has_text = [p for p in props if p in ('text', 'raw', 'utterance', 'content', 'role', 'speaker')]
        if has_text:
            w(self.style.WARNING(f'  ⚠ 원문/화자성 속성 발견: {has_text}'))
        else:
            w(self.style.SUCCESS('  ✓ 원문·화자 속성 없음 → 대화 재구성 불가 확인'))
        w('')

        tot_user_turns = tot_events = 0

        for uid in uids:
            w('-' * 62)
            w(f'user_id={uid}')

            user_turns = ChatMessage.objects.filter(
                session__user_id=uid, role='user').count()
            asst_turns = ChatMessage.objects.filter(
                session__user_id=uid, role='assistant').count()

            with drv.session() as s:
                ev = s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                           'RETURN count(e) AS c', uid=uid).single()['c']
                # 유효 = HAS_EVENT '간선'의 valid_to가 비어 있는 것 (노드 속성 아님 — v2 규약)
                ev_live = s.run('MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                                'WHERE h.valid_to IS NULL '
                                'RETURN count(e) AS c', uid=uid).single()['c']
                # 인물 = 관계 선언(RELATES_TO) + 사건 등장(INVOLVES) 모두 (KNOWS는 v1 유물)
                ppl = s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT|RELATES_TO]->(x) '
                            'OPTIONAL MATCH (x)-[:INVOLVES]->(q:Person) '
                            'WITH collect(CASE WHEN x:Person THEN x END) + collect(q) AS ps '
                            'UNWIND ps AS p WITH p WHERE p IS NOT NULL '
                            'RETURN count(DISTINCT p) AS c', uid=uid).single()['c']

            tot_user_turns += user_turns
            tot_events += ev

            rate = (ev / user_turns * 100) if user_turns else 0.0
            w(f'  Postgres  사용자 턴 {user_turns}  /  봇 턴 {asst_turns}')
            w(f'  Neo4j     Event {ev} (유효 {ev_live}) · Person {ppl}')
            w(f'  → 그래프 저장률: {rate:.1f}%  (Event수 / 사용자턴수)')
            w(f'  → 봇 턴 {asst_turns}건은 그래프에 0건 (Event는 사용자 발화에서만 추출)')

            # ── 3. recall 출력 길이 vs 최근 N턴 원문 길이 ──
            try:
                rc = memory_backend.recall(uid) or ''
            except Exception as e:
                rc = ''
                w(self.style.WARNING(f'  recall 실패: {e}'))
            n = getattr(settings, 'CHAT_RECENT_N', 10)
            recent = list(ChatMessage.objects.filter(session__user_id=uid)
                          .order_by('-created_at')[:n])
            raw_len = sum(len(m.content or '') for m in recent)
            w(f'  recall() 길이 {len(rc)}자  vs  최근 {n}턴 원문 {raw_len}자')

        w('=' * 62)
        overall = (tot_events / tot_user_turns * 100) if tot_user_turns else 0.0
        w(f' 전체 그래프 저장률: {overall:.1f}%  '
          f'(Event {tot_events} / 사용자턴 {tot_user_turns})')
        w('=' * 62)
        w('')
        w('[이 커맨드로 측정 안 되는 것]')
        w(' - 지시어("그거/왜") 복원 가능 여부: 대화 실험 필요(27종 평가 틀 사용)')
        w(' - 원문 없이 recall만으로 대화 품질이 어디서 깨지는지: 정성 평가 필요')
        w(' * 저장률 숫자만으로 "그래프 단독 불가"를 단정하지 말 것.')

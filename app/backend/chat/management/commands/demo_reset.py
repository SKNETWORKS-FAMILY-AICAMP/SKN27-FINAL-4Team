# -*- coding: utf-8 -*-
"""데모/검증용 전체 초기화 (2026-07-14) — 신규 사용자 상태로 리셋.

지우는 것: 대화(세션·메시지), 장기 요약, 그래프 기억(Neo4j 전체), MBTI 응답·리포트,
          마음 리포트, 데일리 운세 — 즉 "사용자가 쌓은 데이터" 전부
남기는 것: 계정(로그인 정보), 벡터 인덱스(자동 유지), 코드·설정

사용: python manage.py demo_reset --yes     (--yes 없이는 개수만 보여주고 안 지움)
용도: ① 신규 사용자 E2E 검증 ② 시연 직전 클린 세팅 (데모 기억 심기 전 단계)
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '사용자 데이터 전체 초기화 (계정은 유지) — 신규 상태 E2E 검증·시연 준비용'

    def add_arguments(self, p):
        p.add_argument('--yes', action='store_true', help='실제 삭제 실행 (없으면 미리보기만)')

    def handle(self, *args, **opts):
        w = self.stdout.write
        targets = []

        from chat.models import ChatSession, ChatMessage, UserMemory, MbtiAnswer
        targets += [ChatMessage, ChatSession, UserMemory, MbtiAnswer]
        try:
            from mbti.models import (MbtiQuestionResponse, MbtiResponseScore,
                                     MbtiMonthlyResultRecord, MbtiMonthlyAxisResult,
                                     MbtiMonthlyReport)
            targets += [MbtiQuestionResponse, MbtiResponseScore,
                        MbtiMonthlyResultRecord, MbtiMonthlyAxisResult, MbtiMonthlyReport]
        except Exception:
            pass
        try:
            from mindreport.models import MindReport
            targets.append(MindReport)
        except Exception:
            pass
        try:
            from calendar_api.models import DailyFortune
            targets.append(DailyFortune)
        except Exception:
            pass

        w('━━ 초기화 대상 (Postgres) ━━')
        for m in targets:
            w(f'  {m.__name__:<28} {m.objects.count():>6}건')

        from chat import graph_memory_v2_base as graph_memory   # v1 철거 (2026-07-21)
        neo_count = 0
        if graph_memory.is_enabled():
            drv = graph_memory._get_driver()
            with drv.session() as s:
                neo_count = s.run('MATCH (n) RETURN count(n) AS c').single()['c']
        w(f'  {"Neo4j 노드 (전체)":<27} {neo_count:>6}개')

        if not opts['yes']:
            w('\n미리보기 모드 — 실제 삭제하려면: python manage.py demo_reset --yes')
            return

        w('\n━━ 삭제 실행 ━━')
        for m in targets:   # FK 역순 고려: 메시지→세션 순서로 이미 배치
            n, _ = m.objects.all().delete()
            w(f'  {m.__name__}: {n}건 삭제')
        if graph_memory.is_enabled():
            with graph_memory._get_driver().session() as s:
                s.run('MATCH (n) DETACH DELETE n')
            w(f'  Neo4j: {neo_count}개 노드 전체 삭제 (벡터 인덱스는 유지됨)')
        w('\n완료 — 계정은 그대로. 로그인하면 신규 사용자 상태로 시작합니다.')

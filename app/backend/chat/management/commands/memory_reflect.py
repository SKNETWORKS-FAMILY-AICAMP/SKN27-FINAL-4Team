# -*- coding: utf-8 -*-
"""리플렉션 실행 (2026-07-13) — 기억 군집 → 통찰 생성.

사용: python manage.py memory_reflect            # 모든 사용자
      python manage.py memory_reflect --uid 1    # 특정 사용자

배치 결정과 분리된 설계: 지금은 수동/시연 전 실행, 배포 후 팀이 야간 배치를
켜면 cron에 이 한 줄만 등록하면 됨. recall은 통찰 없으면 no-op이라 안 돌려도 무해.
"""
from django.core.management.base import BaseCommand

from chat import graph_memory


class Command(BaseCommand):
    help = '기억 리플렉션 — 군집(θ=0.22 실측) → 통찰 노드 생성'

    def add_arguments(self, p):
        p.add_argument('--uid', type=int, default=None)

    def handle(self, *args, **opts):
        w = self.stdout.write
        if not graph_memory.is_enabled():
            self.stderr.write('Neo4j 비활성 — .env NEO4J_* 확인')
            return
        if opts['uid']:
            uids = [opts['uid']]
        else:
            drv = graph_memory._get_driver()
            with drv.session() as s:
                uids = [r['uid'] for r in
                        s.run('MATCH (u:User) RETURN u.uid AS uid ORDER BY uid').data()]
        w(f'대상 사용자 {len(uids)}명')
        for uid in uids:
            r = graph_memory.reflect(uid)
            if r['status'] == 'skipped':
                w(f"  uid {uid}: 스킵 (기억 {r['memories']}개 < {graph_memory.REFLECT_MIN_MEMORIES})")
            elif r['status'] == 'ok':
                w(f"  uid {uid}: 기억 {r['memories']}개 → 통찰 {len(r['insights'])}개")
                for text, size in r['insights']:
                    w(f'     · "{text}" (근거 {size}개)')
            else:
                w(f"  uid {uid}: {r['status']} {r.get('error', '')}")

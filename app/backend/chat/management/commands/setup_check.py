# -*- coding: utf-8 -*-
"""백엔드 셋업 자가진단 (2026-07-13) — 새 환경에서 뭐가 부러졌는지 한 방에.

사용: python manage.py setup_check
각 항목 ✓/✗ 와 고치는 법을 출력. 팀원 온보딩·시연 전 점검용.
"""
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '환경 자가진단 — env·DB·Neo4j·임베딩·LLM 연결 전수 점검'

    def handle(self, *args, **opts):
        w = self.stdout.write
        results = []

        def check(name, fn, fix):
            try:
                detail = fn() or ''
                results.append(True)
                w(f'  ✓ {name}  {detail}')
            except Exception as e:
                results.append(False)
                w(f'  ✗ {name} — {str(e)[:80]}')
                w(f'    → 조치: {fix}')

        w('━━ 빈틈사이 백엔드 자가진단 ━━')

        # ① .env 필수 키
        def env_keys():
            need = ['OPENAI_API_KEY', 'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
            missing = [k for k in need if not os.environ.get(k, '').strip()]
            if missing:
                raise RuntimeError('누락: ' + ', '.join(missing))
            return f'({len(need)}개 모두 있음)'
        check('.env 필수 키', env_keys, '.env에 누락 키 추가 (팀 채팅의 .env 템플릿 참고)')

        # ② Postgres
        def pg():
            from django.db import connection
            with connection.cursor() as c:
                c.execute('SELECT 1')
            return f"({connection.settings_dict.get('HOST')}:{connection.settings_dict.get('PORT')})"
        check('Postgres 연결', pg, 'docker compose up -d db  (컨테이너 wellness_postgres 확인)')

        # ③ Neo4j
        def neo():
            from chat import graph_memory_v2_base as graph_memory   # v1 철거 (2026-07-21)
            if not graph_memory.is_enabled():
                raise RuntimeError('연결 실패 — URI/비밀번호 또는 컨테이너')
            return f"({os.environ.get('NEO4J_URI')})"
        check('Neo4j 연결 (기억 시스템)', neo,
              'docker compose up -d neo4j + .env NEO4J_URI=bolt://localhost:7687 확인')

        # (④ 벡터 인덱스·⑤ 임베딩 검사 제거 — 임베딩 완전 철거 2026-07-21.
        #  의미 연결은 LLM 폴백 경로라 별도 인프라 검사가 필요 없음)

        # ⑥ sklearn (리플렉션)
        def skl():
            from sklearn.cluster import AgglomerativeClustering  # noqa
        check('scikit-learn (리플렉션)', skl, 'uv pip install -r requirements.txt')

        # ⑦ OpenAI 호출
        def llm():
            from ai.agents.llm import get_llm
            r = get_llm(temperature=0, max_tokens=5).invoke([('user', 'hi')])
            if not (r.content or '').strip():
                raise RuntimeError('빈 응답')
        check('LLM 호출 (OpenAI)', llm, '.env OPENAI_API_KEY 확인 (챗봇·추출·통찰 전부 여기 의존)')

        w('')
        ok = sum(results)
        if ok == len(results):
            w(f'━━ {ok}/{len(results)} 전부 통과 — 챗봇·기억·의미검색·리플렉션 풀가동 상태 ━━')
        else:
            w(f'━━ {ok}/{len(results)} 통과 — ✗ 항목의 조치를 위에서부터 순서대로 ━━')
            w('   (Neo4j 계열 ✗는 기억 기능만 꺼질 뿐 챗봇은 동작함)')

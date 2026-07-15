# -*- coding: utf-8 -*-
"""기억 시스템 정량 평가 (2026-07-12) — 회상 정확도·환각률·망각 준수율.

사용법:
    python manage.py memory_eval              # 전체 20 시나리오
    python manage.py memory_eval --only M01   # 특정 시나리오만
    python manage.py memory_eval --limit 5    # 앞 N개만

설계:
- 격리 uid(987001~)로 실행 → 실사용 데이터 무오염. 시작·종료 시 평가 uid 그래프 전체 삭제.
- 채팅 API를 거치지 않고 기억 레이어 직접 구동(_capture 동기 호출) → TTS 미사용, 결정적.
- 응답자는 실제 프롬프트(COMMON_RULES)와 같은 규칙 + [기억] 컨텍스트만으로 답변 →
  '기억 레이어가 만든 컨텍스트로 올바른 답이 나오는가'를 측정 (추출→저장→회상→활용 E2E).
"""
import json

from django.core.management.base import BaseCommand

from chat import graph_memory
from chat.memory_eval_scenarios import NOISE_POOL, SCENARIOS

EVAL_UID_BASE = 987000


def _llm(temperature=0, max_tokens=200):
    from ai.agents.llm import get_llm
    return get_llm(temperature=temperature, max_tokens=max_tokens)


def _wipe(uid: int):
    """평가 uid의 그래프 노드 전체 삭제 (격리 보장)."""
    drv = graph_memory._get_driver()
    with drv.session() as s:
        s.run('MATCH (n) WHERE n.uid = $uid DETACH DELETE n', uid=uid)


def _answer(recall_text: str, question: str) -> str:
    """실서비스와 같은 규칙(COMMON_RULES)으로 [기억]만 근거 삼아 답변."""
    from ai.agents.personas import COMMON_RULES
    memory_block = f'[사용자에 대한 기억 요약]\n{recall_text}' if recall_text.strip() \
        else '[사용자에 대한 기억 요약]\n(없음)'
    resp = _llm(temperature=0.3, max_tokens=150).invoke([
        ('system', COMMON_RULES + '\n\n' + memory_block),
        ('user', question),
    ])
    text = resp.content.strip()
    # 접지 검증 — 운영(resp_prep_node)과 동일 가드 (2026-07-14)
    from ai.agents.answer_guard import check_grounded, retry_instruction
    for attempt in (1, 2):   # 운영(resp_prep_node)과 동일한 2단 재생성 루프
        ok, offending = check_grounded(text, recall_text, question)
        if ok:
            break
        resp = _llm(temperature=0.3, max_tokens=150).invoke([
            ('system', COMMON_RULES + '\n\n' + memory_block
             + '\n\n' + retry_instruction(offending, attempt)),
            ('user', question),
        ])
        text = resp.content.strip() or text
    return text


def _grade_keywords(answer: str, expect_any, forbid):
    for group in (expect_any or []):
        if not any(k in answer for k in group):
            return False, f'기대 키워드 그룹 미포함: {group}'
    for k in (forbid or []):
        if k in answer:
            return False, f'금지 키워드 등장: {k}'
    return True, ''


def _grade_llm_once(answer: str, rubric: str, today: str, question: str,
                    temperature: float):
    resp = _llm(temperature=temperature, max_tokens=150).invoke([
        ('system',
         '채점자다. 기준을 문자 그대로 적용하라.\n'
         '1) 첫 줄: 답변이 기준의 fail 조건에 해당하는지 한 문장으로 판단 근거.\n'
         '2) 마지막 줄: pass 또는 fail 한 단어만.\n'
         '기준이 pass로 규정한 답변 유형이면 반드시 pass다. '
         'fail은 fail 조건에 명확히 해당할 때만.\n'
         f'(오늘 날짜: {today})\n[기준]\n' + rubric),
        ('user', f'[질문]\n{question}\n\n[답변]\n{answer}'),
    ])
    text = (resp.content or '').strip().lower()
    last = text.splitlines()[-1].strip() if text else ''
    if 'pass' in last or 'fail' in last:
        return 'pass' in last
    return 'pass' in text and 'fail' not in text   # 형식 미준수 폴백


def _grade_llm(answer: str, rubric: str, today: str, question: str = ''):
    # 다수결 3표 (2026-07-14): 채점자 1명은 명백한 정답도 가끔 fail로 찍음
    # (S01·S02·S05에서 실측). temp 0.5로 표를 다양화해 3표 다수결 — 개별 표는
    # 흔들려도 다수결은 안정 (앙상블). 첫 2표가 일치하면 3표째 생략(비용 절감).
    votes = []
    for i in range(3):
        try:
            votes.append(_grade_llm_once(answer, rubric, today, question, temperature=0.5))
        except Exception:
            votes.append(False)
        if len(votes) == 2 and votes[0] == votes[1]:
            break   # 만장일치 조기 종료
    ok = votes.count(True) > len(votes) / 2
    detail = '표결 ' + '/'.join('P' if v else 'F' for v in votes)
    return ok, detail


class Command(BaseCommand):
    help = '기억 시스템 정량 평가 (회상 정확도·환각률·망각 준수율)'

    def add_arguments(self, parser):
        parser.add_argument('--only', type=str, default=None)
        parser.add_argument('--limit', type=int, default=None)
        parser.add_argument('--debug', action='store_true',
                            help='추출 LLM의 JSON 출력을 그대로 표시 (진단용)')
        parser.add_argument('--runs', type=int, default=1,
                            help='반복 실행 횟수 — LLM 변동성 보정, 평균±범위 보고 (권장 3)')

    def handle(self, *args, **opts):
        if not graph_memory.is_enabled():
            self.stderr.write('Neo4j 비활성 — .env NEO4J_* 설정 확인')
            return
        # 평가 전용 안전장치: LLM 호출 무한 대기 방지 (타임아웃 45초·재시도 1회).
        # get_llm을 감싸서 이 프로세스 안의 모든 호출(_extract 포함)에 적용 — 서비스 코드 무변경.
        import ai.agents.llm as _llm_mod
        _orig_get_llm = _llm_mod.get_llm
        def _timed_get_llm(temperature=0.7, max_tokens=300):
            llm = _orig_get_llm(temperature=temperature, max_tokens=max_tokens)
            try:
                llm.request_timeout = 45
                llm.max_retries = 1
            except Exception:
                pass
            return llm
        _llm_mod.get_llm = _timed_get_llm
        if opts.get('debug'):
            _orig_extract = graph_memory._extract
            def _debug_extract(message):
                data = _orig_extract(message)
                self.stdout.write(f'    [추출] "{message[:40]}" → '
                                  + json.dumps(data, ensure_ascii=False)[:250])
                return data
            graph_memory._extract = _debug_extract
        today = graph_memory._today_iso()
        scenarios = SCENARIOS
        if opts['only']:
            wanted = {x.strip() for x in opts['only'].split(',') if x.strip()}
            scenarios = [s for s in scenarios if s['id'] in wanted]
        if opts['limit']:
            scenarios = scenarios[:opts['limit']]

        n_runs = max(1, opts.get('runs') or 1)
        all_totals, all_by_type = [], []
        self.stdout.write(f'기억 평가 시작 — {len(scenarios)}개 시나리오 × {n_runs}회 (오늘: {today})\n')
        results = []

        for run_no in range(1, n_runs + 1):
          if n_runs > 1:
              self.stdout.write(f'\n───── {run_no}/{n_runs}회차 ─────')
          results = []
          for i, sc in enumerate(scenarios):
            uid = EVAL_UID_BASE + i + 1
            _wipe(uid)
            try:
                # 심기 + 노이즈 (동기 — 결정적 실행)
                self.stdout.write(f"  {sc['id']} 진행 중"
                                  f" (LLM 호출 {len(sc['plant']) + sc.get('noise', 0) + 2}회"
                                  ' — 30초~1분)…')
                self.stdout.flush() if hasattr(self.stdout, 'flush') else None
                for turn in sc['plant']:
                    graph_memory._capture(uid, turn)
                for j in range(sc.get('noise', 0)):
                    graph_memory._capture(uid, NOISE_POOL[j % len(NOISE_POOL)])
                if sc.get('reflect'):   # 리플렉션 시나리오 — 심기 후 통찰 생성 (2026-07-13)
                    rr = graph_memory.reflect(uid)
                    if opts.get('debug'):
                        self.stdout.write(f"    [리플렉션] {rr}")

                # 질문을 message로 전달 — 언급 기반 직접 검색(벡터·키워드)까지 평가 대상 (2026-07-13)
                recall_text = graph_memory.recall(uid, message=sc['question'])
                if opts.get('debug'):
                    self.stdout.write('    [recall]\n      ' + recall_text.replace('\n', '\n      '))
                answer = _answer(recall_text, sc['question'])

                if sc['grade'] == 'keywords':
                    ok, why = _grade_keywords(answer, sc.get('expect_any'), sc.get('forbid'))
                    if not ok:
                        # 하이브리드: 표현만 다른 정답("7월 스무 날") 구제 — LLM 재채점
                        rubric = ('기대 정보: ' + json.dumps(sc.get('expect_any'), ensure_ascii=False)
                                  + ' — 답변이 이 정보를 다른 표현으로라도 정확히 담았으면 pass, '
                                    '틀리거나 없으면 fail.')
                        ok2, why2 = _grade_llm(answer, rubric, today, sc['question'])
                        if ok2:
                            ok, why = True, '키워드 미스 → LLM 재채점 pass: ' + why
                else:
                    ok, why = _grade_llm(answer, sc['rubric'], today, sc['question'])

                results.append(dict(id=sc['id'], type=sc['type'], ok=ok,
                                    question=sc['question'], answer=answer,
                                    recall=recall_text, why=why))
                mark = 'PASS' if ok else 'FAIL'
                self.stdout.write(f"[{mark}] {sc['id']} ({sc['type']}) — {sc['question']}")
                self.stdout.write(f"       답: {answer[:90]}")
                if not ok:
                    self.stdout.write(f"       사유: {why}")
            except Exception as e:
                # 타임아웃 등 실행 오류 — 해당 시나리오만 FAIL 처리하고 계속 진행
                results.append(dict(id=sc['id'], type=sc['type'], ok=False,
                                    question=sc['question'], answer='(실행 오류)',
                                    recall='', why=f'실행 오류: {str(e)[:120]}'))
                self.stdout.write(f"[ERR ] {sc['id']} — {str(e)[:100]}")
            finally:
                _wipe(uid)

          # ── 회차 집계 ──
          by_type = {}
          for r in results:
              by_type.setdefault(r['type'], []).append(r['ok'])
          all_totals.append(sum(r['ok'] for r in results))
          all_by_type.append(by_type)
        self.stdout.write('\n===== 결과 =====')
        label = dict(fact='사실 회상', supersede='모순 처리(supersede)',
                     forget='잊어줘 준수', trap='환각 함정 방어', combo='조합·D-day',
                     para='패러프레이즈(의미 검색)', reflect='리플렉션(통찰)')
        n_sc = len(scenarios)
        for t in label:
            per_run = [sum(bt.get(t, [])) for bt in all_by_type if t in bt]
            if not per_run:
                continue
            denom = len(all_by_type[0].get(t, []))
            if n_runs > 1:
                self.stdout.write(f'{label[t]:20s}: 평균 {sum(per_run)/len(per_run):.1f}/{denom} '
                                  f'(범위 {min(per_run)}~{max(per_run)})')
            else:
                self.stdout.write(f'{label[t]:20s}: {per_run[0]}/{denom}')
        if n_runs > 1:
            avg = sum(all_totals) / len(all_totals)
            self.stdout.write(f'{"전체":20s}: 평균 {avg:.1f}/{n_sc} ({100.0*avg/n_sc:.0f}%) '
                              f'— 범위 {min(all_totals)}~{max(all_totals)} ({n_runs}회)')
        else:
            total = all_totals[0]
            self.stdout.write(f'{"전체":20s}: {total}/{n_sc} ({100.0*total/n_sc:.0f}%)')
        trap_runs = [bt.get('trap', []) for bt in all_by_type]
        if trap_runs and trap_runs[0]:
            fails = [len(tr) - sum(tr) for tr in trap_runs]
            rate = 100.0 * sum(fails) / (len(trap_runs[0]) * len(trap_runs))
            self.stdout.write(f'환각률: {rate:.0f}% (함정 중 지어낸 비율, {n_runs}회 통산 — 낮을수록 좋음)')

        out = 'memory_eval_results.json'
        summary = (f'{all_totals[0]}/{n_sc}' if n_runs == 1
                   else f'평균 {sum(all_totals)/len(all_totals):.1f}/{n_sc} '
                        f'(범위 {min(all_totals)}~{max(all_totals)}, {n_runs}회)')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(dict(today=today, runs=n_runs, total=summary,
                           per_run_totals=all_totals,
                           results=results), f, ensure_ascii=False, indent=1)   # results = 마지막 회차 상세
        self.stdout.write(f'\n상세 결과 저장: app/backend/{out}')

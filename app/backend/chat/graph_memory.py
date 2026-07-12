# -*- coding: utf-8 -*-
"""GraphDB 장기 기억 (Neo4j) — user_memory 텍스트 요약과 '병행'하는 구조화 기억.

대화에서 사건·인물·감정·취향을 추출해 사용자 중심 그래프로 저장하고,
회상 시 관련 서브그래프를 텍스트로 꺼내 컨텍스트에 주입한다.

안전장치(중요):
- NEO4J_URI 미설정 또는 연결 실패 시 자동 비활성(no-op) → 기존 챗봇에 영향 없음.
- 모든 작업은 예외를 삼켜 대화 흐름을 막지 않는다(비동기 스레드).
- 시크릿 모드·비로그인은 호출부에서 스킵.

환경변수: NEO4J_URI(예: bolt://localhost:7687) · NEO4J_USER · NEO4J_PASSWORD
"""
import datetime
import json
import os
import re
import threading

_driver = None
_driver_tried = False
_lock = threading.Lock()


def _today_iso() -> str:
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d')


def _dday(date_str: str, today: str) -> str:
    """'2026-07-18' → 'D-6' (당일 'D-DAY'). 과거·형식 오류는 ''."""
    try:
        n = (datetime.date.fromisoformat(date_str) - datetime.date.fromisoformat(today)).days
        return '' if n < 0 else ('D-DAY' if n == 0 else f'D-{n}')
    except Exception:
        return ''


def _today_kst() -> str:
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d (%a)')


def _get_driver():
    """Neo4j 드라이버(최초 1회 연결). 미설정/실패 시 None → 비활성."""
    global _driver, _driver_tried
    if _driver_tried:
        return _driver
    with _lock:
        if _driver_tried:
            return _driver
        _driver_tried = True
        uri = os.environ.get('NEO4J_URI', '').strip()
        if not uri:
            return None
        try:
            from neo4j import GraphDatabase
            user = os.environ.get('NEO4J_USER', 'neo4j')
            pwd = os.environ.get('NEO4J_PASSWORD', '')
            drv = GraphDatabase.driver(uri, auth=(user, pwd))
            drv.verify_connectivity()
            _driver = drv
            print('[graph_memory] Neo4j 연결됨')
        except Exception as e:
            print(f'[graph_memory] Neo4j 비활성({e})')
            _driver = None
        return _driver


def is_enabled() -> bool:
    return _get_driver() is not None


# ── 추출 (LLM → 구조화 JSON) ─────────────────────────────────

def _extract(message: str):
    """대화 한 줄에서 사건·인물·취향을 구조화 추출. 실패 시 None."""
    from ai.agents.llm import get_llm
    resp = get_llm(temperature=0, max_tokens=300).invoke([
        ('system',
         "사용자 메시지에서 '기억할 가치가 있는' 사건·인물·취향을 뽑아 JSON으로만 출력하라.\n"
         f"- 날짜 표현(내일, 다음주 화요일 등)은 오늘 {_today_kst()} 기준 실제 날짜(YYYY-MM-DD)로 변환.\n"
         "- 사용자가 직접 말한 사실만. 추측 금지. 없으면 빈 배열.\n"
         "- 일회성 스몰토크(날씨·메뉴), 단순 감탄·맞장구는 제외.\n"
         "- 관계의 끝(이별·절교·퇴사 등)이나 일정 취소를 말하면 expired에 기록하라. "
         "예: '민수랑 헤어졌어' → expired에 민수(person) + events에 이별 사건. "
         "'여행 취소됐어' → expired에 여행(event).\n"
         "- 사용자가 '잊어줘/기억하지 마/그 얘기 지워줘'라고 요청하면 그 대상을 expired에 기록하라 "
         "(kind: person|event|preference, reason: '사용자 요청'). 잊어달라는 요청 자체는 events로 저장하지 마라.\n"
         "형식(없는 키는 생략 가능, JSON 외 다른 말 금지):\n"
         '{"events":[{"name":"면접","date":"2026-07-13","emotion":"불안","people":["엄마"]}],'
         '"people":[{"name":"엄마","relation":"가족"}],"preferences":["드라마"],'
         '"expired":[{"kind":"person","name":"민수","reason":"이별"}]}'),
        ('user', message),
    ])
    raw = resp.content.strip()
    if raw.startswith('```'):
        raw = raw.strip('`')
        if raw.lower().startswith('json'):
            raw = raw[4:].strip()
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


# ── 저장 (Cypher MERGE) ──────────────────────────────────────

def _norm_key(s: str) -> str:
    """dedup 1차 — 표기 차이만 다른 중복 차단 (2026-07-12).
    공백 제거·소문자화·끝 문장부호 제거: '화나는 일'/'화나는일', 'Colab'/'colab' → 같은 키.
    노드는 key(정규화)로 MERGE하고 name(원 표기)은 표시용으로 보존한다.
    의미 유사 병합(임베딩)은 2차 — 야간 배치에서 처리 예정."""
    s = (s or '').strip().lower()
    s = re.sub(r'[.,!?~…]+$', '', s)
    s = re.sub(r'\s+', '', s)
    return s


# 감정 가중 응고화 (2026-07-12) — 감정이 실린 턴의 기억일수록 강하게 남는다.
# 인지과학의 감정 응고화(emotional consolidation) 원리: 부정 감정(슬픔·분노)이 가장 강하게,
# 기쁨은 중간, 일상은 기본. 회상 정렬의 동순위 타이브레이커로 사용.
_SALIENCE = {'sadness': 1.5, 'anger': 1.4, 'joy': 1.2}


def _store(tx, uid: int, data: dict, salience: float = 1.0) -> None:
    tx.run('MERGE (u:User {uid:$uid})', uid=uid)
    for ev in (data.get('events') or []):
        name = (ev.get('name') or '').strip()
        key = _norm_key(name)
        if not key:
            continue
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (e:Event {uid:$uid, key:$key}) '
            'ON CREATE SET e.name = $name '
            'SET e.date = coalesce($date, e.date) '
            'SET e.salience = CASE WHEN coalesce(e.salience, 0) < $sal '
            '                 THEN $sal ELSE e.salience END '
            'MERGE (u)-[:HAS_EVENT]->(e)',
            uid=uid, key=key, name=name, date=ev.get('date'), sal=salience)
        emo = (ev.get('emotion') or '').strip()
        if emo:
            tx.run(
                'MATCH (e:Event {uid:$uid, key:$key}) '
                'MERGE (m:Emotion {uid:$uid, type:$emo}) '
                'MERGE (e)-[:FELT]->(m)',
                uid=uid, key=key, emo=emo)
        for pn in (ev.get('people') or []):
            pn = (pn or '').strip()
            pkey = _norm_key(pn)
            if not pkey:
                continue
            tx.run(
                'MATCH (u:User {uid:$uid}), (e:Event {uid:$uid, key:$key}) '
                'MERGE (p:Person {uid:$uid, key:$pkey}) '
                'ON CREATE SET p.name = $pn '
                'MERGE (e)-[:INVOLVES]->(p) '
                'MERGE (u)-[:KNOWS]->(p)',
                uid=uid, key=key, pkey=pkey, pn=pn)
    for pp in (data.get('people') or []):
        pn = (pp.get('name') or '').strip() if isinstance(pp, dict) else str(pp).strip()
        pkey = _norm_key(pn)
        if not pkey:
            continue
        rel = pp.get('relation') if isinstance(pp, dict) else None
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (p:Person {uid:$uid, key:$pkey}) '
            'ON CREATE SET p.name = $pn '
            'SET p.relation = coalesce($rel, p.relation) '
            'MERGE (u)-[:KNOWS]->(p)',
            uid=uid, pkey=pkey, pn=pn, rel=rel)
    for pr in (data.get('preferences') or []):
        pr = pr.get('name') if isinstance(pr, dict) else pr
        pr = (pr or '').strip() if isinstance(pr, str) else ''
        fkey = _norm_key(pr)
        if not fkey:
            continue
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (f:Preference {uid:$uid, key:$fkey}) '
            'ON CREATE SET f.name = $pr '
            'MERGE (u)-[:PREFERS]->(f)',
            uid=uid, fkey=fkey, pr=pr)
    # supersede (2026-07-12, Zep식 시간 유효성): 끝난 관계·취소된 일정은 삭제 대신 만료 도장.
    # 노드·역사는 남되 '현재 사실' 자격만 잃는다 → 회상에서 제외 ("헤어진 애인 안부 묻기" 방지)
    # ★반드시 저장 루프 '뒤'에 실행 — 같은 턴의 사건(이별)이 인물을 재생성해도 도장이 이긴다
    today = _today_iso()
    for ex in (data.get('expired') or []):
        if not isinstance(ex, dict):
            continue
        xkey = _norm_key(ex.get('name') or '')
        if not xkey:
            continue
        kind = (ex.get('kind') or '').strip().lower()
        reason = (ex.get('reason') or '').strip() or None
        if kind == 'person':
            tx.run(
                'MATCH (u:User {uid:$uid})-[:KNOWS]->(p:Person) '
                'WHERE p.key = $xkey OR p.name = $xname '
                'SET p.valid_until = $today, p.ended_reason = coalesce($reason, p.ended_reason)',
                uid=uid, xkey=xkey, xname=(ex.get('name') or '').strip(),
                today=today, reason=reason)
        elif kind == 'event':
            tx.run(
                'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                'WHERE e.key = $xkey OR e.name CONTAINS $xname '
                'SET e.valid_until = $today, e.ended_reason = coalesce($reason, e.ended_reason)',
                uid=uid, xkey=xkey, xname=(ex.get('name') or '').strip(),
                today=today, reason=reason)
        elif kind == 'preference':
            # "잊어줘" 명령 (2026-07-12) — 잊어달라면 진짜 잊는 친구 (시크릿챗과 짝을 이루는 신뢰 장치)
            tx.run(
                'MATCH (u:User {uid:$uid})-[:PREFERS]->(f:Preference) '
                'WHERE f.key = $xkey OR f.name = $xname '
                'SET f.valid_until = $today, f.ended_reason = coalesce($reason, f.ended_reason)',
                uid=uid, xkey=xkey, xname=(ex.get('name') or '').strip(),
                today=today, reason=reason)



def _capture(uid: int, message: str, emotion: str = None) -> None:
    try:
        drv = _get_driver()
        if drv is None:
            return
        data = _extract(message)
        if not data:
            return
        if not (data.get('events') or data.get('people') or data.get('preferences')):
            return
        sal = _SALIENCE.get(emotion or '', 1.0)
        with drv.session() as s:
            s.execute_write(lambda tx: _store(tx, uid, data, salience=sal))
    except Exception as e:
        print(f'[graph_memory] 캡처 실패: {e}')


def capture_async(user_id, message: str, emotion: str = None) -> None:
    """비동기 그래프 저장 트리거. 비로그인·빈 메시지·Neo4j 미설정 시 스킵.
    emotion(그 턴의 감정 라벨)이 있으면 기억 강도(salience) 가중 — 감정 응고화."""
    if not user_id or not (message or '').strip():
        return
    if not is_enabled():
        return
    threading.Thread(target=_capture, args=(user_id, message, emotion), daemon=True).start()


# ── 회상 (서브그래프 → 텍스트) ───────────────────────────────

def recall(user_id, limit: int = 6, message: str = None) -> str:
    """사용자의 사건(감정·인물·날짜)과 취향을 그래프에서 꺼내 텍스트로. 비활성/실패 시 ''.
    message가 있으면 재강화(2026-07-12): 사용자가 '직접 언급한' 기억의 강도를 올린다
    — 떠올린 기억은 선명해진다(reconsolidation). 매 턴 수동 주입분은 강화하지 않음(부익부 고착 방지)."""
    if not user_id or not is_enabled():
        return ''
    try:
        drv = _get_driver()
        lines = []
        today = _today_iso()
        with drv.session() as s:
            # ① 다가오는 일 (선제 챙김 — "내일 면접이지?" 의 재료, 2026-07-12)
            coming = s.run(
                'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                'WHERE e.date >= $today AND e.valid_until IS NULL '
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.key AS key, e.name AS name, e.date AS date, collect(DISTINCT p.name) AS people '
                'ORDER BY e.date ASC LIMIT 3',
                uid=user_id, today=today).data()
            for c in coming:
                d = _dday(c.get('date') or '', today)
                parts = [f"{c['name']} ({c['date']}" + (f' · {d}' if d else '') + ')']
                ppl = [x for x in (c.get('people') or []) if x]
                if ppl:
                    parts.append('· 함께: ' + ', '.join(ppl))
                lines.append('- 다가오는 일: ' + ' '.join(parts))
            # ② 지난·일반 기억 (감정 강한 기억 우선)
            events = s.run(
                'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                'WHERE e.date IS NULL OR e.date < $today '
                'OPTIONAL MATCH (e)-[:FELT]->(m:Emotion) '
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.key AS key, e.name AS name, e.date AS date, '
                'coalesce(e.salience, 1.0) + 0.1 * CASE WHEN coalesce(e.recall_count, 0) > 5 '
                'THEN 5 ELSE coalesce(e.recall_count, 0) END AS sal, '   # 재강화 보정(상한 +0.5 — 고착 방지)
                'collect(DISTINCT m.type) AS emotions, collect(DISTINCT p.name) AS people '
                'ORDER BY coalesce(date, \'\') DESC, sal DESC LIMIT $limit',   # 집계 RETURN에선 반환 컬럼만 정렬 가능
                uid=user_id, today=today, limit=limit).data()
            for e in events:
                parts = [e['name']]
                if e.get('date'):
                    parts.append(f"({e['date']})")
                emos = [x for x in (e.get('emotions') or []) if x]
                if emos:
                    parts.append('· 감정: ' + ', '.join(emos))
                ppl = [x for x in (e.get('people') or []) if x]
                if ppl:
                    parts.append('· 함께: ' + ', '.join(ppl))
                lines.append('- ' + ' '.join(parts))
            # 인물(KNOWS) 회상 — 저장만 되고 회상 안 되던 구멍 보수 (2026-07-12)
            people = s.run(
                'MATCH (u:User {uid:$uid})-[:KNOWS]->(p:Person) '
                'WHERE p.valid_until IS NULL '
                'RETURN p.key AS key, p.name AS name, p.relation AS relation LIMIT 10',
                uid=user_id).data()
            names = [f"{p['name']}({p['relation']})" if p.get('relation') else p['name']
                     for p in people if p.get('name')]
            if names:
                lines.append('- 인물: ' + ', '.join(names))
            pref = s.run(
                'MATCH (u:User {uid:$uid})-[:PREFERS]->(f:Preference) '
                'WHERE f.valid_until IS NULL '
                'RETURN collect(f.name) AS names', uid=user_id).single()
            if pref and pref['names']:
                lines.append('- 취향: ' + ', '.join(pref['names']))
        # 재강화: 사용자가 이번 메시지에서 직접 언급한 기억만 (이름이 메시지에 포함될 때)
        if message:
            ev_keys = [r.get('key') for r in (coming + events)
                       if r.get('key') and r.get('name') and len(r['name']) >= 2
                       and r['name'] in message]
            pp_keys = [r.get('key') for r in people
                       if r.get('key') and r.get('name') and len(r['name']) >= 2
                       and r['name'] in message]
            if ev_keys or pp_keys:
                with drv.session() as s:
                    if ev_keys:
                        s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                              'WHERE e.key IN $keys '
                              'SET e.recall_count = coalesce(e.recall_count, 0) + 1, '
                              '    e.last_recalled = $today',
                              uid=user_id, keys=ev_keys, today=today)
                    if pp_keys:
                        s.run('MATCH (u:User {uid:$uid})-[:KNOWS]->(p:Person) '
                              'WHERE p.key IN $keys '
                              'SET p.recall_count = coalesce(p.recall_count, 0) + 1, '
                              '    p.last_recalled = $today',
                              uid=user_id, keys=pp_keys, today=today)
        return '\n'.join(lines)
    except Exception as e:
        print(f'[graph_memory] 회상 실패: {e}')
        return ''


def upcoming(user_id, days: int = 7, limit: int = 2) -> str:
    """다가오는 일정 한 줄 텍스트 — 오프너 선제 챙김용 (2026-07-12).
    예: '부산 여행 (2026-07-18 · D-6, 민수와)'. 없거나 비활성이면 ''."""
    if not user_id or not is_enabled():
        return ''
    try:
        today = _today_iso()
        drv = _get_driver()
        with drv.session() as s:
            rows = s.run(
                'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                'WHERE e.date >= $today AND e.valid_until IS NULL '
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.name AS name, e.date AS date, collect(DISTINCT p.name) AS people '
                'ORDER BY e.date ASC LIMIT $limit',
                uid=user_id, today=today, limit=limit).data()
        out = []
        for r in rows:
            d = _dday(r.get('date') or '', today)
            try:
                gap = (datetime.date.fromisoformat(r['date'])
                       - datetime.date.fromisoformat(today)).days
            except Exception:
                gap = 999
            if gap > days:
                continue
            ppl = [x for x in (r.get('people') or []) if x]
            item = f"{r['name']} ({r['date']}" + (f' · {d}' if d else '') + ')'
            if ppl:
                item += f" — {', '.join(ppl)}와"
            out.append(item)
        return ' / '.join(out)
    except Exception:
        return ''

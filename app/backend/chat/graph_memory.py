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
import threading

_driver = None
_driver_tried = False
_lock = threading.Lock()


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
         "형식(없는 키는 생략 가능, JSON 외 다른 말 금지):\n"
         '{"events":[{"name":"면접","date":"2026-07-13","emotion":"불안","people":["엄마"]}],'
         '"people":[{"name":"엄마","relation":"가족"}],"preferences":["드라마"]}'),
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

def _store(tx, uid: int, data: dict) -> None:
    tx.run('MERGE (u:User {uid:$uid})', uid=uid)
    for ev in (data.get('events') or []):
        name = (ev.get('name') or '').strip()
        if not name:
            continue
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (e:Event {uid:$uid, name:$name}) '
            'SET e.date = coalesce($date, e.date) '
            'MERGE (u)-[:HAS_EVENT]->(e)',
            uid=uid, name=name, date=ev.get('date'))
        emo = (ev.get('emotion') or '').strip()
        if emo:
            tx.run(
                'MATCH (e:Event {uid:$uid, name:$name}) '
                'MERGE (m:Emotion {uid:$uid, type:$emo}) '
                'MERGE (e)-[:FELT]->(m)',
                uid=uid, name=name, emo=emo)
        for pn in (ev.get('people') or []):
            pn = (pn or '').strip()
            if not pn:
                continue
            tx.run(
                'MATCH (u:User {uid:$uid}), (e:Event {uid:$uid, name:$name}) '
                'MERGE (p:Person {uid:$uid, name:$pn}) '
                'MERGE (e)-[:INVOLVES]->(p) '
                'MERGE (u)-[:KNOWS]->(p)',
                uid=uid, name=name, pn=pn)
    for pp in (data.get('people') or []):
        pn = (pp.get('name') or '').strip() if isinstance(pp, dict) else str(pp).strip()
        if not pn:
            continue
        rel = pp.get('relation') if isinstance(pp, dict) else None
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (p:Person {uid:$uid, name:$pn}) '
            'SET p.relation = coalesce($rel, p.relation) '
            'MERGE (u)-[:KNOWS]->(p)',
            uid=uid, pn=pn, rel=rel)
    for pr in (data.get('preferences') or []):
        pr = pr.get('name') if isinstance(pr, dict) else pr
        pr = (pr or '').strip() if isinstance(pr, str) else ''
        if not pr:
            continue
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (f:Preference {uid:$uid, name:$pr}) '
            'MERGE (u)-[:PREFERS]->(f)',
            uid=uid, pr=pr)


def _capture(uid: int, message: str) -> None:
    try:
        drv = _get_driver()
        if drv is None:
            return
        data = _extract(message)
        if not data:
            return
        if not (data.get('events') or data.get('people') or data.get('preferences')):
            return
        with drv.session() as s:
            s.execute_write(lambda tx: _store(tx, uid, data))
    except Exception as e:
        print(f'[graph_memory] 캡처 실패: {e}')


def capture_async(user_id, message: str) -> None:
    """비동기 그래프 저장 트리거. 비로그인·빈 메시지·Neo4j 미설정 시 스킵."""
    if not user_id or not (message or '').strip():
        return
    if not is_enabled():
        return
    threading.Thread(target=_capture, args=(user_id, message), daemon=True).start()


# ── 회상 (서브그래프 → 텍스트) ───────────────────────────────

def recall(user_id, limit: int = 6) -> str:
    """사용자의 사건(감정·인물·날짜)과 취향을 그래프에서 꺼내 텍스트로. 비활성/실패 시 ''."""
    if not user_id or not is_enabled():
        return ''
    try:
        drv = _get_driver()
        lines = []
        with drv.session() as s:
            events = s.run(
                'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                'OPTIONAL MATCH (e)-[:FELT]->(m:Emotion) '
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.name AS name, e.date AS date, '
                'collect(DISTINCT m.type) AS emotions, collect(DISTINCT p.name) AS people '
                'ORDER BY e.date DESC LIMIT $limit',
                uid=user_id, limit=limit).data()
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
            pref = s.run(
                'MATCH (u:User {uid:$uid})-[:PREFERS]->(f:Preference) '
                'RETURN collect(f.name) AS names', uid=user_id).single()
            if pref and pref['names']:
                lines.append('- 취향: ' + ', '.join(pref['names']))
        return '\n'.join(lines)
    except Exception as e:
        print(f'[graph_memory] 회상 실패: {e}')
        return ''

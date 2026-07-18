# -*- coding: utf-8 -*-
"""GraphDB 장기기억 v2 — Temporal Knowledge Graph (Neo4j). Zep/Graphiti 계보.

핵심 원리:
  · 사실(fact) = '시간 붙은 관계(edge)'. 모든 fact 관계는 valid_from·valid_to·created_at·episode.
  · 사실이 바뀌면 삭제하지 않고 valid_to를 찍어 무효화 → 현재(valid_to IS NULL)와 이력을 분리.
  · 엔티티(사람·장소·주제·감정)는 노드로 통합(MERGE), 여러 대화에 걸쳐 누적.
  · 원본 발화는 Episode 노드로 보존(출처 추적).
  · 감정은 학습 모델(KcELECTRA predict_emotion_full) 4확률만 사용.

제공 기능:
  recall()              — 현재 유효한 사실 회상 (valid_to IS NULL)
  open_loops()          — ⑥ 지난 미래사건(후속 없음) → "그거 어떻게 됐어?"
  relationship_changes()— ⑦ 무효화된 관계 이력 → 변화 이후 공감 / 지난 인연 오답 방지
  absence_days()        — ⑨ 마지막 대화 이후 경과일 → 오랜만 인사

안전장치: NEO4J_URI 미설정/실패 시 자동 no-op. 예외 삼킴(대화 흐름 보호).
임계값은 전부 env 설정(하드코딩 회피).
"""
import datetime
import json
import os
import re
import threading
import uuid

_driver = None
_driver_tried = False
_lock = threading.Lock()

RECALL_LIMIT = int(os.environ.get('MEM_RECALL_LIMIT', '6'))
OPENLOOP_MAX_AGE = int(os.environ.get('MEM_OPENLOOP_AGE_DAYS', '30'))   # 이보다 오래된 미해결은 안 물음
RELCHANGE_WINDOW = int(os.environ.get('MEM_RELCHANGE_DAYS', '30'))      # 최근 관계변화 조회 창
ABSENCE_MIN = int(os.environ.get('MEM_ABSENCE_DAYS', '7'))              # 오랜만 인사 임계(설정값)
_NEG_EMO = ('슬픔', '분노')


def _today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()


def _today_s():
    return _today().isoformat()


def _now():
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%dT%H:%M:%S')


def _norm(s):
    s = (s or '').strip().lower()
    s = re.sub(r'[.,!?~…]+$', '', s)
    return re.sub(r'\s+', '', s)


def _get_driver():
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
            drv = GraphDatabase.driver(
                uri, auth=(os.environ.get('NEO4J_USER', 'neo4j'),
                           os.environ.get('NEO4J_PASSWORD', '')))
            drv.verify_connectivity()
            _setup(drv)
            _driver = drv
            print('[graph_memory_v2] Neo4j(temporal KG) 연결됨')
        except Exception as e:
            print(f'[graph_memory_v2] Neo4j 비활성({e})')
            _driver = None
        return _driver


def is_enabled():
    return _get_driver() is not None


def _setup(drv):
    stmts = [
        'CREATE CONSTRAINT u_uid IF NOT EXISTS FOR (u:User) REQUIRE u.uid IS UNIQUE',
        'CREATE CONSTRAINT ep_id IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE',
        'CREATE CONSTRAINT ev_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE',
        'CREATE CONSTRAINT d_date IF NOT EXISTS FOR (d:Date) REQUIRE d.date IS UNIQUE',
        'CREATE CONSTRAINT em_type IF NOT EXISTS FOR (m:Emotion) REQUIRE m.type IS UNIQUE',
        'CREATE CONSTRAINT pl_name IF NOT EXISTS FOR (p:Place) REQUIRE p.name IS UNIQUE',
        'CREATE CONSTRAINT tp_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE',
        'CREATE INDEX ev_key IF NOT EXISTS FOR (e:Event) ON (e.uid, e.key)',
        'CREATE INDEX pr_key IF NOT EXISTS FOR (p:Person) ON (p.uid, p.key)',
    ]
    with drv.session() as s:
        for q in stmts:
            try:
                s.run(q)
            except Exception as e:
                print(f'[graph_memory_v2] 스키마 경고: {e}')


# ── 감정: 학습 모델 4확률 ──────────────────────────────────────
def _emotion_probs(text):
    try:
        from ai.emotion.emotion_model import predict_emotion_full
        _, _, probs = predict_emotion_full(text)
        return probs or {}
    except Exception:
        return {}


# ── 추출 ──────────────────────────────────────────────────────
def _extract(message):
    from ai.agents.llm import get_llm
    sys = (
        "사용자 메시지에서 기억할 사실을 JSON으로만 뽑아라.\n"
        "events(사건/일정): {name(5~15자 구체), date(YYYY-MM-DD, 다가오는 일정만, "
        f"오늘 {_today_s()} 기준. 과거는 null), place, topic(취업/건강/연애/가족/학업/돈/취미 등 한 단어), "
        "people(이름 배열), cause(이유), caused_by(원인이 같은 메시지의 다른 사건 이름이면 그 이름)}\n"
        "relations(관계): {person, relation(가족/친구/연인/직장/반려동물)}\n"
        "preferences(취향): {topic, polarity: 호|오}\n"
        "invalidations(끝난 것): {kind: relation|event|preference, name, reason} "
        "— 이별·절교·퇴사·취소·'잊어줘'.\n"
        "직접 말한 것만. 추측 금지. 빈 배열 생략 가능. JSON 외 금지.\n"
        '예: {"events":[{"name":"엄마 병원검사","date":"2026-07-22","place":"병원",'
        '"topic":"가족","people":["엄마"],"cause":"엄마가 편찮으심"}],'
        '"relations":[{"person":"엄마","relation":"가족"}]}'
    )
    try:
        resp = get_llm(temperature=0, max_tokens=450).invoke(
            [('system', sys), ('user', message)])
        raw = resp.content.strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


# 공통 temporal edge 속성 (MERGE 후 ON CREATE로 찍음)
_TSTAMP = ('ON CREATE SET r.valid_from=$now, r.valid_to=null, '
           'r.created_at=$now, r.episode=$eid ')


def _store(tx, uid, data, probs, message):
    now = _now()
    eid = 'ep_' + uuid.uuid4().hex[:12]
    tx.run('MERGE (u:User {uid:$uid})', uid=uid)
    tx.run('CREATE (ep:Episode {id:$eid, uid:$uid, text:$text, created_at:$now})',
           eid=eid, uid=uid, text=message[:1000], now=now)

    name_to_key = {}
    top_emo = max(probs, key=probs.get) if probs else None
    salience = 1.0 + max((probs.get(k, 0.0) for k in _NEG_EMO), default=0.0)

    for ev in (data.get('events') or []):
        name = (ev.get('name') or '').strip()
        key = _norm(name)
        if not key:
            continue
        name_to_key[key] = key
        tx.run(
            'MATCH (u:User {uid:$uid}), (ep:Episode {id:$eid}) '
            'MERGE (e:Event {uid:$uid, key:$key}) '
            'ON CREATE SET e.id=$evid, e.name=$name, e.created_at=$now, e.recall_count=0 '
            'SET e.cause=coalesce($cause,e.cause), e.top_emotion=coalesce($top,e.top_emotion), '
            '    e.salience=CASE WHEN coalesce(e.salience,0)<$sal THEN $sal ELSE e.salience END '
            'MERGE (ep)-[:RECORDS]->(e) '
            'MERGE (u)-[r:HAS_EVENT]->(e) ' + _TSTAMP,
            uid=uid, eid=eid, key=key, evid='ev_' + uuid.uuid4().hex[:10],
            name=name, now=now, cause=(ev.get('cause') or '').strip() or None,
            top=top_emo, sal=salience)
        # 언제/어디서/주제
        if (ev.get('date') or '').strip():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (d:Date {date:$v}) '
                   'MERGE (e)-[r:ON]->(d) ' + _TSTAMP,
                   uid=uid, key=key, v=ev['date'].strip(), now=now, eid=eid)
        if (ev.get('place') or '').strip():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (p:Place {name:$v}) '
                   'MERGE (e)-[r:AT]->(p) ' + _TSTAMP,
                   uid=uid, key=key, v=ev['place'].strip(), now=now, eid=eid)
        if (ev.get('topic') or '').strip():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (t:Topic {name:$v}) '
                   'MERGE (e)-[r:ABOUT]->(t) ' + _TSTAMP,
                   uid=uid, key=key, v=ev['topic'].strip(), now=now, eid=eid)
        # 누구
        for pn in (ev.get('people') or []):
            pk = _norm(pn)
            if not pk:
                continue
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) '
                   'MERGE (p:Person {uid:$uid,key:$pk}) ON CREATE SET p.name=$pn '
                   'MERGE (e)-[r:INVOLVES]->(p) ' + _TSTAMP,
                   uid=uid, key=key, pk=pk, pn=(pn or '').strip(), now=now, eid=eid)
        # 감정 4확률 (모델)
        for et, sc in probs.items():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (m:Emotion {type:$et}) '
                   'MERGE (e)-[r:EVOKED]->(m) '
                   'ON CREATE SET r.score=$sc, r.episode=$eid '
                   'SET r.score=$sc',
                   uid=uid, key=key, et=et, sc=float(sc), eid=eid)

    # 인과 (왜가 같은 메시지 내 다른 사건)
    for ev in (data.get('events') or []):
        cb, ek = _norm(ev.get('caused_by') or ''), _norm(ev.get('name') or '')
        if cb and ek and cb in name_to_key and ek in name_to_key and cb != ek:
            tx.run('MATCH (a:Event {uid:$uid,key:$ek}),(b:Event {uid:$uid,key:$cb}) '
                   'MERGE (a)-[:BECAUSE_OF]->(b)', uid=uid, ek=ek, cb=cb)

    # 관계 (RELATES_TO) — 시간 사실
    for rl in (data.get('relations') or []):
        pn = (rl.get('person') or '').strip()
        pk = _norm(pn)
        if not pk:
            continue
        rel = (rl.get('relation') or '').strip() or '지인'
        tx.run('MATCH (u:User {uid:$uid}) MERGE (p:Person {uid:$uid,key:$pk}) '
               'ON CREATE SET p.name=$pn '
               'MERGE (u)-[r:RELATES_TO {relation:$rel}]->(p) ' + _TSTAMP,
               uid=uid, pk=pk, pn=pn, rel=rel, now=now, eid=eid)

    # 취향 (PREFERS) — 시간 사실
    for pf in (data.get('preferences') or []):
        tp = (pf.get('topic') if isinstance(pf, dict) else pf) or ''
        tk = (tp or '').strip()
        if not tk:
            continue
        pol = (pf.get('polarity') if isinstance(pf, dict) else None) or '호'
        tx.run('MATCH (u:User {uid:$uid}) MERGE (t:Topic {name:$tk}) '
               'MERGE (u)-[r:PREFERS {polarity:$pol}]->(t) ' + _TSTAMP,
               uid=uid, tk=tk, pol=pol, now=now, eid=eid)

    # 무효화 (belief revision) — valid_to 찍기, 삭제 X
    for inv in (data.get('invalidations') or []):
        if not isinstance(inv, dict):
            continue
        ck = _norm(inv.get('name') or '')
        if not ck:
            continue
        kind = (inv.get('kind') or '').strip().lower()
        reason = (inv.get('reason') or '').strip() or None
        etype = {'relation': 'RELATES_TO', 'preference': 'PREFERS'}.get(kind, 'HAS_EVENT')
        tx.run(
            f'MATCH (u:User {{uid:$uid}})-[r:{etype}]->(n) '
            'WHERE r.valid_to IS NULL AND (n.key=$ck OR n.name CONTAINS $ck OR n.name=$ck) '
            'SET r.valid_to=$today, r.end_reason=coalesce($reason,r.end_reason)',
            uid=uid, ck=ck, today=_today_s(), reason=reason)


def _capture(uid, message):
    try:
        drv = _get_driver()
        if drv is None:
            return
        data = _extract(message)
        if not data or not any(data.get(k) for k in
                               ('events', 'relations', 'preferences', 'invalidations')):
            return
        probs = _emotion_probs(message)
        with drv.session() as s:
            s.execute_write(lambda tx: _store(tx, uid, data, probs, message))
    except Exception as e:
        print(f'[graph_memory_v2] 캡처 실패: {e}')


def capture_async(user_id, message, **_):
    if not user_id or not (message or '').strip() or not is_enabled():
        return
    threading.Thread(target=_capture, args=(user_id, message), daemon=True).start()


# ── 회상 (현재 유효한 사실 = valid_to IS NULL) ─────────────────
def recall(user_id, message=None, limit=None):
    if not user_id or not is_enabled():
        return ''
    limit = limit or RECALL_LIMIT
    try:
        drv = _get_driver()
        lines, today = [], _today_s()
        with drv.session() as s:
            # 다가오는 일 (유효한 미래 사건)
            for c in s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event)-[o:ON]->(d:Date) '
                'WHERE h.valid_to IS NULL AND o.valid_to IS NULL AND d.date>=$today '
                'OPTIONAL MATCH (e)-[iv:INVOLVES]->(p:Person) '
                'RETURN e.name AS n, d.date AS dt, collect(DISTINCT p.name) AS ppl '
                'ORDER BY d.date ASC LIMIT 3', uid=user_id, today=today).data():
                w = ' · 함께: ' + ', '.join(x for x in c['ppl'] if x) if any(c['ppl']) else ''
                lines.append(f"- 다가오는 일: {c['n']} ({c['dt']}){w}")
            # 최근 감정 강한 기억
            for e in s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL '
                'RETURN e.name AS n, e.top_emotion AS emo, e.cause AS c '
                'ORDER BY coalesce(e.salience,1.0) DESC, e.created_at DESC LIMIT $lim',
                uid=user_id, lim=limit).data():
                p = [e['n']]
                if e.get('emo'):
                    p.append(f"· 감정:{e['emo']}")
                if e.get('c'):
                    p.append(f"· 이유:{e['c']}")
                lines.append('- ' + ' '.join(p))
            # 현재 인물 (유효한 관계)
            cur = s.run(
                'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                'WHERE r.valid_to IS NULL '
                'RETURN DISTINCT p.name AS n, r.relation AS rel LIMIT 10', uid=user_id).data()
            if cur:
                lines.append('- 인물: ' + ', '.join(
                    f"{x['n']}({x['rel']})" for x in cur if x['n']))
            # 취향 (유효)
            pf = s.run('MATCH (u:User {uid:$uid})-[r:PREFERS]->(t:Topic) '
                       "WHERE r.valid_to IS NULL AND r.polarity<>'오' "
                       'RETURN collect(DISTINCT t.name) AS xs', uid=user_id).single()
            if pf and pf['xs']:
                lines.append('- 취향: ' + ', '.join(pf['xs']))
        return '\n'.join(lines)
    except Exception as e:
        print(f'[graph_memory_v2] 회상 실패: {e}')
        return ''


# ── ⑥ 미해결 추적 (open loop) ─────────────────────────────────
def open_loops(user_id):
    """지난 미래사건인데 후속 없음 → '그거 어떻게 됐어?' 재료. 물어본 건 표시(중복 방지)."""
    if not user_id or not is_enabled():
        return []
    try:
        drv = _get_driver()
        today = _today()
        cutoff = (today - datetime.timedelta(days=OPENLOOP_MAX_AGE)).isoformat()
        with drv.session() as s:
            rows = s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event)-[o:ON]->(d:Date) '
                'WHERE h.valid_to IS NULL AND o.valid_to IS NULL '
                '  AND d.date < $today AND d.date >= $cutoff '
                '  AND coalesce(e.followup_asked,false) = false '
                'RETURN e.key AS key, e.name AS name, d.date AS date '
                'ORDER BY d.date DESC LIMIT 3',
                uid=user_id, today=today.isoformat(), cutoff=cutoff).data()
        return [{'name': r['name'], 'date': r['date'], 'key': r['key']} for r in rows]
    except Exception:
        return []


def mark_followed_up(user_id, key):
    """open_loops로 물어본 사건 표시 — 다시 안 묻게."""
    if not user_id or not is_enabled():
        return
    try:
        with _get_driver().session() as s:
            s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event {key:$key}) '
                  'SET e.followup_asked=true', uid=user_id, key=key)
    except Exception:
        pass


# ── ⑦ 관계 변화 감지 ──────────────────────────────────────────
def relationship_changes(user_id, days=None):
    """최근 무효화된 관계(valid_to 찍힘) → 변화 이후 공감 + 지난 인연 오답 방지."""
    if not user_id or not is_enabled():
        return []
    days = days or RELCHANGE_WINDOW
    try:
        drv = _get_driver()
        since = (_today() - datetime.timedelta(days=days)).isoformat()
        with drv.session() as s:
            rows = s.run(
                'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                'WHERE r.valid_to IS NOT NULL AND r.valid_to >= $since '
                'RETURN p.name AS name, r.relation AS rel, r.valid_to AS ended, '
                '       r.end_reason AS reason ORDER BY r.valid_to DESC LIMIT 3',
                uid=user_id, since=since).data()
        return [{'name': r['name'], 'relation': r['rel'],
                 'ended': r['ended'], 'reason': r['reason']} for r in rows]
    except Exception:
        return []


# ── ⑨ 오랜만 인사 ─────────────────────────────────────────────
def absence_days(user_id):
    """마지막 Episode 이후 경과일. 없으면 -1. ABSENCE_MIN 이상이면 오랜만."""
    if not user_id or not is_enabled():
        return -1
    try:
        drv = _get_driver()
        with drv.session() as s:
            row = s.run('MATCH (ep:Episode {uid:$uid}) '
                        'RETURN max(ep.created_at) AS last', uid=user_id).single()
        if not row or not row['last']:
            return -1
        last = datetime.date.fromisoformat(row['last'][:10])
        return (_today() - last).days
    except Exception:
        return -1


def absence_opener(user_id):
    """오랜만(ABSENCE_MIN일↑)이면 미해결과 결합한 인사 문구, 아니면 ''."""
    gap = absence_days(user_id)
    if gap < ABSENCE_MIN:
        return ''
    loops = open_loops(user_id)
    if loops:
        return f"오랜만이야! 저번에 '{loops[0]['name']}' 얘기했었는데 어떻게 됐어?"
    return "오랜만이야, 그동안 어떻게 지냈어?"


# ── 인과 추적 (BECAUSE_OF) ─────────────────────────────────────
def root_cause(user_id, event_name):
    if not user_id or not is_enabled():
        return ''
    depth = int(os.environ.get('MEM_CAUSE_DEPTH', '5'))
    try:
        with _get_driver().session() as s:
            row = s.run(
                'MATCH (e:Event {uid:$uid}) WHERE e.name CONTAINS $name '
                f'MATCH path=(e)-[:BECAUSE_OF*1..{depth}]->(root:Event) '
                'WHERE NOT (root)-[:BECAUSE_OF]->(:Event) '
                'RETURN [n IN nodes(path)|n.name] AS chain '
                'ORDER BY length(path) DESC LIMIT 1',
                uid=user_id, name=_norm(event_name)).single()
            return ' ← '.join(row['chain']) if row and row['chain'] else ''
    except Exception:
        return ''

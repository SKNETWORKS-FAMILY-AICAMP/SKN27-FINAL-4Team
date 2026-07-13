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
         "(reason: '사용자 요청'). 잊어달라는 요청 자체는 events로 저장하지 마라.\n"
         "- expired의 kind는 반드시 영문 소문자 person, event, preference 중 하나만 사용하라. "
         "name은 원래 저장됐을 이름 그대로 짧게 (예: '민트초코', '현우', '편의점 알바').\n"
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


def _extract_expired(message: str):
    """만료 전용 추출기 (2026-07-12) — 범용 추출이 expired를 놓칠 때의 2차 안전망.
    외길 프롬프트(끝난 것만 묻기)라 범용 재시도보다 훨씬 안정적. 실패 시 []."""
    from ai.agents.llm import get_llm
    try:
        resp = get_llm(temperature=0, max_tokens=150).invoke([
            ('system',
             "사용자 메시지에서 '끝났거나 무효가 된 것'만 찾아 JSON 배열로 출력하라.\n"
             "- 관계의 끝(이별·절교·퇴사), 일정 취소, '잊어줘/기억하지 마' 요청이 대상.\n"
             "- kind는 person|event|preference 중 하나(영문 소문자), name은 대상 이름 짧게.\n"
             "- 없으면 빈 배열 []. JSON 외 다른 말 금지.\n"
             '예: [{"kind":"person","name":"민수","reason":"이별"}]'),
            ('user', message),
        ])
        raw = resp.content.strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


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

# ── 벡터 의미 검색 (2026-07-12) ──────────────────────────────
VEC_INDEX = 'memory_vec'      # Neo4j 벡터 인덱스 이름 (Event.embedding, 768, cosine)
VEC_RECALL_MIN = 0.33   # 실측 (memory_embed_bench): 무관질문 최고 0.32 < 정답 최저 0.35         # 질문↔기억 유사도 하한 — 초기값, 평가셋 스윕으로 보정 예정
VEC_DEDUP_MIN = 0.93          # 저장 시 즉시 병합 임계값 — 보수적으로 높게 (오병합 방지), 스윕 예정

# 만료 신호 힌트 — 이 패턴이 있는데 추출이 expired를 안 내면 1회 재시도 (2026-07-12 평가셋 변동성 보정)
_EXPIRY_HINT = re.compile(
    r'헤어졌|헤어져|절교|이별|그만뒀|그만둠|그만둘|퇴사|취소|깨졌|파토|잊어줘|잊어버려|기억하지\s*마|지워줘')


def _store(tx, uid: int, data: dict, salience: float = 1.0, vectors: dict = None) -> None:
    tx.run('MERGE (u:User {uid:$uid})', uid=uid)
    this_turn_keys = []   # 이번 턴에 저장한 사건 키 — 만료에서 보호 (종결 기록 생존)
    for ev in (data.get('events') or []):
        name = (ev.get('name') or '').strip()
        key = _norm_key(name)
        if not key:
            continue
        this_turn_keys.append(key)
        vec = (vectors or {}).get(name) or (vectors or {}).get((ev.get('name') or '').strip())
        tx.run(
            'MATCH (u:User {uid:$uid}) '
            'MERGE (e:Event {uid:$uid, key:$key}) '
            'ON CREATE SET e.name = $name '
            'SET e.date = coalesce($date, e.date) '
            'SET e.embedding = coalesce(e.embedding, $vec) '   # 의미 검색용 벡터 (없으면 유지)
            'SET e.salience = CASE WHEN coalesce(e.salience, 0) < $sal '
            '                 THEN $sal ELSE e.salience END '
            'MERGE (u)-[:HAS_EVENT]->(e)',
            uid=uid, key=key, name=name, date=ev.get('date'), sal=salience, vec=vec)
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
    # 캐스케이드(평가셋 S03 보정): 추출 LLM이 kind를 잘못 찍어도(알바→person)
    # 선언 kind에서 도장 0건이면 나머지 종류를 순차 시도한다.
    def _expire_one(kind_, xkey_, xname_, reason_):
        q = {
            'person': ('MATCH (u:User {uid:$uid})-[:KNOWS]->(p:Person) '
                       'WHERE p.key = $xkey OR p.name = $xname '
                       'OR (size($xkey) >= 2 AND (p.key CONTAINS $xkey OR $xkey CONTAINS p.key)) '
                       'OR any(t IN $tokens WHERE p.key CONTAINS t OR p.name CONTAINS t) '
                       'SET p.valid_until = $today, '
                       '    p.ended_reason = coalesce($reason, p.ended_reason)'),
            'event': ('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                      'WHERE NOT e.key IN $keep '   # 이번 턴 사건(이별·취소 등 종결 기록) 보호 — 과잉 만료 방지
                      'AND (e.key = $xkey OR e.name CONTAINS $xname '
                      'OR (size($xkey) >= 2 AND (e.key CONTAINS $xkey OR $xkey CONTAINS e.key)) '
                      'OR any(t IN $tokens WHERE e.key CONTAINS t OR e.name CONTAINS t)) '
                      'SET e.valid_until = $today, '
                      '    e.ended_reason = coalesce($reason, e.ended_reason)'),
            'preference': ('MATCH (u:User {uid:$uid})-[:PREFERS]->(f:Preference) '
                           'WHERE f.key = $xkey OR f.name = $xname '
                           'OR (size($xkey) >= 2 AND (f.key CONTAINS $xkey OR $xkey CONTAINS f.key)) '
                       'OR any(t IN $tokens WHERE f.key CONTAINS t OR f.name CONTAINS t) '
                           'SET f.valid_until = $today, '
                           '    f.ended_reason = coalesce($reason, f.ended_reason)'),
        }[kind_]
        tokens = [t for t in re.split(r'\s+', xname_) if len(t) >= 2]
        res = tx.run(q, uid=uid, xkey=xkey_, xname=xname_, tokens=tokens,
                     keep=this_turn_keys, today=today, reason=reason_)
        try:
            return res.consume().counters.properties_set
        except Exception:
            return 1   # 카운터 미지원(테스트 목 등) — 도장 성공 간주(캐스케이드 중단)

    today = _today_iso()
    for ex in (data.get('expired') or []):
        if not isinstance(ex, dict):
            continue
        xkey = _norm_key(ex.get('name') or '')
        if not xkey:
            continue
        xname = (ex.get('name') or '').strip()
        reason = (ex.get('reason') or '').strip() or None
        # 잊어줘 vs supersede 의미 구분 (2026-07-12 평가셋 F02 원인):
        #  · 잊어줘("사용자 요청") = 그 대상의 흔적을 인물·사건·취향 '전부' 만료 (중단 없음)
        #  · supersede(이별·취소 등) = 첫 매칭 종류에서 중단 (종결 사건 등 맥락 보존)
        is_forget = bool(reason and re.search(r'요청|잊', reason))
        if is_forget:
            reason = '사용자 요청'   # 정규화 — recall의 '지난 인연' 제외 필터가 확실히 걸리도록
        declared = (ex.get('kind') or '').strip().lower()
        order = [declared] if declared in ('person', 'event', 'preference') else []
        order += [k for k in ('person', 'event', 'preference') if k not in order]
        for k in order:
            stamped = _expire_one(k, xkey, xname, reason)
            if stamped and not is_forget:
                break   # supersede만 중단 — 잊어줘는 전 종류 계속



def _capture(uid: int, message: str, emotion: str = None) -> None:
    try:
        drv = _get_driver()
        if drv is None:
            return
        data = _extract(message)
        # 만료 신호가 뚜렷한데 범용 추출이 expired를 놓쳤으면 전용 추출기로 보강 (2026-07-12)
        # — 같은 프롬프트 재굴림(변동성 반복)이 아니라 외길 프롬프트로 묻고, 기존 추출에 '병합'한다
        if _EXPIRY_HINT.search(message) and not (data or {}).get('expired'):
            exp = _extract_expired(message)
            if exp:
                data = data or {}
                data['expired'] = exp
        if not data:
            return
        if not (data.get('events') or data.get('people')
                or data.get('preferences') or data.get('expired')):
            return   # expired 포함 — '잊어줘'만 있는 메시지도 저장돼야 함 (평가셋 F01 원인, 2026-07-12)
        sal = _SALIENCE.get(emotion or '', 1.0)
        # 벡터 준비 (모델 없으면 전부 None → 기존 동작 그대로)
        from chat import embedder
        vectors = {}
        for ev in (data.get('events') or []):
            name = (ev.get('name') or '').strip()
            if name:
                vectors[name] = embedder.embed(name)
        with drv.session() as s:
            # dedup 2차 (즉시): 새 사건이 기존 사건과 의미상 같으면(코사인 ≥ VEC_DEDUP_MIN)
            # 새로 만들지 않고 기존 노드로 병합 리다이렉트 — "발표 잘함" ≈ "발표 대박"
            def _overlaps(a, b):
                """만료 대상 이름과 병합 후보가 같은 사건을 가리키는지 (토큰 겹침)"""
                na, nb = _norm_key(a), _norm_key(b)
                if not na or not nb:
                    return False
                if na in nb or nb in na:
                    return True
                ta = {t for t in re.split(r'\s+', a.strip()) if len(t) >= 2}
                tb = {t for t in re.split(r'\s+', b.strip()) if len(t) >= 2}
                return bool(ta & tb)

            expired_names = [(e.get('name') or '').strip()
                             for e in (data.get('expired') or []) if e.get('name')]
            for ev in (data.get('events') or []):
                name = (ev.get('name') or '').strip()
                vec = vectors.get(name)
                if not vec:
                    continue
                # 종결 기록은 병합 금지 (S04 회귀, 2026-07-13): "영화 약속 취소"가
                # "영화 보기"로 병합되면 종결 정보가 소실되고, 원본이 이번 턴
                # keep 목록에 들어가 만료 도장까지 차단됨. 만료 신호가 있는
                # 이벤트는 독립 노드로 남긴다.
                if _EXPIRY_HINT.search(name):
                    continue
                try:
                    hit = s.run(
                        f'CALL db.index.vector.queryNodes("{VEC_INDEX}", 3, $vec) '
                        'YIELD node, score '
                        'WHERE node.uid = $uid AND score >= $min '
                        'AND node.valid_until IS NULL AND node.name <> $name '
                        'RETURN node.name AS name, score LIMIT 1',
                        vec=vec, uid=uid, min=VEC_DEDUP_MIN, name=name).single()
                    if hit and any(_overlaps(x, hit['name']) for x in expired_names):
                        continue   # 병합 후보가 이번 턴 만료 대상 — 합치면 만료가 막힘
                    if hit:
                        print(f"[graph_memory] dedup2: '{name}' ≈ '{hit['name']}' "
                              f"({hit['score']:.2f}) → 병합")
                        ev['name'] = hit['name']   # MERGE가 기존 노드를 향하게
                except Exception:
                    pass   # 인덱스 미생성 등 — 병합 없이 진행
            s.execute_write(lambda tx: _store(tx, uid, data, salience=sal, vectors=vectors))
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
                'WHERE (e.date IS NULL OR e.date < $today) AND e.valid_until IS NULL '   # 만료 필터 누락 봉합 — F03 원인 (2026-07-12)
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
            # ③ 언급 기반 직접 검색 (2026-07-12) — "너 그거 기억나?" 커버.
            #    회상 창(상위 N개) 밖으로 밀린 옛 기억도, 사용자가 이름을 부르면
            #    창과 무관하게 그래프에서 직접 찾아온다. 만료된 기억은 제외(잊은 건 잊은 것).
            if message and len(message.strip()) >= 4:
                msgnorm = _norm_key(message)
                # 중복 방지는 key+name 이중으로 — 옛 노드(key=null)끼리 null==null 오판 방지 (실측 버그)
                seen_keys = {r.get('key') for r in (coming + events) if r.get('key')}
                seen_names = {r.get('name') for r in (coming + events) if r.get('name')}
                # ③-a 의미 검색 (2026-07-12): 질문을 벡터로 바꿔 뜻이 가까운 기억을 찾는다
                #     "회사 옮기려던 거 기억나?" ≈ "이직 고민" — 단어가 안 겹쳐도 소환
                asked = []
                try:
                    from chat import embedder
                    qvec = embedder.embed(message)
                    if qvec:
                        asked = s.run(
                            f'CALL db.index.vector.queryNodes("{VEC_INDEX}", 8, $vec) '
                            'YIELD node, score '
                            'WHERE node.uid = $uid AND node.valid_until IS NULL '
                            'AND score >= $min '
                            'OPTIONAL MATCH (node)-[:FELT]->(m:Emotion) '
                            'RETURN node.key AS key, node.name AS name, node.date AS date, '
                            'collect(DISTINCT m.type) AS emotions, score '
                            'ORDER BY score DESC LIMIT 4',
                            vec=qvec, uid=user_id, min=VEC_RECALL_MIN).data()
                except Exception:
                    asked = []   # 모델·인덱스 미준비 → 키워드 폴백
                # ③-b 키워드 폴백: 임베딩이 못 찾았을 때 문자열 매칭으로 한 번 더
                if not asked:
                    asked = s.run(
                        'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                        'WHERE e.valid_until IS NULL AND size(e.name) >= 2 '
                        'AND ($msg CONTAINS e.name '
                        '     OR (size(e.key) >= 2 AND $msgnorm CONTAINS e.key) '
                        '     OR any(t IN split(e.name, \' \') '
                        '            WHERE size(t) >= 2 AND $msg CONTAINS t)) '
                        'OPTIONAL MATCH (e)-[:FELT]->(m:Emotion) '
                        'RETURN e.key AS key, e.name AS name, e.date AS date, '
                        'collect(DISTINCT m.type) AS emotions LIMIT 4',
                        uid=user_id, msg=message, msgnorm=msgnorm).data()
                for r in asked:
                    if (r.get('key') and r['key'] in seen_keys) \
                            or (r.get('name') and r['name'] in seen_names):
                        continue   # 이미 회상 창에 있는 건 중복 방지
                    parts = [r['name']]
                    if r.get('date'):
                        parts.append(f"({r['date']})")
                    emos = [x for x in (r.get('emotions') or []) if x]
                    if emos:
                        parts.append('· 감정: ' + ', '.join(emos))
                    lines.append('- (방금 물어본 기억) ' + ' '.join(parts))
                    events.append(r)   # 재강화 매칭 범위에 포함 — 꺼낸 기억은 선명해진다

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
            # 종료된 관계는 '과거'로 명시 — "지금 남자친구 누구야?"에 헤어진 사람을 현재로 답하는 것 방지 (2026-07-12)
            # 잊어달라고 한 인물(reason='사용자 요청')은 '지난 인연'에도 안 보여줌 — 완전 배제 (2026-07-12)
            # supersede(이별·절교 등)만 과거로 표시: 헤어진 사실은 위로 맥락에 필요하지만, 잊어달란 건 잊어야 함
            past = s.run(
                'MATCH (u:User {uid:$uid})-[:KNOWS]->(p:Person) '
                'WHERE p.valid_until IS NOT NULL '
                "AND coalesce(p.ended_reason, '') <> '사용자 요청' "
                'RETURN p.name AS name, p.relation AS relation, p.ended_reason AS reason LIMIT 5',
                uid=user_id).data()
            # 축약 태그 대신 완전한 문장 단언 — 소형 LLM이 '두 사람'으로 오독하던 문제 보정 (2026-07-12)
            for p in past:
                if not p.get('name'):
                    continue
                rel = p.get('relation') or '인연'
                why = f" ({p['reason']})" if p.get('reason') else ''
                lines.append(f"- ★{p['name']}은(는) 이제 {rel}이 아님{why} — "
                             f"위 기억에 {p['name']}이(가) 나와도 전부 지난 일임. 현재 관계 아님")
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

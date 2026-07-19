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
            _ensure_vector_index(drv)   # 운영 자동화: 첫 연결 때 인덱스 보장 (멱등)
            _driver = drv
            print('[graph_memory] Neo4j 연결됨')
        except Exception as e:
            print(f'[graph_memory] Neo4j 비활성({e})')
            _driver = None
        return _driver


def _ensure_vector_index(drv):
    """벡터 인덱스 자동 생성 (2026-07-13) — 수동 init 없이도 운영 배포가 안전하게.

    첫 연결 시 1회 실행, CREATE ... IF NOT EXISTS라 멱등. 신규 환경(운영 포함)은
    이것만으로 의미 검색이 켜짐 — 저장 시 임베딩은 자동 부착되므로 백필이 필요한
    건 "임베딩 도입 이전의 옛 데이터"가 있는 개발 DB뿐 (그때만 memory_vector_init).
    실패해도 무해: 벡터 질의가 키워드 폴백으로 동작."""
    try:
        from chat import embedder
        with drv.session() as s:
            s.run(
                f'CREATE VECTOR INDEX {VEC_INDEX} IF NOT EXISTS '
                'FOR (e:Event) ON (e.embedding) '
                'OPTIONS {indexConfig: {`vector.dimensions`: $dim, '
                '`vector.similarity_function`: "cosine"}}', dim=embedder.EMBED_DIM)
    except Exception as e:
        print(f'[graph_memory] 벡터 인덱스 자동 생성 실패(키워드 폴백 동작): {e}')


def is_enabled() -> bool:
    return _get_driver() is not None


# ── 추출 (LLM → 구조화 JSON) ─────────────────────────────────

def _extract(message: str):
    """대화 한 줄에서 사건·인물·취향을 구조화 추출. 실패 시 None."""
    from ai.agents.llm import get_llm
    resp = get_llm(temperature=0, max_tokens=300).invoke([
        ('system',
         "사용자 메시지에서 '기억할 가치가 있는' 것을 뽑아 JSON으로만 출력하라.\n"
         "[반드시 기록 — 최우선 규칙. 아래 항목은 일상처럼 보여도 기록한다]\n"
         "- 계획·약속, 사건(과거의 일 포함), 관계·이름 소개(가족·친구·반려동물), 취향, 구매.\n"
         "- ★지속 고민·스트레스·상태도 사건으로 기록★ ('요즘 이직할까 고민이 많아'→'이직 고민', "
         "'야근 3일 연속이야'→'연속 야근', '발표 준비 때문에 스트레스야'→'발표 준비 스트레스'). "
         "마음 상태를 말하는 발화는 잡담이 아니다 — 버리지 마라.\n"
         "- ★한 메시지에 사실이 여러 개면 하나도 빼지 말고 각각 기록★ "
         "(예: '20일에 병원 가고, 갔다 와서 엄마랑 맛있는 거 먹기로 했어' → "
         "events에 '병원 방문'(date 있음) + '엄마와 외식 약속' 2개).\n"
         "- 반려동물 이름은 people에. 예: '우리집 강아지 이름은 콩이야' → "
         'people에 {"name":"콩이","relation":"반려동물(강아지)"}.\n'
         "[버릴 것 — 위 기록 대상에 해당하지 않을 때만]\n"
         "- 일회성 일상 보고(오늘 뭐 먹었다·날씨·버스 늦음)와 단순 감탄·맞장구.\n"
         "[name·date 규칙]\n"
         "- name은 맥락 있게 5~15자 ('혼남' 말고 '상사한테 혼남'). 사용자가 말한 구체적 "
         "이름 그대로 — '포항 여행'을 '여행'으로 뭉개면 다른 기억까지 잘못 만료된다.\n"
         f"- date는 다가오는 일정·사용자가 콕 집은 날짜만, 오늘 {_today_kst()} 기준 YYYY-MM-DD로 변환. "
         "과거의 일은 사건은 기록하되 date는 항상 비워라.\n"
         "[끝난 것 — expired]\n"
         "- 이별·절교·퇴사·일정 취소는 ★expired와 events 둘 다★ 기록 — expired엔 옛것(만료용), "
         "events엔 '끝났다는 사실'. 예: '민수랑 헤어졌어' → expired 민수(person) + events '민수와 이별'. "
         "'제주 여행 취소됐어' → expired '제주 여행'(event) + events '제주 여행 취소'.\n"
         "- '잊어줘/기억하지 마' 요청은 그 대상을 expired에 (reason: '사용자 요청'). "
         "잊어달라는 요청 자체는 events로 저장 금지.\n"
         "- expired의 name은 끝난 '대상'의 이름이다 — '편의점 알바'(O), "
         "'편의점 알바 그만두기'(X, 행위로 쓰지 마라). 그만둔 이유·배경으로만 언급된 "
         "사람(사장 등)을 관계 종결로 확대 해석하지 마라 — 사용자가 그 관계를 끝냈다고 "
         "직접 말한 대상만 expired에 넣는다.\n"
         "- expired의 kind는 영문 소문자 person|event|preference 중 하나.\n"
         "- 사용자가 직접 말한 사실만. 추측 금지. 없으면 빈 배열.\n"
         "형식(없는 키는 생략 가능, JSON 외 다른 말 금지):\n"
         '{"events":[{"name":"회사 면접 예정","date":"2026-07-20","emotion":"불안","people":["엄마"]}],'
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
             "- kind는 person|event|preference 중 하나(영문 소문자), name은 사용자가 말한 "
             "구체적 이름 그대로 ('포항 여행'을 '여행'으로 뭉개지 마라).\n"
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
EXPIRE_VEC_MIN = 0.60         # 만료 벡터 폴백 (memory_expire_bench 실측): 무관 최고 0.42 대비
                              # 오폭 여유 0.18의 보수 운용 — 확실할 때만 만료, 미스는 현상 유지
_CLOSURE_NAME = re.compile(r'취소|그만두|그만둠|그만뒀|이별|절교|퇴사|무산|파토|종료|깨짐|끝남')
# '그만두' 어간 추가 (2026-07-14, S03 부산물): 추출기가 '그만두기'로 내면 둠/뒀와 부분
# 매칭이 안 돼 이중 접미('그만두기 그만둠')가 생겼음. TAIL엔 미추가 — '다음 달에 알바
# 그만두기로 했어' 같은 미래 계획을 다가오는 일에서 오폭 제외하지 않기 위함.
# 끝단 앵커판 (2026-07-14 감사 P1-1): '다가오는 일' 제외·'끝난 일' 태깅은 이름이 종결어로
# ★끝날 때만★ — '퇴사 면담 예정'/'프로젝트 종료 발표회' 같은 정당한 미래 일정 오폭 방지.
# (합성 종결 기록은 구조상 항상 '… 취소/이별'로 끝난다)
_CLOSURE_TAIL = re.compile(r'(취소|그만둠|그만뒀|이별|절교|퇴사|무산|파토|종료|깨짐|끝남)\s*$')

# (리플렉션 완전 은퇴 2026-07-19 — reflect()·Insight 채널·REFLECT_* 다이얼 삭제.
#  '요즘 흐름'은 최근 N턴 원문 + 기억 나열로 즉석 해석 — R01·R02가 이 경로로 통과)


# 만료 신호 힌트 — 이 패턴이 있는데 추출이 expired를 안 내면 1회 재시도 (2026-07-12 평가셋 변동성 보정)
_EXPIRY_HINT = re.compile(
    r'헤어졌|헤어져|절교|이별|그만뒀|그만둠|그만둘|퇴사|취소|깨졌|파토|잊어줘|잊어버려|기억하지\s*마|지워줘')


def _store(tx, uid: int, data: dict, salience: float = 1.0, vectors: dict = None,
           expired_vectors: dict = None, emotion_probs: dict = None) -> None:
    tx.run('MERGE (u:User {uid:$uid})', uid=uid)
    # 감정: 학습 모델(KcELECTRA)의 4감정 확률을 그래프 감정으로 통일 (LLM 자유형 대신).
    # top_emo = 대표 감정(argmax) — 회상 시 한 개만 빠르게 읽도록 이벤트에 비정규화.
    top_emo = max(emotion_probs, key=emotion_probs.get) if emotion_probs else None
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
            # 부활 (2026-07-14): 취소했던 일정을 같은 이름+미래 날짜로 다시 심으면 만료 해제.
            # 미래 날짜 조건 덕에 "취소된 거 아쉽다" 같은 회고(날짜 없음)로는 부활하지 않는다.
            'SET e.valid_until = CASE WHEN $date IS NOT NULL AND $date >= $today '
            '    THEN null ELSE e.valid_until END '
            'SET e.ended_reason = CASE WHEN $date IS NOT NULL AND $date >= $today '
            '    THEN null ELSE e.ended_reason END '
            'SET e.embedding = coalesce(e.embedding, $vec) '   # 의미 검색용 벡터 (없으면 유지)
            'SET e.salience = CASE WHEN coalesce(e.salience, 0) < $sal '
            '                 THEN $sal ELSE e.salience END '
            'SET e.top_emotion = coalesce($top_emo, e.top_emotion) '   # 대표 감정 비정규화
            'MERGE (u)-[:HAS_EVENT]->(e)',
            uid=uid, key=key, name=name, date=(ev.get('date') or '').strip() or None,
            today=_today_iso(), sal=salience, vec=vec, top_emo=top_emo)
        # 감정 = 학습 모델(KcELECTRA) 4감정 확률만 점수째로 (기쁨·슬픔·분노·일반).
        # 모델이 확률을 못 주면 감정은 저장하지 않는다 (LLM 폴백 없음 — 감정 소스는 모델 하나).
        for etype, escore in (emotion_probs or {}).items():
            tx.run(
                'MATCH (e:Event {uid:$uid, key:$key}) '
                'MERGE (m:Emotion {uid:$uid, type:$etype}) '
                'MERGE (e)-[r:FELT]->(m) '
                'SET r.score = $escore',
                uid=uid, key=key, etype=etype, escore=float(escore))
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
                       'OR (size($tokens) > 0 AND all(t IN $tokens WHERE p.key CONTAINS t OR p.name CONTAINS t)) '
                       'SET p.valid_until = $today, '
                       '    p.ended_reason = coalesce($reason, p.ended_reason)'),
            'event': ('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                      'WHERE NOT e.key IN $keep '   # 이번 턴 사건(이별·취소 등 종결 기록) 보호 — 과잉 만료 방지
                      'AND (e.key = $xkey OR e.name CONTAINS $xname '
                      'OR (size($xkey) >= 2 AND (e.key CONTAINS $xkey OR $xkey CONTAINS e.key)) '
                      'OR (size($tokens) > 0 AND all(t IN $tokens WHERE e.key CONTAINS t OR e.name CONTAINS t))) '
                      'SET e.valid_until = $today, '
                      '    e.ended_reason = coalesce($reason, e.ended_reason)'),
            'preference': ('MATCH (u:User {uid:$uid})-[:PREFERS]->(f:Preference) '
                           'WHERE f.key = $xkey OR f.name = $xname '
                           'OR (size($xkey) >= 2 AND (f.key CONTAINS $xkey OR $xkey CONTAINS f.key)) '
                       'OR (size($tokens) > 0 AND all(t IN $tokens WHERE f.key CONTAINS t OR f.name CONTAINS t)) '
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
        total_stamped = 0
        for k in order:
            stamped = _expire_one(k, xkey, xname, reason)
            total_stamped += stamped or 0
            if stamped and not is_forget:
                break   # supersede만 중단 — 잊어줘는 전 종류 계속
        # 4단(2026-07-13): 문자열 3단 전멸 시 벡터 폴백 — "운동 레슨"→"헬스 PT 등록".
        # EXPIRE_VEC_MIN=0.60 보수 운용 (벤치: 단일 임계값 분리 불가 → 고문턱만 채택,
        # 무관 최고 0.42와 여유 0.18). 미스 비용=현상 유지, 오폭 비용=기억 실종의 비대칭.
        vec = (expired_vectors or {}).get(ex.get('name') or '')
        if total_stamped == 0 and vec:
            try:
                hit = tx.run(
                    f'CALL db.index.vector.queryNodes("{VEC_INDEX}", 4, $vec) '
                    'YIELD node, score '
                    'WHERE node.uid = $uid AND node.valid_until IS NULL '
                    'AND NOT node.key IN $keep '   # 이번 턴 종결 기록이 1등으로 잡히는 자폭 방지
                    'AND score >= $min '
                    'RETURN node.key AS key, node.name AS name, score '
                    'ORDER BY score DESC LIMIT 1',
                    vec=vec, uid=uid, keep=this_turn_keys, min=EXPIRE_VEC_MIN).single()
                if hit:
                    tx.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event {key:$key}) '
                           'SET e.valid_until = $today, '
                           '    e.ended_reason = coalesce($reason, e.ended_reason)',
                           uid=uid, key=hit['key'], today=today, reason=reason)
                    print(f"[graph_memory] 만료 벡터 매칭: '{ex.get('name')}' ≈ "
                          f"'{hit['name']}' ({hit['score']:.2f}) → 만료")
            except Exception:
                pass   # 인덱스 미생성 등 — 폴백 없이 현상 유지



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
        # 종결 기록 보증 (2026-07-13, S02~S04 회귀): 추출기가 expired만 내고 종결 사건을
        # 빠뜨리면 코드가 합성 — "취소됐다"는 사실 자체가 기억이어야 나중에 답할 수 있다.
        # LLM의 변덕에 빌지 않고 코드가 관용하는 원칙. 잊어줘 요청은 제외(요청 자체 무저장).
        _CLOSURE_WORD = [(r'그만뒀|그만둠|그만둘|퇴사', '그만둠'),
                         (r'취소|파토|깨졌|무산', '취소'),
                         (r'헤어졌|헤어져|이별|절교', '이별')]
        # 맹탕 파편 제거 (2026-07-14, E2E 부산·강릉 재현): 취소 발화에서 추출기가
        # "여행" 같은 일반명사 파편을 사건으로 함께 내면 ① 아래 합성 가드가
        # "이미 종결 사건을 냈다"로 오인해 스킵 ② 파편이 keep 보호로 생존해
        # 맹탕 노드가 쌓임 — 두 결함의 공통 원인. 만료 대상 이름에 통째로
        # 포함되는(진부분) 종결어 없는 사건은 버린다. ("여행" ⊂ "강릉 여행")
        _xnames = [_norm_key(ex.get('name') or '') for ex in (data.get('expired') or [])
                   if isinstance(ex, dict)]
        if _xnames and data.get('events'):
            data['events'] = [
                ev for ev in data['events']
                if not (isinstance(ev, dict)
                        and _norm_key(ev.get('name') or '')
                        and not _CLOSURE_NAME.search(ev.get('name') or '')
                        and any(x and _norm_key(ev['name']) != x
                                and _norm_key(ev['name']) in x for x in _xnames))]
        for ex in (data.get('expired') or []):
            if not isinstance(ex, dict):
                continue   # 추출기가 문자열로 낼 때 방어 — 가드가 캡처 전체를 죽이면 안 됨 (S01, 2026-07-13)
            xname = (ex.get('name') or '').strip()
            xreason = (ex.get('reason') or '').strip()
            # kind 검사 완화 (2026-07-14, E2E 속초 3연속): 추출기가 kind를 'Event'·'여행'·
            # 생략으로 내면 만료는 폴백으로 성공하는데 합성만 조용히 스킵되던 구멍.
            # person·preference로 '명시된' 것만 제외하고 나머지는 전부 사건으로 취급
            # — 만료 쪽 폴백과 같은 관용 원칙.
            xkind = (ex.get('kind') or '').strip().lower()
            if not xname or xkind in ('person', 'preference'):
                continue
            if re.search(r'요청|잊', xreason):
                continue   # 잊어줘 — 종결 기록도 남기지 않음
            nx = _norm_key(xname)
            # '이미 냈다' 인정 조건 강화 (2026-07-14, E2E 부산·강릉): 이름이 겹치는
            # 것만으론 부족 — 종결어(취소·이별 등)까지 있어야 진짜 종결 사건.
            # "여행" 같은 파편이 합성을 막던 구멍의 직접 봉인 (위 파편 필터와 2중).
            if any(nx and _norm_key(ev.get('name') or '')
                   and _CLOSURE_NAME.search(ev.get('name') or '')
                   and (nx in _norm_key(ev['name']) or _norm_key(ev['name']) in nx)
                   for ev in (data.get('events') or []) if isinstance(ev, dict)):
                continue   # 추출기가 진짜 종결 사건(종결어 포함)을 이미 냈음
            if _CLOSURE_NAME.search(xname):
                # 이름에 이미 종결어가 있으면 그대로 기록 — "그만두기 그만둠" 이중 접미 방지 (S03 부산물, 2026-07-14)
                data.setdefault('events', []).append({'name': xname})
                print(f'[graph_memory] 종결 기록 합성(이름 그대로): {xname} (kind={xkind or "없음"})')
                continue
            word = next((w for p, w in _CLOSURE_WORD if re.search(p, xreason + ' ' + message)), '종료')
            data.setdefault('events', []).append({'name': f'{xname} {word}'})
            print(f'[graph_memory] 종결 기록 합성: {xname} {word} (kind={xkind or "없음"})')
        # 감정 확률(학습 모델) — 그래프 감정·salience를 KcELECTRA 4감정으로 통일.
        # 로컬 추론이라 비용 미미. 모델 비활성이면 probs 빈 dict → 기존 salience 폴백.
        emotion_probs = {}
        try:
            from ai.emotion.emotion_model import predict_emotion_full
            _, _, emotion_probs = predict_emotion_full(message)
            emotion_probs = emotion_probs or {}
        except Exception:
            emotion_probs = {}
        # weight = 1 + 부정감정 최대 점수(슬픔·분노) — 모델 확률에서 계산 (하드코딩 _SALIENCE 대체).
        # 모델이 확률을 못 주면 기본 1.0 (감정 소스는 모델 하나).
        sal = 1.0 + max(emotion_probs.get('슬픔', 0.0), emotion_probs.get('분노', 0.0)) \
            if emotion_probs else 1.0
        # 벡터 준비 (모델 없으면 전부 None → 기존 동작 그대로)
        from chat import embedder
        vectors = {}
        for ev in (data.get('events') or []):
            name = (ev.get('name') or '').strip()
            if name:
                vectors[name] = embedder.embed(name)
        # 만료 대상 임베딩 (4단 벡터 폴백용 — Event kind만)
        expired_vectors = {}
        for ex in (data.get('expired') or []):
            if isinstance(ex, dict) and (ex.get('kind') or '') == 'event' and ex.get('name'):
                expired_vectors[ex['name']] = embedder.embed(ex['name'])
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
                             for e in (data.get('expired') or [])
                             if isinstance(e, dict) and e.get('name')]
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
            s.execute_write(lambda tx: _store(tx, uid, data, salience=sal, vectors=vectors,
                                               expired_vectors=expired_vectors,
                                               emotion_probs=emotion_probs))
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
            # (⓪ '요즘 흐름' Insight 채널 삭제 2026-07-19 — 리플렉션 은퇴로 생산자 없음)
            # ① 다가오는 일 (선제 챙김 — "내일 면접이지?" 의 재료, 2026-07-12)
            coming = s.run(
                'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                'WHERE e.date >= $today AND e.valid_until IS NULL '
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.key AS key, e.name AS name, e.date AS date, collect(DISTINCT p.name) AS people '
                'ORDER BY e.date ASC LIMIT 3',
                uid=user_id, today=today).data()
            for c in coming:
                if _CLOSURE_TAIL.search((c.get('name') or '').strip()):
                    continue   # 종결 기록(…취소/…이별)은 '다가오는 일'이 아니다 (F3 · 끝단 앵커 P1-1)
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
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.key AS key, e.name AS name, e.date AS date, '
                'coalesce(e.salience, 1.0) + 0.1 * CASE WHEN coalesce(e.recall_count, 0) > 5 '
                'THEN 5 ELSE coalesce(e.recall_count, 0) END AS sal, '   # 재강화 보정(상한 +0.5 — 고착 방지)
                'e.top_emotion AS emotion, collect(DISTINCT p.name) AS people '
                'ORDER BY coalesce(date, \'\') DESC, sal DESC LIMIT $limit',   # 집계 RETURN에선 반환 컬럼만 정렬 가능
                uid=user_id, today=today, limit=limit).data()
            for e in events:
                parts = [e['name']]
                if e.get('date'):
                    parts.append(f"({e['date']})")
                if e.get('emotion'):
                    parts.append('· 감정: ' + e['emotion'])
                ppl = [x for x in (e.get('people') or []) if x]
                if ppl:
                    parts.append('· 함께: ' + ', '.join(ppl))
                # 종결 기록은 단언 렌더링 (2026-07-13, S05): "운동 레슨 취소"를 예정으로
                # 오독해 "다음 주에 가기로 했잖아"라고 뒤집는 사고 방지 — S01 '지난 인연'
                # 문장 단언과 동일 처방. LLM 해석에 맡기지 않고 문장이 못을 박는다.
                if _CLOSURE_TAIL.search((e['name'] or '').strip()):
                    parts.append('★이미 끝난 일 — 예정 아님★')
                lines.append('- ' + ' '.join(parts))
            # ②-1 지난 일정 단언 (2026-07-13, S05): 만료된 사건을 통째로 숨기면
            # "다음 주에 뭐 있었지?"에 봇이 답할 근거가 없다 — supersede는 역사 보존이
            # 원칙이므로 최근 만료분은 '끝났다는 사실'로 단언해 준다.
            # 잊어줘(사용자 요청) 만료는 제외 — 잊어달란 건 재노출 금지 (F03 교훈).
            try:
                recent = (datetime.date.fromisoformat(today)
                          - datetime.timedelta(days=14)).isoformat()
                gone = s.run(
                    'MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event) '
                    'WHERE e.valid_until IS NOT NULL '
                    "AND coalesce(e.ended_reason, '') <> '사용자 요청' "
                    'AND e.valid_until >= $recent '
                    'RETURN e.name AS name, e.date AS date, e.ended_reason AS reason '
                    'ORDER BY e.valid_until DESC LIMIT 3',
                    uid=user_id, recent=recent).data()
                for g in gone:
                    d = f" ({g['date']})" if g.get('date') else ''
                    why = g.get('reason') or '종결'
                    lines.append(f"- ★{g['name']}{d}은(는) {why}됨 — 이제 없는 일정임★")
            except Exception:
                pass
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
                            'RETURN node.key AS key, node.name AS name, node.date AS date, '
                            'node.top_emotion AS emotion, score '
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
                        'RETURN e.key AS key, e.name AS name, e.date AS date, '
                        'e.top_emotion AS emotion LIMIT 4',
                        uid=user_id, msg=message, msgnorm=msgnorm).data()
                for r in asked:
                    if (r.get('key') and r['key'] in seen_keys) \
                            or (r.get('name') and r['name'] in seen_names):
                        continue   # 이미 회상 창에 있는 건 중복 방지
                    parts = [r['name']]
                    if r.get('date'):
                        parts.append(f"({r['date']})")
                    if r.get('emotion'):
                        parts.append('· 감정: ' + r['emotion'])
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
            if _CLOSURE_TAIL.search((r.get('name') or '').strip()):
                continue   # 종결 기록은 오프너 선제 챙김 대상 아님 (F3 · 끝단 앵커 P1-1)
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

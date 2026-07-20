# -*- coding: utf-8 -*-
"""GraphDB 장기기억 v2 — 기본 스키마 구현 (2026-07-16, 기억시스템_v2_기본스키마.svg 정본).

스키마 (기본 축):
  노드 8: User·Episode·Event(중심)·Person + 공유 Date·Place·Topic·Emotion(4종)
  관계 10: RECORDS·HAS_EVENT·ON{role}·AT·ABOUT·INVOLVES·EVOKED{score}
          ·BECAUSE_OF·RELATES_TO{relation,sentiment}·PREFERS{polarity}
  모든 fact 관계: valid_from·valid_to(null=현재)·created_at·episode (temporal)
  C1(2026-07-16): 기간 사건 — ON에 role(on|start|end), Event에 occurs_start/occurs_end
                  병행(같은 트랜잭션 기록. 의미는 관계에, 판정은 속성에).

v1 실측 자산 포팅 (재설계_확정 §8-4 회귀 방지):
  1. 종결 기록 — 이번 턴 keep 보호 + 파편 필터 + 종결 이벤트 합성 + recall 단언 렌더
  2. 무효화 매칭 — key↔key 정규화 비교 + 전체 토큰 AND (단일 CONTAINS 금지)
  3. 부활 — 같은 key + 미래 날짜 재등록 시 valid_to 해제
  4. 잊어줘 ≠ supersede — 잊어줘는 suppressed 재노출 금지 / 취소는 역사 보존
  5. answer_guard 계약 — '[요즘 흐름]' 마커 + '★이미 끝난 일★'/'★…아님★' 단언 포함
  (§8-4-6 검증 이관 게이트는 프로세스 요구사항 — 27종+가드 포팅 96%↑ 재통과 전 배선 금지)

기타 반영:
  · 복합감정 — 사건 2개 이상이면 사건별 KcELECTRA 개별 판정 (스펙 §9 첫 항목)
  · 위기 게이트 — crisis 턴 저장 차단 (v1 보안 자산 — 위기 발화 무저장 원칙, §8-4 아님)

의도적 제외 (2026-07-16 팀 결정):
  · 임베딩 — 사용 안 함(팀장 결정). 검색·병합·만료는 key/토큰 결정 매칭만.
    ※ 패러프레이즈 회상은 v1 실측 기준 56% 수준으로 하락 예상 — 게이트 측정으로 재평가.
  · Insight/리플렉션(은퇴 2026-07-15) · 요약 계층(은퇴 2026-07-16)
  · 확장 4종(State·Goal·Value·Coping)은 다음 단계 — 이 파일은 '기본 스키마' 범위.

안전장치: NEO4J_URI 미설정/실패 시 자동 no-op. 예외 삼킴(대화 흐름 보호).
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

# 다이얼 일원화 (2026-07-19) — 값·근거·env 이름은 memory_config.py 한 곳에서 관리.
# (CLOSURE_WINDOW=14 삭제 — 종결 단언 노출은 사건 자신의 occurs 날짜에서 유도:
#  날짜 있는 종결은 그 날짜가 지날 때까지, 날짜 없는 종결은 최신순 LIMIT 3이 양을 제한)
from .memory_config import (RECALL_LIMIT, OPENLOOP_MAX_AGE, RELCHANGE_WINDOW,
                            ABSENCE_MIN, VEC_INDEX, VEC_RECALL_MIN,
                            VEC_DEDUP_MIN, EXPIRE_VEC_MIN)

_NEG_EMO = ('슬픔', '분노')

# 잊어줘 명시 표현 — forget 판정의 결정적 게이트 (S05 실측 2026-07-18: 추출 LLM이
# '취소됐어'를 forget:true로 오분류 → 매칭 성공 시 역사까지 증발할 뻔. LLM 판정을
# 코드가 재확인한다 — 발화에 이 표현이 없으면 forget 강등)
_FORGET_HINT = re.compile(r'잊어|기억하지\s*마|지워|꺼내지\s*마|삭제해')

# 챗봇 캐릭터 이름 — 사용자의 인물이 아니다 (2026-07-20 실측: "고마워 까미야" →
# '까미야'(호격조사 포함)로 저장되는 자기참조 오염). 저장 단계에서 결정적으로 배제.
_CHARACTER_NAMES = {'포리', '까미', '토토', '여울'}


def _is_character(pn):
    """호격·존칭 어미를 벗기고 캐릭터 이름인지 판정 ('까미야'·'포리님'도 잡는다)."""
    n = re.sub(r'(야|아|님|씨)$', '', (pn or '').strip())
    return n in _CHARACTER_NAMES

# 종결 어휘 (v1 자산 — '그만두' 어간 포함: '그만두기 그만둠' 이중 접미 사고 방지)
_CLOSURE_STEM = re.compile(r'취소|그만두|그만둠|그만뒀|이별|절교|퇴사|무산|파토|종료|깨짐|깨졌|깨져|끝남|끝났|헤어')   # 활용형 포함 (S04-off 실측: '깨졌어'가 '깨짐'에 안 걸림)
_CLOSURE_TAIL = re.compile(r'(취소|그만둠|그만두기|이별|절교|퇴사|무산|파토|종료|깨짐|끝남)$')   # 끝단 앵커
# '그만두기' 추가 (S03-v2 실측 2026-07-20): 추출기가 종결 기록을 '편의점 알바 그만두기'로
# 명명 — '그만둠'만 알던 앵커가 못 알아봐 만료 유도가 침묵 (v1 '그만두기 그만둠' 교훈의 완결)
_CLOSURE_WORD = (('취소', '취소'), ('퇴사|그만', '그만둠'), ('이별|헤어', '이별'),
                 ('절교', '절교'), ('무산|파토|깨져|깨졌|깨짐', '무산'))


def _today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()


def _today_s():
    return _today().isoformat()


_today_iso = _today_s   # v1 호환 별칭 (memory_eval 러너가 사용)


def _now():
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%dT%H:%M:%S')


def _norm(s):
    s = (s or '').strip().lower()
    s = re.sub(r'[.,!?~…]+$', '', s)
    return re.sub(r'\s+', '', s)


def _tokens(s):
    """무효화 매칭용 토큰 — 2글자 이상 어절 (전체 토큰 AND의 재료)."""
    return [t for t in re.split(r'\s+', (s or '').strip()) if len(t) >= 2]


_CAUSAL_Q = re.compile(r'왜|때문|이유|어쩌다|무슨 일로')


def _causal_question(message):
    """'왜/때문/이유' 계열 질문 판정 — 인과 사슬(⑤) 주입 게이트 (결정적)."""
    return bool(_CAUSAL_Q.search(message or ''))


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
            auth = (os.environ.get('NEO4J_USER', 'neo4j'),
                    os.environ.get('NEO4J_PASSWORD', ''))
            try:
                # 속성 미존재 경고(01N52) 억제 — 새 그래프엔 valid_to 등이 아직 안 찍혀
                # 정상인데도 조회마다 경고가 콘솔을 뒤덮는다 (평가 로그 가독성 사고)
                drv = GraphDatabase.driver(uri, auth=auth,
                                           notifications_min_severity='OFF')
            except Exception:
                drv = GraphDatabase.driver(uri, auth=auth)   # 구버전 드라이버 폴백
            drv.verify_connectivity()
            _setup(drv)
            _driver = drv
            print('[graph_memory_v2_base] Neo4j(temporal KG) 연결됨')
        except Exception as e:
            print(f'[graph_memory_v2_base] Neo4j 비활성({e})')
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
        # (em_type 유일 제약 제거 2026-07-16 — v1이 Emotion을 {uid,type}로 만들어 같은 DB에서
        #  충돌·캡처 전멸 사고. MERGE by type만으로 공유 노드 보장은 충분)
        'CREATE CONSTRAINT pl_name IF NOT EXISTS FOR (p:Place) REQUIRE p.name IS UNIQUE',
        'CREATE CONSTRAINT tp_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE',
        'CREATE INDEX ev_key IF NOT EXISTS FOR (e:Event) ON (e.uid, e.key)',
        'CREATE INDEX ev_occ IF NOT EXISTS FOR (e:Event) ON (e.uid, e.occurs_end)',
        'CREATE INDEX pr_key IF NOT EXISTS FOR (p:Person) ON (p.uid, p.key)',
    ]
    with drv.session() as s:
        for q in stmts:
            try:
                s.run(q)
            except Exception as e:
                print(f'[graph_memory_v2_base] 스키마 경고: {e}')
    try:
        from chat import embedder
        with drv.session() as s:
            s.run(f'CREATE VECTOR INDEX {VEC_INDEX} IF NOT EXISTS '
                  'FOR (e:Event) ON (e.embedding) '
                  'OPTIONS {indexConfig: {`vector.dimensions`: $dim, '
                  '`vector.similarity_function`: "cosine"}}', dim=embedder.EMBED_DIM)
    except Exception as e:
        print(f'[graph_memory_v2_base] 벡터 인덱스 생성 실패(결정 매칭 폴백): {e}')


# ── 감정: 학습 모델(KcELECTRA) 4확률 — 감정 소스는 모델 하나 ──
def _emotion_probs(text):
    try:
        from ai.emotion.emotion_model import predict_emotion_full
        _, _, probs = predict_emotion_full(text)
        return probs or {}
    except Exception:
        return {}


# ── 추출 (v1 프롬프트 자산 포팅) ──────────────────────────────
def _extract(message):
    from ai.agents.llm import get_llm
    sys = (
        "사용자 메시지에서 '기억할 가치가 있는' 것을 JSON으로만 출력하라.\n"
        "[반드시 기록 — 최우선. 일상처럼 보여도 기록]\n"
        "- 계획·약속, 사건(과거의 일 포함), 관계·이름 소개(가족·친구·반려동물), 취향, 구매.\n"
        "- ★지속 고민·스트레스·상태도 사건으로 기록★ ('이직할까 고민이 많아'→'이직 고민', "
        "'야근 3일 연속'→'연속 야근'). 마음 상태 발화는 잡담이 아니다 — 버리지 마라.\n"
        "- ★★이 프롬프트의 예시 문구를 출력에 복사하지 마라. 오직 사용자 메시지에 실제로 "
        "등장한 내용만 기록★★ (실측 사고: '발표 망쳤어' 한 문장에서 예시의 '연속 야근'· "
        "'스트레스'가 지어내져 저장됨 — 없는 기억 날조는 최악의 오류다).\n"
        "- ★한 메시지에 사실이 여러 개면 하나도 빼지 말고 각각 기록★\n"
        "- 반려동물 이름은 relations에 (예: '강아지 콩이' → {\"person\":\"콩이\","
        "\"relation\":\"반려동물(강아지)\"}).\n"
        "[버릴 것 — 위에 해당 안 될 때만] 일회성 일상 보고(식사·날씨·버스)와 감탄·맞장구.\n"
        "[name 규칙] 5~15자, 맥락 있게('혼남' 말고 '상사한테 혼남'). 사용자가 말한 구체적 "
        "이름 그대로 — '포항 여행'을 '여행'으로 뭉개면 다른 기억까지 잘못 만료된다.\n"
        f"[date 규칙] 다가오는 일정·콕 집은 날짜만, 오늘 {_today_s()} 기준 YYYY-MM-DD. "
        "기간이면 date(시작)+date_end(끝) — 사용자가 명시한 날짜만, 계산·추측 금지. "
        "과거의 일은 date를 null로.\n"
        "[인과 규칙] caused_by는 사용자가 '~때문에/~해서'로 명시한 경우만. 추측 금지. "
        "★방향 주의: 'X 때문에 Y'라고 말하면 결과 Y의 caused_by가 원인 X다 — 둘 다 "
        "events로 기록하고, cause 텍스트 필드에 결과를 적는 역전 금지. "
        "X·Y는 자리표시자일 뿐이다 — 사용자가 실제로 말한 사건 이름만 써라.★\n"
        "events: {name, date, date_end, place, topic(취업/건강/연애/가족/학업/돈/취미 등 "
        "한 단어), people(배열), cause(이유 텍스트), caused_by(원인인 같은 메시지 내 다른 "
        "사건 이름)}\n"
        "★place: 발화에 장소가 있으면 반드시 place 필드에 분리해 담아라 — 이름에 뭉치지 "
        "말 것 ('성수동 카페에서 수아랑 만나기로' → name '수아와 만남', place '성수동 카페' / "
        "'홍대에서 놀았어' → place '홍대'). 장소 언급이 없으면 생략.★\n"
        "★date 판별: 약속·계획·기념일·시험처럼 '그 날짜가 챙길 의미가 있는' 사건에만 담아라. "
        "이미 일어난 일상 서술('점심 못 먹었어', '오늘 힘들었어')에 오늘 날짜를 붙이지 마라 — "
        "일정이 아닌 것이 다가오는 일로 둔갑한다.★\n"
        "relations: {person, relation(가족/친구/연인/직장/반려동물)}\n"
        "★relations 판별: 사용자가 '자기 사람'으로 선언·서사한 관계만 담아라 "
        "('내 친구 수아', '우리 엄마', '회사 동료 지현'). 사건 서술에 역할로 등장만 한 "
        "인물(팀장님·의사·사장 등)은 relations 금지 — 그 사건 events의 people에만.★\n"
        "★챗봇 캐릭터(포리·까미·토토·여울)는 대화 상대인 나 자신이다 — people·relations 어디에도 "
        "절대 넣지 마라.★\n"
        "preferences: {topic, polarity: 호|오, category} — ★topic은 좋아하는 대상 그대로"
        "('민트초코','클라이밍'). 카테고리('맛','취미')로 뭉개면 잊어줘가 그 대상을 "
        "못 찾는다★ category는 그 대상이 속한 분류 한 단어(음식/음료/취미/운동/음악/"
        "콘텐츠/장소/동물/기타) — 사건의 topic과 같은 어휘를 써라.\n"
        "invalidations(끝난 것): {kind: relation|event|preference, name, reason, forget} — "
        "이별·절교·퇴사·취소·약속 깨짐·파토. name은 끝난 '대상'의 이름('편의점 알바' O, "
        "'편의점 알바 그만두기' X). 이유·배경으로만 언급된 사람을 관계 종결로 확대 해석 "
        "금지 — 직접 끝냈다고 말한 대상만.\n"
        "★kind 판별: relation은 '사람'과의 관계(연인·친구·가족)가 끝날 때만. 알바·직장·"
        "일정·활동·계획이 끝난 건 전부 event다 ('편의점 알바 그만둠'→event, "
        "'준호와 이별'→relation).★\n"
        "['잊어줘'] forget:true는 사용자가 '잊어줘/기억하지 마/지워줘/그 얘기 꺼내지 마'라고 "
        "★명시적으로 요청했을 때만★. 취소·이별·퇴사·무산은 forget:false다 — 끝났어도 "
        "역사는 남겨야 한다. 잊어달라는 요청 자체는 events로 저장 금지.\n"
        "[끝난 것 병기] 이별·취소·퇴사는 invalidations와 events 둘 다 — events엔 "
        "'끝났다는 사실'(예: '제주 여행 취소'). 단 name에 이미 종결어가 있으면 그대로.\n"
        "★출력 형식: 네 필드(events·relations·preferences·invalidations) 전부 배열이다. "
        "항목이 하나여도 반드시 [ ] 배열로 감싸라.★\n"
        '예: {"events":[{"name":"병원 방문","date":"2026-07-20","topic":"건강",'
        '"people":["엄마"]}],"relations":[{"person":"엄마","relation":"가족"}]}\n'
        "직접 말한 것만. 추측 금지. 빈 배열 생략 가능. JSON 외 금지."
    )
    try:
        llm = get_llm(temperature=0, max_tokens=500)
        msgs = [('system', sys), ('user', message)]
        try:
            # 구조 강제 (2026-07-18): JSON 형식을 프롬프트 부탁이 아니라 API로 보장
            # — 'events가 dict로 옴' 62% 사고의 근본 처방. _norm_shape는 2차 방어로 유지.
            resp = llm.bind(response_format={'type': 'json_object'}).invoke(msgs)
        except Exception:
            resp = llm.invoke(msgs)   # 미지원 버전 폴백
        raw = resp.content.strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()
        d = json.loads(raw)
        return _norm_shape(d)
    except Exception:
        return {}


def _norm_shape(d):
    """추출 JSON 형식 정규화 (2026-07-16 실측 사고 봉인 — 62% 붕괴의 최상류 원인).
    LLM이 단일 객체를 배열 없이 내면(events가 dict) 저장 0건 → 회상 전무 → 백지 창작.
    dict → [dict]로 감싸고, 리스트도 dict도 아니면 버린다."""
    if not isinstance(d, dict):
        return {}
    for k in ('events', 'relations', 'preferences', 'invalidations'):
        v = d.get(k)
        if v is None:
            d[k] = []
        elif isinstance(v, dict):
            d[k] = [v]
        elif not isinstance(v, list):
            d[k] = []
    return d


# ── 종결 이벤트 합성 (§8-4-1) ─────────────────────────────────
def _derive_invalidations_from_closures(data, message):
    """추출이 종결 이벤트('편의점 알바 그만둠')만 내고 invalidations를 빠뜨린 회차 방어
    (S03-off 실측: 만료 미발생 → '알바 시작했잖아' 오답). 종결 이벤트 이름에서 종결어를
    벗겨 만료 대상을 결정적으로 복원한다 — LLM 누락을 코드가 되채우는 역방향 합성."""
    if not _CLOSURE_STEM.search(message or ''):
        return data
    if data.get('invalidations'):
        return data
    derived = []
    for ev in (data.get('events') or []):
        if not isinstance(ev, dict):
            continue
        name = (ev.get('name') or '').strip()
        m = _CLOSURE_TAIL.search(name)
        if not m:
            continue
        target = name[:m.start()].strip()
        if len(target) >= 2:
            derived.append({'kind': 'event', 'name': target, 'forget': False})
            print(f'[graph_memory_v2_base] 만료 대상 유도: {name} → {target} (추출 누락 방어)')
    if not derived:
        # 최후 방어벨트 (S03 재퇴행 실측 2026-07-19): 추출이 invalidations도 종결
        # 이벤트도 안 낸 회차 — 발화 자체에서 만료 대상을 결정적으로 파싱.
        # 파싱 결과도 이후 해석기(토큰 AND → LLM)를 거치므로 쓰레기면 자연 무시(no-op).
        m = re.search(r'([가-힣A-Za-z0-9 ]{2,24}?)\s*(?:이|가|은|는|도|을|를)?\s*'
                      r'(?:취소됐|취소 됐|깨졌|무산됐|파토\s*났|그만뒀|끝났)', message or '')
        if m:
            toks = [t for t in m.group(1).split() if len(t) >= 2
                    and t not in ('근데', '그냥', '오늘', '어제', '요즘', '그거', '아까')]
            target = ' '.join(toks[-3:]).strip()
            if len(target) >= 2:
                derived.append({'kind': 'event', 'name': target, 'forget': False})
                print(f'[graph_memory_v2_base] 만료 대상 발화 파싱: → {target} (최후 방어)')
    if derived:
        data['invalidations'] = derived
    return data


def _derive_forget_from_speech(data, message):
    """잊어줘 최후 방어 (2026-07-20 실측: '점심 못 먹음 잊어줘' 2연속 무시) —
    발화에 잊어줘 명시가 있는데 추출이 forget invalidation을 안 냈으면
    발화에서 대상을 결정적으로 파싱해 합성. 이후 해석기(토큰 AND→LLM)가 실명 매칭."""
    if not _FORGET_HINT.search(message or ''):
        return data
    invs = [i for i in (data.get('invalidations') or []) if isinstance(i, dict)]
    if any(i.get('forget') for i in invs):
        return data
    m = re.search(r'([가-힣A-Za-z0-9 ]{2,24}?)\s*(?:얘기|이야기|것|건|거)?\s*'
                  r'(?:는|은|도|를|을)?\s*(?:잊어|기억하지\s*마|지워|꺼내지\s*마)', message or '')
    if m:
        toks = [t for t in m.group(1).split() if len(t) >= 2
                and t not in ('근데', '그냥', '이제', '제발', '그거', '아까', '방금')]
        target = ' '.join(toks[-3:]).strip()
        if len(target) >= 2:
            invs.append({'kind': 'event', 'name': target, 'forget': True})
            data['invalidations'] = invs
            print(f'[graph_memory_v2_base] 잊어줘 발화 파싱: → {target} (최후 방어)')
    return data


def _demote_unhinted_forget(data, message):
    """발화에 잊어줘 명시 표현이 없으면 forget → False (supersede로 강등, 역사 보존).
    잊어줘 과소 판정(놓침)은 rubric상 안전하지만, 과잉 판정은 역사 삭제 사고다."""
    if _FORGET_HINT.search(message or ''):
        return data
    for inv in (data.get('invalidations') or []):
        if isinstance(inv, dict) and inv.get('forget'):
            inv['forget'] = False
            print(f"[graph_memory_v2_base] forget 강등: {inv.get('name')} "
                  '(잊어줘 명시 표현 없음 — supersede로 처리)')
    return data


def _synthesize_closures(data, message):
    """invalidations에 대응하는 종결 이벤트가 events에 없으면 합성 (§8-4-1).
    LLM이 병기 규칙을 놓친 회차 방어 (v1 실측: temp 0에서도 간헐 누락).
    v1 봉인 3종 포함: 파편 저장 금지 · kind 변주 관용 · 이중 접미 방지."""
    if not isinstance(data.get('events'), list):
        data['events'] = []
    events = data['events']   # 반드시 data 내부 리스트 참조 — `or []`는 고아 리스트 사고
    inv_list = [i for i in (data.get('invalidations') or []) if isinstance(i, dict)]
    inv_keys = [_norm(i.get('name') or '') for i in inv_list]

    # 파편 필터 (§8-4-1b + S02-off 확장 2026-07-19): 만료 대상 이름의 '조각'("여행"⊂
    # "강릉 여행")뿐 아니라 ★같은 이름의 맨몸 재진술★("제주도 여행" 그대로)도 저장 금지.
    # 실측: 추출기가 취소 발화에서 원본 이름을 이벤트로 재발행 → keep 보호가 만료 대상
    # 본인을 지켜버려 만료 불발 (보호 장치가 피해자를 보호한 역설). 종결 기록(~취소)만 생존.
    def _is_fragment(e):
        name = (e.get('name') or '').strip() if isinstance(e, dict) else ''
        if _CLOSURE_TAIL.search(name):
            return False    # 종결 기록은 이번 턴의 주인공 — 절대 안 버림
        k = _norm(name)
        return bool(k) and any(k == ik or k in ik for ik in inv_keys if ik)
    events[:] = [e for e in events if isinstance(e, dict) and not _is_fragment(e)]

    for inv in inv_list:
        if inv.get('forget'):
            continue    # 잊어줘는 종결 기록을 남기지 않는다 (재노출 금지)
        kind = (inv.get('kind') or '').strip().lower()
        if kind in ('person', 'relation', 'preference'):
            continue    # 명시된 인물·취향만 제외 — kind 변주('Event'·'여행'·생략)는 관용 (속초 3연속)
        name = (inv.get('name') or '').strip()
        if not name:
            continue
        nk = _norm(name)

        # 이번 턴에 이 대상의 '종결' 사건이 이미 있으면 합성 생략 (중복 방지).
        # 종결 판정은 끝단 앵커(_CLOSURE_TAIL) — '퇴사 면담 예정'(어간이 중간)은 종결 아님.
        def _is_closure_of(e):
            en = (e.get('name') or '').strip()
            return bool(nk and nk in _norm(en) and _CLOSURE_TAIL.search(en))
        if any(_is_closure_of(e) for e in events):
            continue
        if _CLOSURE_STEM.search(name):
            events.append({'name': name})   # 이름에 이미 종결어('그만두기' 등) — 그대로 (이중 접미 방지)
            continue
        word = next((w for p, w in _CLOSURE_WORD
                     if re.search(p, (inv.get('reason') or '') + ' ' + message)), '종료')
        events.append({'name': f'{name} {word}'})
        print(f'[graph_memory_v2_base] 종결 기록 합성: {name} {word}')
    return data


def _vector_expire_match(drv, uid, name):
    """만료 벡터 폴백 (0.60) — 글자가 안 겹치는 만료 대상('운동 레슨'≈'PT 첫 수업' 0.70).
    v1 실측 경로 복원 (memory_expire_bench: 무관 최고 0.42 < 임계 0.60)."""
    try:
        from chat import embedder
        if not embedder.is_available():
            return None
        with drv.session() as s:
            row = s.run(
                f'CALL db.index.vector.queryNodes("{VEC_INDEX}", 4, $vec) '
                'YIELD node, score '
                'WHERE node.uid=$uid AND score>=$min '
                '  AND coalesce(node.suppressed,false)=false '
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(node) '
                'WHERE h.valid_to IS NULL '
                'RETURN node.name AS n, score ORDER BY score DESC LIMIT 1',
                vec=embedder.embed(name), uid=uid, min=EXPIRE_VEC_MIN).single()
        if row:
            print(f"[graph_memory_v2_base] 만료 벡터 매칭: '{name}' ≈ '{row['n']}' "
                  f"({row['score']:.2f}) → 대상 확정")
            return row['n']
    except Exception:
        pass
    return None


def _resolve_invalidations(drv, uid, data, message=''):
    """만료 대상 해석 (2026-07-16) — 결정 매칭(토큰 AND) 실패 시 LLM 1회 판정 폴백.
    v1 임베딩 폴백(0.60)의 자리 대체 — 임베딩 미사용 결정 하의 표현 변주 대응.
    실측 근거: S05 '운동 레슨 취소' vs 저장명 'PT 첫 수업' (글자 0겹침 → 만료 실패 → 취소
    일정을 계속 챙기는 오답), S04 '영화 약속' vs '태영과 영화 보기'. 무효화는 드문 이벤트라
    LLM 1회 비용 미미. 시그니처 패턴: 결정적 게이트 → 실패 시에만 LLM 확인."""
    invs = [i for i in (data.get('invalidations') or []) if isinstance(i, dict)]
    if not invs:
        return data
    try:
        with drv.session() as s:
            cand = {
                'event': [r['n'] for r in s.run(
                    'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                    'WHERE h.valid_to IS NULL RETURN e.name AS n LIMIT 30',
                    uid=uid).data()],
                'relation': [r['n'] for r in s.run(
                    'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                    'WHERE r.valid_to IS NULL RETURN p.name AS n LIMIT 30',
                    uid=uid).data()],
                'preference': [r['n'] for r in s.run(
                    'MATCH (u:User {uid:$uid})-[r:PREFERS]->(t:Topic) '
                    'WHERE r.valid_to IS NULL RETURN t.name AS n LIMIT 30',
                    uid=uid).data()],
            }
    except Exception:
        return data
    for inv in invs:
        name = (inv.get('name') or '').strip()
        if not name:
            continue
        kind = (inv.get('kind') or '').strip().lower()
        toks = [_norm(t) for t in _tokens(name)] or [_norm(name)]

        # kind 교정 게이트 (S03-v2 실측 2026-07-20): 추출 LLM이 '편의점 알바'를
        # kind=relation으로 오분류 → 만료 요청이 빈 인물 서랍으로 가서 조용히 증발
        # ('알바 시작했잖아' 오답의 뿌리). 신고된 kind에 맞는 게 없고 다른 kind에
        # 정확히(전체 토큰 AND) 맞는 게 있으면 결정적으로 재배달한다.
        def _hits(k):
            return any(all(t in _norm(c) for t in toks)
                       for c in (cand.get(k) or []) if c)
        if kind not in cand:
            kind = 'event'
        if not _hits(kind):
            alt = next((k2 for k2 in ('event', 'relation', 'preference')
                        if k2 != kind and _hits(k2)), None)
            if alt:
                print(f'[graph_memory_v2_base] 만료 kind 교정: {name} '
                      f'{kind}→{alt} (신고 서랍 비었음 — 결정 매칭 재배달)')
                kind = alt
                inv['kind'] = alt

        pool = [c for c in (cand.get(kind) if kind in cand else cand['event']) or [] if c]
        if not pool:
            continue
        if any(all(t in _norm(c) for t in toks) for c in pool):
            continue    # 1차: 결정 매칭 (비용 0 경로)
        if kind not in ('relation', 'preference'):
            hit = _vector_expire_match(drv, uid, name)   # 2차: 벡터 폴백 0.60 (v1 경로 복원)
            if hit:
                inv['name'] = hit
                continue
        try:
            from ai.agents.llm import get_llm
            # v4 (2026-07-18): 열린 선택은 소형 모델이 겁먹고 '없음'으로 도망친다(S05 3연속
            # 실측). 항목별 같다/다르다 판단을 먼저 시키면 판정을 감행한다.
            resp = get_llm(temperature=0, max_tokens=120).invoke([
                ('system',
                 "사용자의 기억 목록과 '끝났다/취소됐다'는 발화다. 끝난 대상이 목록의 어느 "
                 "항목인지 판정하라.\n"
                 "절차: 각 항목마다 '발화의 대상과 같은 활동·일정·관계인가?'를 같다/다르다로 "
                 "한 줄씩 판단하라. 사람은 같은 것을 매번 다르게 부른다 — 'PT 수업'을 "
                 "'운동 레슨'으로, '미용실 예약'을 '머리하러 가기'로. 이름이 달라도 범주와 "
                 "맥락이 맞으면 같다.\n"
                 "마지막 줄: '같다' 항목이 있으면 그 이름만 목록 표기 그대로, 없으면 '없음'."),
                ('user', f'발화: {message}\n끝난 대상: {name}\n목록: '
                         + json.dumps(pool, ensure_ascii=False)),
            ])
            pick = (resp.content or '').strip().splitlines()[-1].strip().strip('"\'')
            if pick not in pool:
                # 모델이 라벨을 따라 쓰는 사고("마지막 줄: PT 첫 수업") — 정답을 라벨 때문에
                # 버리지 않게, 후보명이 출력 안에 통째로 들어 있으면 그걸로 인정 (S05 실측)
                contained = [c for c in pool if c and c in pick]
                if len(contained) == 1:
                    pick = contained[0]
            if pick and pick != '없음' and pick in pool:
                print(f'[graph_memory_v2_base] 만료 대상 해석: {name} → {pick} (LLM 폴백)')
                inv['name'] = pick
            else:
                print(f'[graph_memory_v2_base] 만료 대상 해석 불발: {name} → {pick!r} '
                      f'(후보 {len(pool)}개)')   # S05 사고: 불발이 침묵하면 진단 불가
        except Exception:
            pass    # 폴백 실패 = 현상 유지 (미스는 안전, 오폭은 재앙 — v1 원칙)
    return data


# 공통 temporal edge 속성 (MERGE 후 ON CREATE로 찍음)
_TSTAMP = ('ON CREATE SET r.valid_from=$now, r.valid_to=null, '
           'r.created_at=$now, r.episode=$eid ')


def _store(tx, uid, data, msg_probs, message, vectors=None):
    now = _now()
    today = _today_s()
    eid = 'ep_' + uuid.uuid4().hex[:12]
    tx.run('MERGE (u:User {uid:$uid})', uid=uid)
    tx.run('CREATE (ep:Episode {id:$eid, uid:$uid, text:$text, created_at:$now})',
           eid=eid, uid=uid, text=message[:1000], now=now)

    events = [e for e in (data.get('events') or []) if isinstance(e, dict)]
    keep_keys = set()   # 이번 턴 저장분 — 무효화에서 보호 (§8-4-1a)

    for ev in events:
        name = (ev.get('name') or '').strip()
        key = _norm(name)
        if not key:
            continue
        vec = (vectors or {}).get(name)
        # dedup 2차 (0.93): 표기가 달라도 의미가 같으면 기존 노드에 병합.
        # 종결 기록('~취소')은 유사해도 원본에 병합 금지 — 병합되면 keep 보호가
        # 만료 도장을 막는 v1 S04 회귀.
        if vec is not None and not _CLOSURE_TAIL.search(name):
            try:
                row = tx.run(
                    f'CALL db.index.vector.queryNodes("{VEC_INDEX}", 3, $vec) '
                    'YIELD node, score '
                    'WHERE node.uid=$uid AND score>=$min AND node.key<>$key '
                    '  AND coalesce(node.suppressed,false)=false '
                    'RETURN node.key AS k, node.name AS n, score '
                    'ORDER BY score DESC LIMIT 1',
                    vec=vec, uid=uid, min=VEC_DEDUP_MIN, key=key).single()
                if row and not _CLOSURE_TAIL.search((row['n'] or '').strip()):
                    print(f"[graph_memory_v2_base] dedup2: '{name}' ≈ '{row['n']}' "
                          f"({row['score']:.2f}) → 병합")
                    name, key = row['n'], row['k']
            except Exception:
                pass
        keep_keys.add(key)
        # 복합감정(§9-1): 사건 2개 이상이면 사건별 판정, 아니면 메시지 단위
        probs = ev.get('_probs') if ev.get('_probs') is not None else msg_probs
        top_emo = max(probs, key=probs.get) if probs else None
        salience = 1.0 + max((probs.get(k, 0.0) for k in _NEG_EMO), default=0.0)
        # C1: 기간 사건 — occurs_start/occurs_end (사용자 명시 날짜만)
        d_start = (ev.get('date') or '').strip() or None
        d_end = (ev.get('date_end') or '').strip() or None
        tx.run(
            'MATCH (u:User {uid:$uid}), (ep:Episode {id:$eid}) '
            'MERGE (e:Event {uid:$uid, key:$key}) '
            'ON CREATE SET e.id=$evid, e.name=$name, e.created_at=$now, e.recall_count=0 '
            'SET e.cause=coalesce($cause,e.cause), e.top_emotion=coalesce($top,e.top_emotion), '
            '    e.salience=CASE WHEN coalesce(e.salience,0)<$sal THEN $sal ELSE e.salience END, '
            '    e.occurs_start=coalesce($ds,e.occurs_start), '
            '    e.occurs_end=coalesce($de,e.occurs_end), '
            '    e.embedding=coalesce(e.embedding,$vec) '   # 의미 검색 재료 (없으면 유지)
            'MERGE (ep)-[:RECORDS]->(e) '
            'MERGE (u)-[r:HAS_EVENT]->(e) ' + _TSTAMP,
            uid=uid, eid=eid, key=key, evid='ev_' + uuid.uuid4().hex[:10],
            name=name, now=now, cause=(ev.get('cause') or '').strip() or None,
            top=top_emo, sal=salience, ds=d_start, de=d_end, vec=vec)
        # 부활 (§8-4-3): 같은 key + 미래 날짜 재등록 → 무효화 해제
        if d_start and d_start >= today:
            tx.run('MATCH (u:User {uid:$uid})-[r:HAS_EVENT]->(e:Event {uid:$uid,key:$key}) '
                   'WHERE r.valid_to IS NOT NULL '
                   'SET r.valid_to=null, r.end_reason=null, e.suppressed=null',
                   uid=uid, key=key)
        # 언제 (C1: ON{role}) / 어디서 / 주제
        if d_start:
            role = 'start' if d_end else 'on'
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (d:Date {date:$v}) '
                   'MERGE (e)-[r:ON {role:$role}]->(d) ' + _TSTAMP,
                   uid=uid, key=key, v=d_start, role=role, now=now, eid=eid)
        if d_end:
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (d:Date {date:$v}) '
                   "MERGE (e)-[r:ON {role:'end'}]->(d) " + _TSTAMP,
                   uid=uid, key=key, v=d_end, now=now, eid=eid)
        if (ev.get('place') or '').strip():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (p:Place {name:$v}) '
                   'MERGE (e)-[r:AT]->(p) ' + _TSTAMP,
                   uid=uid, key=key, v=ev['place'].strip(), now=now, eid=eid)
        if (ev.get('topic') or '').strip():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (t:Topic {name:$v}) '
                   'MERGE (e)-[r:ABOUT]->(t) ' + _TSTAMP,
                   uid=uid, key=key, v=ev['topic'].strip(), now=now, eid=eid)
        for pn in (ev.get('people') or []):
            pk = _norm(pn)
            if not pk or _is_character(pn):   # 캐릭터 자기참조 배제 (호격 '까미야' 포함)
                continue
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) '
                   'MERGE (p:Person {uid:$uid,key:$pk}) ON CREATE SET p.name=$pn '
                   'MERGE (e)-[r:INVOLVES]->(p) ' + _TSTAMP,
                   uid=uid, key=key, pk=pk, pn=(pn or '').strip(), now=now, eid=eid)
        for et, sc in (probs or {}).items():
            tx.run('MATCH (e:Event {uid:$uid,key:$key}) MERGE (m:Emotion {type:$et}) '
                   'MERGE (e)-[r:EVOKED]->(m) '
                   'ON CREATE SET r.score=$sc, r.episode=$eid '
                   'SET r.score=$sc',
                   uid=uid, key=key, et=et, sc=float(sc), eid=eid)

    # 인과 — 사용자가 명시한 경우만 (추출 규칙에서 잠금)
    ev_keys = {_norm(e.get('name') or '') for e in events}
    for ev in events:
        cb, ek = _norm(ev.get('caused_by') or ''), _norm(ev.get('name') or '')
        if cb and ek and cb in ev_keys and ek in ev_keys and cb != ek:
            tx.run('MATCH (a:Event {uid:$uid,key:$ek}),(b:Event {uid:$uid,key:$cb}) '
                   'MERGE (a)-[:BECAUSE_OF]->(b)', uid=uid, ek=ek, cb=cb)

    # 관계 (RELATES_TO {relation, sentiment}) — 시간 사실
    for rl in (data.get('relations') or []):
        if not isinstance(rl, dict):
            continue
        pn = (rl.get('person') or '').strip()
        pk = _norm(pn)
        if not pk or _is_character(pn):   # 캐릭터 자기참조 배제 (호격 '까미야' 포함)
            continue
        rel = (rl.get('relation') or '').strip() or '지인'
        tx.run('MATCH (u:User {uid:$uid}) MERGE (p:Person {uid:$uid,key:$pk}) '
               'ON CREATE SET p.name=$pn '
               'MERGE (u)-[r:RELATES_TO {relation:$rel}]->(p) ' + _TSTAMP,
               uid=uid, pk=pk, pn=pn, rel=rel, now=now, eid=eid)

    # 취향 (PREFERS {polarity}) — 시간 사실
    for pf in (data.get('preferences') or []):
        tp = (pf.get('topic') if isinstance(pf, dict) else pf) or ''
        tk = (tp or '').strip()
        if not tk:
            continue
        pol = (pf.get('polarity') if isinstance(pf, dict) else None) or '호'
        tx.run('MATCH (u:User {uid:$uid}) MERGE (t:Topic {name:$tk}) '
               'MERGE (u)-[r:PREFERS {polarity:$pol}]->(t) ' + _TSTAMP,
               uid=uid, tk=tk, pol=pol, now=now, eid=eid)
        # Topic 계층 (2026-07-20): 구체 취향 → 카테고리 간선 — 사건의 ABOUT 카테고리와
        # 같은 노드를 공유해 '민트초코 → 음식 ← 맛집 사건'으로 연결된다 (관계 11종째)
        cat = ((pf.get('category') if isinstance(pf, dict) else None) or '').strip()
        if cat and cat != tk:
            tx.run('MATCH (t:Topic {name:$tk}) MERGE (c:Topic {name:$cat}) '
                   'MERGE (t)-[:IN_CATEGORY]->(c)', tk=tk, cat=cat)

    # 무효화 (belief revision) — §8-4-2/4: key↔key + 전체 토큰 AND, 잊어줘 분리
    for inv in (data.get('invalidations') or []):
        if not isinstance(inv, dict):
            continue
        iname = (inv.get('name') or '').strip()
        ck = _norm(iname)
        if not ck:
            continue
        kind = (inv.get('kind') or '').strip().lower()
        forget = bool(inv.get('forget'))
        reason = (inv.get('reason') or '').strip() or None
        etype = {'relation': 'RELATES_TO', 'preference': 'PREFERS'}.get(kind, 'HAS_EVENT')
        toks = [_norm(t) for t in _tokens(iname)] or [ck]
        # 대상 탐색: 정규화 key끼리. 전체 토큰 AND — 단일 CONTAINS 광역 오폭 방지
        rows = tx.run(
            f'MATCH (u:User {{uid:$uid}})-[r:{etype}]->(n) '
            'WHERE r.valid_to IS NULL '
            'RETURN coalesce(n.key, toLower(n.name)) AS k', uid=uid).data()
        targets = [row['k'] for row in rows
                   if row['k'] and all(t in row['k'] for t in toks)]
        if kind == 'event':
            # keep 보호 축소 (S03-v2 keep 역설, 2026-07-20): 이번 턴 저장분 중
            # '종결 기록'만 보호한다. 이전엔 전부 보호 → 추출기가 만료 피해자를
            # 꼬리 붙여 재진술하면("편의점 알바 시작") 파편 필터(같은 이름만 제거)를
            # 빠져나가 keep이 만료를 막았다 — 조용한 만료 불발의 뿌리.
            # 재진술이 도장을 맞아도 옳다: 그 사실이 끝났다는 게 이번 턴의 진실이니까.
            targets = [k for k in targets
                       if k not in keep_keys or not _CLOSURE_TAIL.search(k)]
        for tk_ in targets:
            tx.run(
                f'MATCH (u:User {{uid:$uid}})-[r:{etype}]->(n) '
                'WHERE r.valid_to IS NULL AND coalesce(n.key, toLower(n.name))=$tk '
                'SET r.valid_to=$today, r.end_reason=coalesce($reason,r.end_reason)' +
                (', n.suppressed=true' if forget else ''),
                uid=uid, tk=tk_, today=today,
                reason='사용자 요청' if forget else reason)
            if forget and etype == 'RELATES_TO':
                # 잊어줘(인물) = 그 인물이 얽힌 사건까지 재노출 금지 (F02 실측:
                # 인물은 지워졌는데 '소개팅' 이벤트가 살아서 되노출). "관련 기억 전부" 원칙.
                tx.run(
                    'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event)'
                    '-[:INVOLVES]->(p:Person {uid:$uid}) '
                    'WHERE coalesce(p.key, toLower(p.name))=$tk '
                    "SET h.valid_to=$today, h.end_reason='사용자 요청', e.suppressed=true",
                    uid=uid, tk=tk_, today=today)


def _capture(uid, message, crisis=False):
    try:
        if crisis:
            return    # 위기 게이트: 위기 발화는 그래프에 박제하지 않는다
        drv = _get_driver()
        if drv is None:
            return
        data = _extract(message)
        if not data or not any(data.get(k) for k in
                               ('events', 'relations', 'preferences', 'invalidations')):
            return
        data = _demote_unhinted_forget(data, message)   # forget 오분류 강등 (결정적 게이트)
        data = _derive_forget_from_speech(data, message)   # 잊어줘 누락 역합성 (최후 방어)
        data = _derive_invalidations_from_closures(data, message)   # 만료 누락 역합성 (S03 방어)
        data = _resolve_invalidations(drv, uid, data, message)   # 해석 먼저 — 종결 합성이 실명(實名)을 쓰게
        data = _synthesize_closures(data, message)
        msg_probs = _emotion_probs(message)
        events = [e for e in (data.get('events') or []) if isinstance(e, dict)]
        if len(events) >= 2:    # 복합감정: 사건별 개별 판정 ("이별=슬픔, 빵=기쁨")
            for ev in events:
                seg = ((ev.get('name') or '') + ' ' + (ev.get('cause') or '')).strip()
                ev['_probs'] = _emotion_probs(seg) or msg_probs
        vectors = {}
        try:
            from chat import embedder
            if embedder.is_available():
                for ev in events:
                    nm = (ev.get('name') or '').strip()
                    if nm:
                        vectors[nm] = embedder.embed(nm)
        except Exception:
            vectors = {}
        with drv.session() as s:
            s.execute_write(lambda tx: _store(tx, uid, data, msg_probs, message,
                                              vectors=vectors))
    except Exception as e:
        print(f'[graph_memory_v2_base] 캡처 실패: {e}')


def capture_async(user_id, message, crisis=False, **_):
    if not user_id or not (message or '').strip() or not is_enabled():
        return
    threading.Thread(target=_capture, args=(user_id, message, crisis), daemon=True).start()


# ── 회상 — answer_guard 계약(§8-4-5): 마커·단언 문자열 유지 필수 ──
def recall(user_id, message=None, limit=None):
    if not user_id or not is_enabled():
        return ''
    limit = limit or RECALL_LIMIT
    try:
        drv = _get_driver()
        lines, today = [], _today_s()
        with drv.session() as s:
            # ⓪ 최근 종결 단언 (§8-4-1c) — 잊어줘(suppressed)는 제외.
            # 노출 창은 사건 자신의 날짜에서 유도 (2026-07-19): 예정일이 있던 종결은
            # 그 날짜가 지날 때까지 (그때까지가 "곧 가겠네" 오폭 위험 구간),
            # 날짜 없는 종결은 창 없이 최신순 — LIMIT 3이 밀어내기로 양을 제한.
            for c in s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NOT NULL AND e.suppressed IS NULL '
                '  AND (e.occurs_start IS NULL '
                '       OR coalesce(e.occurs_end, e.occurs_start) >= $today) '
                'RETURN e.name AS n, h.valid_to AS d, h.end_reason AS why '
                'ORDER BY h.valid_to DESC LIMIT 3',
                    uid=user_id, today=today).data():
                why = f" ({c['why']})" if c.get('why') else ''
                lines.append(f"- ★이미 끝난 일★ {c['n']}{why} — 다시 잡혔다는 말 없이는 "
                             '진행 중으로 언급 금지')
            # 관계 종결은 날짜 유도 불가(occurs 없음) — 창 없이 최신순 LIMIT 3
            for c in s.run(
                'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                'WHERE r.valid_to IS NOT NULL AND p.suppressed IS NULL '
                'RETURN p.name AS n, r.relation AS rel '
                'ORDER BY r.valid_to DESC LIMIT 3',
                    uid=user_id).data():
                lines.append(f"- ★{c['n']}은 이제 {c['rel']} 아님★ (지난 인연 — "
                             '현재 관계로 언급 금지)')
            # ① 다가오는 일 — D-day (occurs_start 기준, 진행 중 판정은 occurs_end)
            for c in s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL AND e.suppressed IS NULL AND ('
                '  (e.occurs_start IS NOT NULL AND e.occurs_start >= $today) OR '
                '  (e.occurs_end IS NOT NULL AND e.occurs_start <= $today '
                '   AND e.occurs_end >= $today)) '
                'OPTIONAL MATCH (e)-[:INVOLVES]->(p:Person) '
                'RETURN e.name AS n, e.occurs_start AS ds, e.occurs_end AS de, '
                '       collect(DISTINCT p.name) AS ppl '
                'ORDER BY e.occurs_start ASC LIMIT 3',
                    uid=user_id, today=today).data():
                try:
                    dday = (datetime.date.fromisoformat(c['ds']) - _today()).days
                except Exception:
                    continue   # 오염된 날짜(추출 불량)는 이 항목만 건너뜀 — 회상 전체 사망 금지
                when = '진행 중' if dday < 0 or (
                    c['ds'] <= today and (c['de'] or '') >= today and dday <= 0) else (
                    '오늘' if dday == 0 else f'D-{dday}')
                span = f"{c['ds']}~{c['de']}" if c.get('de') else c['ds']
                w = ' · 함께: ' + ', '.join(x for x in c['ppl'] if x) if any(c['ppl']) else ''
                lines.append(f"- 다가오는 일: {c['n']} ({span}, {when}){w}")
            # ② [요즘 흐름] — 감정 딸린 최근 사건 나열 (리플렉션 대체: 해석은 응답 LLM이 즉석)
            flow = s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                'RETURN e.name AS n, e.top_emotion AS emo, e.cause AS c '
                'ORDER BY coalesce(e.salience,1.0) DESC, e.created_at DESC LIMIT $lim',
                uid=user_id, lim=limit).data()
            if flow:
                lines.append('[요즘 흐름]')
                for e in flow:
                    p = [e['n']]
                    if e.get('emo'):
                        p.append(f"· 감정:{e['emo']}")
                    if e.get('c'):
                        p.append(f"· 이유:{e['c']}")
                    lines.append('- ' + ' '.join(p))
            n_before_search = len(lines)   # ③ 채널들이 빈손인지 판정용 (③-1 게이트)
            matched_names = []             # 질문이 가리킨 사건들 — ⑤ 인과 사슬의 출발점
            # ③-0 질문 벡터 직접 검색 (0.33) — 표현이 달라도 의미로 찾음 (임베딩 복원 7/18)
            if (message or '').strip():
                try:
                    from chat import embedder
                    if embedder.is_available():
                        for r in s.run(
                            f'CALL db.index.vector.queryNodes("{VEC_INDEX}", 8, $vec) '
                            'YIELD node, score '
                            'WHERE node.uid=$uid AND score>=$min '
                            '  AND coalesce(node.suppressed,false)=false '
                            'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(node) '
                            'WHERE h.valid_to IS NULL '
                            'RETURN node.key AS k, node.name AS n, '
                            '       node.top_emotion AS emo, score '
                            'ORDER BY score DESC LIMIT 4',
                            vec=embedder.embed(message), uid=user_id,
                                min=VEC_RECALL_MIN).data():
                            line = (f"- (연상) {r['n']}"
                                    + (f" · 감정:{r['emo']}" if r.get('emo') else ''))
                            if line not in lines:
                                lines.append(line)
                            matched_names.append(r['n'])
                            s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->'
                                  '(e:Event {uid:$uid, key:$k}) '
                                  'SET e.recall_count=coalesce(e.recall_count,0)+1',
                                  uid=user_id, k=r['k'])
                except Exception:
                    pass
            # ③ 언급 기반 직접 검색 (결정 매칭 — 벡터와 상보)
            if (message or '').strip():
                mnorm = _norm(message)
                asked = s.run(
                    'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                    'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                    '  AND size(e.key) >= 2 AND $mn CONTAINS e.key '
                    'RETURN e.key AS k, e.name AS n, e.top_emotion AS emo LIMIT 4',
                    uid=user_id, mn=mnorm).data()
                seen = {l for l in lines}
                for r in asked:
                    line = f"- (언급) {r['n']}" + (f" · 감정:{r['emo']}" if r.get('emo') else '')
                    matched_names.append(r['n'])
                    if line not in seen:
                        lines.append(line)
                    # 재강화: 언급된 기억만 recall_count+1
                    s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->'
                          '(e:Event {uid:$uid, key:$k}) '
                          'SET e.recall_count=coalesce(e.recall_count,0)+1',
                          uid=user_id, k=r['k'])
            # ③-1 LLM 연상 폴백 (임베딩 미사용 구성 전용, 2026-07-18) — 결정 매칭이
            # 빈손일 때만 1회. '복권'↔'로또'처럼 단어가 안 겹치는 질문의 의미 연결을
            # 프롬프트로 대체 (P01-off 실측: 흐름 상위 6위 밖 기억은 도달 경로 전무).
            if (message or '').strip() and len(lines) == n_before_search:
                try:
                    from chat import embedder as _emb
                    emb_on = _emb.is_available()
                except Exception:
                    emb_on = False
                if not emb_on:
                    try:
                        names = [r['n'] for r in s.run(
                            'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                            'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                            'RETURN e.name AS n LIMIT 20', uid=user_id).data() if r['n']]
                        if names:
                            from ai.agents.llm import get_llm
                            resp = get_llm(temperature=0, max_tokens=40).invoke([
                                ('system',
                                 '질문이 가리키는 기억이 목록에 있는지 판정하라. 표현이 '
                                 "달라도 같은 일을 가리킬 수 있다('복권 맞음'과 '로또 당첨'). "
                                 "있으면 그 이름만 목록 표기 그대로, 없으면 '없음'. 다른 말 금지."),
                                ('user', f'질문: {message}\n목록: '
                                         + json.dumps(names, ensure_ascii=False)),
                            ])
                            pick = (resp.content or '').strip().strip('"\'')
                            if pick and pick != '없음' and pick in names:
                                lines.append(f'- (연상) {pick}')
                                matched_names.append(pick)
                                print(f'[graph_memory_v2_base] LLM 연상: → {pick}')
                    except Exception:
                        pass
            # ⑤ 인과 사슬 (2026-07-19 배선 — 게이트 통과 후 옵션 이행) — '왜/때문/이유'
            # 질문일 때만, 질문이 가리킨 사건의 원인 사슬(BECAUSE_OF *1..5)을 주입.
            # 엣지는 사용자가 명시한 인과("~때문에")로만 생성되므로 사슬 자체가 접지돼 있다.
            if _causal_question(message):
                # 후보: 질문이 직접 가리킨 사건 우선, 없으면 [요즘 흐름] 상위 사건
                # ("왜 우울하지?"의 '우울함'은 흐름에만 있는 경우가 흔함)
                cands = matched_names or [e['n'] for e in (flow or [])[:3] if e.get('n')]
                for cn in cands[:3]:
                    try:
                        chain = root_cause(user_id, cn)
                    except Exception:
                        chain = ''
                    if chain and '←' in chain:
                        lines.append(f'- 인과 사슬(사용자가 직접 말한 이유만): {chain}')
                        print(f'[graph_memory_v2_base] 인과 사슬 주입: {chain}')
                        break
            # ④ 인물 (유효 관계) / 취향
            cur = s.run(
                'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                'WHERE r.valid_to IS NULL AND p.suppressed IS NULL '
                'RETURN DISTINCT p.name AS n, r.relation AS rel LIMIT 10',
                uid=user_id).data()
            if cur:
                lines.append('- 인물: ' + ', '.join(
                    f"{x['n']}({x['rel']})" for x in cur if x['n']))
            pf = s.run('MATCH (u:User {uid:$uid})-[r:PREFERS]->(t:Topic) '
                       "WHERE r.valid_to IS NULL AND r.polarity<>'오' "
                       'RETURN collect(DISTINCT t.name) AS xs', uid=user_id).single()
            if pf and pf['xs']:
                lines.append('- 취향: ' + ', '.join(pf['xs']))
        return '\n'.join(lines)
    except Exception as e:
        print(f'[graph_memory_v2_base] 회상 실패: {e}')
        return ''


def upcoming(user_id, days=None):
    """다가오는 일정만 (opener 재료 — v1 upcoming(days=) 시그니처 호환)."""
    if not user_id or not is_enabled():
        return ''
    try:
        until = ((_today() + datetime.timedelta(days=int(days))).isoformat()
                 if days else None)
        with _get_driver().session() as s:
            rows = s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                '  AND e.occurs_start IS NOT NULL AND e.occurs_start >= $today '
                '  AND ($until IS NULL OR e.occurs_start <= $until) '
                'RETURN e.name AS n, e.occurs_start AS d ORDER BY d ASC LIMIT 3',
                uid=user_id, today=_today_s(), until=until).data()
        out = []
        for r in rows:
            try:
                dd = (datetime.date.fromisoformat(r['d']) - _today()).days
            except Exception:
                continue
            out.append(f"{r['n']} ({r['d']}, {'오늘' if dd == 0 else f'D-{dd}'})")
        return '\n'.join('- ' + x for x in out)
    except Exception:
        return ''


def panel_summary(user_id):
    """기억 패널 (UI #3, 2026-07-20) — 좌측 패널 '기억하는 것' 카드용 구조화 요약.
    recall과 달리 LLM 무관·결정적 — 그래프 상태를 그대로 JSON으로 (프롬프트 오염 없음).
    소비자: views.memory_panel → 프론트 ChatView 좌측 패널."""
    empty = {'upcoming': [], 'prefs': [], 'people': [], 'recent': []}
    if not user_id or not is_enabled():
        return empty
    try:
        today = _today()
        with _get_driver().session() as s:
            up = s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                '  AND e.occurs_start IS NOT NULL AND e.occurs_start >= $today '
                'RETURN e.name AS n, e.occurs_start AS d ORDER BY d ASC LIMIT 4',
                uid=user_id, today=today.isoformat()).data()
            prefs = s.run(
                'MATCH (u:User {uid:$uid})-[r:PREFERS]->(t:Topic) '
                'WHERE r.valid_to IS NULL '
                'RETURN t.name AS n, r.polarity AS p '
                'ORDER BY r.created_at DESC LIMIT 3', uid=user_id).data()
            people = s.run(
                'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                'WHERE r.valid_to IS NULL AND p.suppressed IS NULL '
                'RETURN DISTINCT p.name AS n, r.relation AS rel LIMIT 3',
                uid=user_id).data()
            recent = s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                '  AND (e.occurs_start IS NULL OR e.occurs_start < $today) '
                'RETURN e.name AS n ORDER BY h.created_at DESC LIMIT 3',
                uid=user_id, today=today.isoformat()).data()
        out = {'upcoming': [], 'prefs': [], 'people': [], 'recent': []}
        for r in up:
            try:
                dd = (datetime.date.fromisoformat(r['d']) - today).days
            except Exception:
                continue
            out['upcoming'].append({'name': r['n'], 'date': r['d'], 'dday': dd})
        out['prefs'] = [{'topic': r['n'], 'polarity': r.get('p') or '호'}
                        for r in prefs if r.get('n')]
        out['people'] = [{'name': r['n'], 'relation': r.get('rel') or ''}
                         for r in people if r.get('n')]
        out['recent'] = [r['n'] for r in recent if r.get('n')]
        return out
    except Exception as e:
        print(f'[graph_memory_v2_base] 패널 요약 실패: {e}')
        return empty


# ── 미해결 추적 (open loop) — 종료일 기준 (C1: 기간 사건은 끝나야 '지남') ──
def open_loops(user_id):
    if not user_id or not is_enabled():
        return []
    try:
        today = _today()
        cutoff = (today - datetime.timedelta(days=OPENLOOP_MAX_AGE)).isoformat()
        with _get_driver().session() as s:
            rows = s.run(
                'MATCH (u:User {uid:$uid})-[h:HAS_EVENT]->(e:Event) '
                'WHERE h.valid_to IS NULL AND e.suppressed IS NULL '
                '  AND coalesce(e.occurs_end, e.occurs_start) < $today '
                '  AND coalesce(e.occurs_end, e.occurs_start) >= $cutoff '
                '  AND coalesce(e.followup_asked,false) = false '
                'RETURN e.key AS key, e.name AS name, '
                '       coalesce(e.occurs_end, e.occurs_start) AS date '
                'ORDER BY date DESC LIMIT 3',
                uid=user_id, today=today.isoformat(), cutoff=cutoff).data()
        return [{'name': r['name'], 'date': r['date'], 'key': r['key']} for r in rows]
    except Exception:
        return []


def mark_followed_up(user_id, key):
    if not user_id or not is_enabled():
        return
    try:
        with _get_driver().session() as s:
            s.run('MATCH (u:User {uid:$uid})-[:HAS_EVENT]->(e:Event {uid:$uid, key:$key}) '
                  'SET e.followup_asked=true', uid=user_id, key=key)
    except Exception:
        pass


# ── 관계 변화 감지 ─────────────────────────────────────────────
def relationship_changes(user_id, days=None):
    if not user_id or not is_enabled():
        return []
    days = days or RELCHANGE_WINDOW
    try:
        since = (_today() - datetime.timedelta(days=days)).isoformat()
        with _get_driver().session() as s:
            rows = s.run(
                'MATCH (u:User {uid:$uid})-[r:RELATES_TO]->(p:Person) '
                'WHERE r.valid_to IS NOT NULL AND r.valid_to >= $since '
                '  AND p.suppressed IS NULL '
                'RETURN p.name AS name, r.relation AS rel, r.valid_to AS ended, '
                '       r.end_reason AS reason ORDER BY r.valid_to DESC LIMIT 3',
                uid=user_id, since=since).data()
        return [{'name': r['name'], 'relation': r['rel'],
                 'ended': r['ended'], 'reason': r['reason']} for r in rows]
    except Exception:
        return []


# ── 오랜만 인사 ────────────────────────────────────────────────
def absence_days(user_id):
    if not user_id or not is_enabled():
        return -1
    try:
        with _get_driver().session() as s:
            row = s.run('MATCH (ep:Episode {uid:$uid}) '
                        'RETURN max(ep.created_at) AS last', uid=user_id).single()
        if not row or not row['last']:
            return -1
        last = datetime.date.fromisoformat(row['last'][:10])
        return (_today() - last).days
    except Exception:
        return -1


def absence_opener(user_id):
    gap = absence_days(user_id)
    if gap < ABSENCE_MIN:
        return ''
    loops = open_loops(user_id)
    if loops:
        return f"오랜만이야! 저번에 '{loops[0]['name']}' 얘기했었는데 어떻게 됐어?"
    return '오랜만이야, 그동안 어떻게 지냈어?'


# ── 인과 추적 (BECAUSE_OF) — §8-4-2: key↔key 매칭으로 수정 ────
def root_cause(user_id, event_name):
    if not user_id or not is_enabled():
        return ''
    depth = int(os.environ.get('MEM_CAUSE_DEPTH', '5'))
    try:
        with _get_driver().session() as s:
            row = s.run(
                'MATCH (e:Event {uid:$uid}) WHERE e.key CONTAINS $k '
                f'MATCH path=(e)-[:BECAUSE_OF*1..{depth}]->(root:Event) '
                'WHERE NOT (root)-[:BECAUSE_OF]->(:Event) '
                'RETURN [n IN nodes(path)|n.name] AS chain '
                'ORDER BY length(path) DESC LIMIT 1',
                uid=user_id, k=_norm(event_name)).single()
            return ' ← '.join(row['chain']) if row and row['chain'] else ''
    except Exception:
        return ''

# -*- coding: utf-8 -*-
"""임베딩 모델 비교 벤치 (2026-07-13) — 감정 모델 실험1과 같은 원칙: 찍지 말고 실측.

과제: 실사용과 동일 — "기억 이름 저장소에서 패러프레이즈 질문으로 정답 기억 찾기"
      정답 질문은 일부러 기억 이름과 단어가 안 겹치게 작성 (키워드로는 0점인 과제)

지표: ① top-1 정확도  ② 마진(정답 − 최고 오답: 클수록 임계값 잡기 쉬움)
      ③ 무관 질문 최고점(이보다 임계값이 높아야 헛소환 없음)  ④ 속도
      → VEC_RECALL_MIN 자동 제안 (무관 최고점과 정답 최저점 사이)

사용: python manage.py memory_embed_bench                 # 4모델 전부
      python manage.py memory_embed_bench --models jhgan/ko-sroberta-multitask openai/text-embedding-3-small
"""
import time

from django.core.management.base import BaseCommand

# ── 기억 저장소 (20개 — 실제 그래프에 쌓이는 형태의 이벤트 이름) ──────────
MEMORIES = [
    '로또 5만원 당첨', '이직 고민', '민수와 부산 여행', '지은이 생일 파티',
    '정보처리기사 시험 준비', '헬스 PT 등록', '회사 발표 잘 마침', '치과 사랑니 발치',
    '편의점 알바 그만둠', '엄마랑 김장', '고양이 츄르 사줌', '자격증 학원 등록',
    '친구랑 노래방', '월급 인상 협상 성공', '독감 걸려서 병원', '새 노트북 구매',
    '운전면허 필기 합격', '동아리 MT 참석', '층간소음 항의', '다이어트 시작',
]

# ── 질문 40개 (기억당 2개) — 단어 겹침 최소화한 패러프레이즈 ─────────────
QUERIES = [  # (질문, 정답 기억 인덱스)
    ('복권 맞았던 거 기억나?', 0), ('저번에 돈 당첨된 거 있잖아', 0),
    ('회사 옮기려던 거 어떻게 됐어?', 1), ('직장 바꿀까 하던 얘기 기억해?', 1),
    ('바다 보러 놀러갔던 거 기억나?', 2), ('민수랑 여행 갔던 얘기', 2),
    ('걔 생일 챙겨줬던 날 기억해?', 3), ('지은이 축하 파티 했잖아', 3),
    ('IT 자격증 공부하던 거 있잖아', 4), ('기사 시험 준비 어떻게 됐어?', 4),
    ('운동 트레이너 끊었던 거 기억나?', 5), ('헬스장 개인 레슨 시작한 거', 5),
    ('프레젠테이션 성공했던 날 기억해?', 6), ('발표 잘 끝냈다고 했잖아', 6),
    ('이빨 뽑았던 거 기억나?', 7), ('치과에서 수술한 거 있잖아', 7),
    ('편의점 일 그만둔 거 기억하지?', 8), ('알바 관뒀다고 했었잖아', 8),
    ('김치 담그러 갔던 거 기억나?', 9), ('엄마랑 김장했잖아', 9),
    ('고양이 간식 사준 거 기억해?', 10), ('츄르 사줬다고 했잖아', 10),
    ('학원 새로 다니기 시작한 거', 11), ('자격증 공부하러 등록했잖아', 11),
    ('친구랑 노래 부르러 갔던 날', 12), ('노래방 갔던 거 기억나?', 12),
    ('연봉 올려달라고 한 거 성공했잖아', 13), ('월급 협상 얘기 기억해?', 13),
    ('아파서 병원 갔던 거 기억나?', 14), ('독감 걸렸을 때 있잖아', 14),
    ('컴퓨터 새로 산 거 기억해?', 15), ('노트북 장만했다고 했잖아', 15),
    ('면허 시험 붙었던 거 기억나?', 16), ('운전 필기 합격했잖아', 16),
    ('동아리 사람들이랑 놀러간 거', 17), ('MT 갔던 얘기 기억해?', 17),
    ('윗집 시끄러워서 따진 거 기억나?', 18), ('층간소음 때문에 항의했잖아', 18),
    ('살 빼기로 한 거 어떻게 됐어?', 19), ('다이어트 시작했다고 했잖아', 19),
]

# ── 무관 질문 8개 — 아무 기억도 소환되면 안 됨 (임계값 하한 재료) ────────
NO_MATCH = [
    '오늘 날씨 어때?', '점심 뭐 먹을까?', '요즘 유행하는 드라마 뭐야?',
    '내일 몇 시에 일어날까?', '주말에 뭐하지?', '커피가 좋아 차가 좋아?',
    '너는 이름이 뭐야?', '심심한데 재밌는 얘기 해줘',
]

DEFAULT_MODELS = [
    'jhgan/ko-sroberta-multitask',
    'BM-K/KoSimCSE-roberta-multitask',
    'intfloat/multilingual-e5-small',
    'openai/text-embedding-3-small',
]


def _encode_batch(model_name, texts, is_query):
    """모델별 배치 임베딩 (정규화 포함) → list[list[float]]"""
    if model_name.startswith('openai/'):
        from openai import OpenAI
        r = OpenAI().embeddings.create(model=model_name.split('/', 1)[-1], input=texts)
        return [d.embedding for d in r.data]
    from sentence_transformers import SentenceTransformer
    if not hasattr(_encode_batch, '_cache'):
        _encode_batch._cache = {}
    if model_name not in _encode_batch._cache:
        _encode_batch._cache[model_name] = SentenceTransformer(model_name)
    m = _encode_batch._cache[model_name]
    if 'e5' in model_name.lower():   # e5 규약
        prefix = 'query: ' if is_query else 'passage: '
        texts = [prefix + t for t in texts]
    return [v.tolist() for v in m.encode(texts, normalize_embeddings=True)]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


class Command(BaseCommand):
    help = '임베딩 모델 4종 비교 — top-1 정확도·마진·무관질문 방어·속도·임계값 제안'

    def add_arguments(self, p):
        p.add_argument('--models', nargs='*', default=DEFAULT_MODELS)

    def handle(self, *args, **opts):
        w = self.stdout.write
        w(f'기억 {len(MEMORIES)}개 / 질문 {len(QUERIES)}개 / 무관 {len(NO_MATCH)}개\n')
        results = []
        for name in opts['models']:
            w(f'━━ {name}')
            try:
                t0 = time.time()
                mem_v = _encode_batch(name, MEMORIES, is_query=False)
                q_v = _encode_batch(name, QUERIES and [q for q, _ in QUERIES], is_query=True)
                nm_v = _encode_batch(name, NO_MATCH, is_query=True)
                elapsed = time.time() - t0
            except Exception as e:
                w(f'   ✗ 로드/추론 실패: {e}\n')
                continue

            correct, margins, pos_scores, fails = 0, [], [], []
            for (q, gold), qv in zip(QUERIES, q_v):
                scores = sorted(((_dot(qv, mv), i) for i, mv in enumerate(mem_v)), reverse=True)
                top_s, top_i = scores[0]
                if top_i == gold:
                    correct += 1
                    pos_scores.append(top_s)
                    margins.append(top_s - scores[1][0])   # 정답 − 2등
                else:
                    fails.append(f'"{q}" → {MEMORIES[top_i]} ({top_s:.2f}) ≠ {MEMORIES[gold]}')
            nm_max = max(max(_dot(qv, mv) for mv in mem_v) for qv in nm_v)

            acc = correct / len(QUERIES)
            m_avg = sum(margins) / len(margins) if margins else 0
            p_min = min(pos_scores) if pos_scores else 0
            # 임계값 제안: 무관 최고점과 정답 최저점 사이 (겹치면 경고)
            thr = round((nm_max + p_min) / 2, 2) if p_min > nm_max else None
            w(f'   top-1 {acc:.0%} ({correct}/{len(QUERIES)}) · 마진 {m_avg:.3f} · '
              f'정답최저 {p_min:.2f} · 무관최고 {nm_max:.2f} · {elapsed:.1f}s')
            w(f'   → VEC_RECALL_MIN 제안: {thr if thr else "⚠ 분리 불가(무관≥정답) — 임계값으로 헛소환 못 막음"}')
            for f in fails[:5]:
                w(f'   ✗ {f}')
            w('')
            results.append((acc, m_avg, name, thr))

        if results:
            results.sort(reverse=True)
            w('═══ 종합 (정확도 → 마진 순) ═══')
            for acc, m, name, thr in results:
                w(f'  {acc:.0%}  마진 {m:.3f}  thr {thr}  {name}')
            best = results[0]
            w(f'\n채택 후보: {best[2]}')
            w(f'적용: .env에  EMBED_MODEL={best[2]}  /  MEM_VEC_RECALL_MIN={best[3]}  (다이얼: memory_config)')

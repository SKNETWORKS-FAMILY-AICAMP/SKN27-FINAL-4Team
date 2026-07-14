# -*- coding: utf-8 -*-
"""리플렉션 군집 임계값(θ) 벤치 (2026-07-13) — REFLECT_SIM_MIN 실측 결정.

과제: 테마를 알고 있는 가짜 기억 세트를 계층 군집으로 나눠보고,
      정답 분할(회사·가족·운동은 각각 뭉치고, 잡음은 어디에도 안 붙음)을
      재현하는 θ 구간을 찾는다. VEC_RECALL_MIN(0.33)을 정한 방식과 동일.

채점: 쌍 단위 F1 — "같은 테마 쌍은 같은 덩어리에 / 다른 테마 쌍은 다른 덩어리에"
      + 통찰 규칙(증거 3+) 적용 후 통찰 개수가 정답(3개)인지

사용: python manage.py memory_reflect_bench
"""
from itertools import combinations

from django.core.management.base import BaseCommand

# 정답을 아는 시험지 — (기억 이름, 테마) / 잡음은 테마 None (어디에도 안 붙어야 함)
# 추출기 산출물 스타일(5~15자 요약형)로 작성 — 실제 저장되는 이름 분포와 같아야
# θ가 실전에서 맞음 (1차 보정을 긴 문장으로 재서 실전에서 뭉개짐 → R01 0/3의 교훈, 2026-07-13)
FIXTURE = [
    ('이직 고민', '회사'), ('상사한테 혼남', '회사'),
    ('야근 연속', '회사'), ('회사 발표 준비', '회사'),
    ('엄마랑 병원', '가족'), ('엄마랑 김장', '가족'), ('부모님 결혼기념일', '가족'),
    ('클라이밍 시작', '운동'), ('헬스 PT 등록', '운동'), ('다이어트 시작', '운동'),
    ('로또 5만원 당첨', None), ('새 노트북 구매', None), ('친구랑 노래방', None),
]

THETAS = [round(0.15 + 0.01 * i, 2) for i in range(16)]   # 0.15 ~ 0.30 정밀 (1차 스윕에서 정답이 0.2 한 점 → 구간 폭 확인)
MIN_EVIDENCE = 3


def _cluster(vecs, theta):
    """코사인 거리 (1-θ) 기준 계층 군집 — 본체와 동일 로직"""
    from sklearn.cluster import AgglomerativeClustering
    import numpy as np
    X = np.array(vecs)
    model = AgglomerativeClustering(
        n_clusters=None, distance_threshold=1.0 - theta,
        metric='cosine', linkage='average')
    return model.fit_predict(X)


class Command(BaseCommand):
    help = '리플렉션 군집 임계값(θ) 스윕 — 정답 테마 재현 F1 측정'

    def handle(self, *args, **opts):
        w = self.stdout.write
        from chat import embedder
        if not embedder.is_available():
            self.stderr.write('임베딩 모델 없음 — sentence-transformers 설치 확인')
            return
        names = [n for n, _ in FIXTURE]
        gold = [t for _, t in FIXTURE]
        vecs = [embedder.embed(n) for n in names]
        if any(v is None for v in vecs):
            self.stderr.write('임베딩 실패')
            return

        w(f'기억 {len(names)}개 (테마 3 + 잡음 3) / θ 스윕 {THETAS[0]}~{THETAS[-1]}\n')
        w(f'{"θ":>5} {"쌍F1":>6} {"통찰수":>4} {"판정":>4}   덩어리 내용')
        best = []
        for th in THETAS:
            labels = _cluster(vecs, th)
            # 쌍 단위 채점: 같은 테마(None 제외) 쌍 = 같은 라벨이어야 정답
            tp = fp = fn = 0
            for i, j in combinations(range(len(names)), 2):
                same_gold = gold[i] is not None and gold[i] == gold[j]
                same_pred = labels[i] == labels[j]
                if same_pred and same_gold: tp += 1
                elif same_pred and not same_gold: fp += 1
                elif not same_pred and same_gold: fn += 1
            f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0
            # 통찰 규칙 적용: 증거 3+ 덩어리 수
            from collections import Counter
            sizes = Counter(labels)
            n_insights = sum(1 for c in sizes.values() if c >= MIN_EVIDENCE)
            ok = f1 == 1.0 and n_insights == 3
            mark = '✓' if ok else '✗'
            if ok:
                best.append(th)
            # 덩어리 미리보기 (2개 이상만)
            groups = {}
            for n, l in zip(names, labels):
                groups.setdefault(l, []).append(n[:6])
            preview = ' | '.join('·'.join(g) for g in groups.values() if len(g) >= 2)
            w(f'{th:>5} {f1:>6.2f} {n_insights:>4} {mark:>4}   {preview[:70]}')

        w('')
        if best:
            mid = best[len(best) // 2]
            w(f'정답 재현 구간: {best[0]} ~ {best[-1]}  →  REFLECT_SIM_MIN = {mid} (구간 중앙값) 제안')
        else:
            w('⚠ 완전 재현 θ 없음 — F1 최고 지점 주변 미세 스윕 필요 (0.025 간격)')

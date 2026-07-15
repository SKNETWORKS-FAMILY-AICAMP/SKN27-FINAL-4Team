# -*- coding: utf-8 -*-
"""만료(supersede) 벡터 매칭 임계값 벤치 (2026-07-13) — EXPIRE_VEC_MIN 실측.

배경: 만료 매칭이 문자열 3단(정규화→포함→토큰)이라 "보기로 한 거 파토났어"가
"영화 보기"를 못 찾음. 4단계로 벡터 폴백을 붙이되, 임계값은 실측으로.

오폭이 미스보다 나쁘다: 엉뚱한 기억을 만료시키면 재앙이므로
"무관 만료어의 최고점 < 임계값 < 정답 쌍의 최저점" 분리 확인이 목적.

사용: python manage.py memory_expire_bench
"""
from django.core.management.base import BaseCommand

# 저장돼 있는 사건 이름들 (추출기 스타일)
STORED = [
    '영화 보기', '제주도 여행 예정', '편의점 알바 시작', '헬스 PT 등록',
    '지은이 생일 파티', '정보처리기사 시험', '회사 발표 준비', '로또 5만원 당첨',
    '엄마랑 병원 방문', '이직 고민',
]

# 정답 쌍: 만료 지시어(추출기가 expired.name으로 낼 법한 표현, 글자 겹침 최소) ↔ 표적
POSITIVE = [
    ('태영이랑 보기로 한 거', '영화 보기'),
    ('바다 놀러가기로 한 거', '제주도 여행 예정'),
    ('가게 일', '편의점 알바 시작'),
    ('운동 레슨', '헬스 PT 등록'),
    ('걔 축하 모임', '지은이 생일 파티'),
    ('자격증 준비', '정보처리기사 시험'),
    ('회사에서 하는 프레젠테이션', '회사 발표 준비'),
    ('회사 옮기려던 거', '이직 고민'),
]

# 무관 만료어: 저장된 어떤 것과도 매칭되면 안 됨 (오폭 방어선의 재료)
NO_MATCH = [
    '동창회', '피아노 학원', '치과 예약', '골프 모임', '집들이', '독서 모임',
]


class Command(BaseCommand):
    help = '만료 벡터 매칭 임계값 스윕 — 오폭 방어선 실측'

    def handle(self, *args, **opts):
        w = self.stdout.write
        from chat import embedder
        if not embedder.is_available():
            self.stderr.write('임베딩 모델 없음')
            return
        sv = {n: embedder.embed(n) for n in STORED}

        def top1(query):
            qv = embedder.embed(query)
            scored = sorted(((sum(a * b for a, b in zip(qv, v)), n) for n, v in sv.items()),
                            reverse=True)
            return scored[0]   # (score, name)

        w(f'저장 {len(STORED)} / 정답 쌍 {len(POSITIVE)} / 무관 {len(NO_MATCH)}\n')
        w('── 정답 쌍 (top-1이 표적인가 + 점수) ──')
        pos_scores, misses = [], []
        for q, gold in POSITIVE:
            s, n = top1(q)
            ok = n == gold
            if ok:
                pos_scores.append(s)
            else:
                misses.append(q)
            w(f'  {"✓" if ok else "✗"} "{q}" → {n} ({s:.3f})' + ('' if ok else f'  [정답: {gold}]'))
        w('── 무관 만료어 (전부 임계값 아래여야 — 오폭 방어) ──')
        neg_max = 0.0
        for q in NO_MATCH:
            s, n = top1(q)
            neg_max = max(neg_max, s)
            w(f'    "{q}" → {n} ({s:.3f})')

        w('')
        if misses:
            w(f'⚠ top-1 미스 {len(misses)}건 — 이 쌍들은 벡터로도 못 찾음 (임계값과 무관한 한계)')
        p_min = min(pos_scores) if pos_scores else 0
        w(f'정답 최저 {p_min:.3f} vs 무관 최고 {neg_max:.3f}')
        if p_min > neg_max:
            thr = round((p_min + neg_max) / 2, 2)
            w(f'→ 분리 성립. EXPIRE_VEC_MIN = {thr} 제안')
            w(f'  (보수 운용 원하면 {round(neg_max + (p_min - neg_max) * 0.7, 2)} — 오폭 여유 더 큼)')
        else:
            w('→ ⚠ 분리 불가 — 겹치는 쌍 제외하고 재검토 필요 (오폭 위험이 이득보다 큼)')

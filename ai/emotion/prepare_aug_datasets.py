# -*- coding: utf-8 -*-
"""실험 ② 데이터 추가 ablation용 — 보조 데이터셋 정제 스크립트.

AI Hub 데이터 재배포 금지 → 생성물(aug_*.jsonl)은 repo 미포함, 이 스크립트만 배포.
출력 형식은 학습 정제본과 동일: {"text": ..., "emotion": 기쁨|슬픔|분노|일반}

① 음성 대화 데이터셋 (감정 분류를 위한 대화 음성, 4·5차년도 CSV)
   - 어노테이터 5명 감정 투표 → 3표 이상 합의된 발화만 채택 (라벨 품질 우선)
   - 7감정 → 4모드: happiness→기쁨, sadness→슬픔, angry·disgust·fear→분노,
     neutral·surprise→일반  (감성대화의 불안→분노, 당황→일반 규칙과 일관)

② 웰니스 대화 스크립트 (xlsx)
   - '감정/*' 카테고리의 유저 발화만 사용 (증상/배경 등은 감정 라벨로 부적합)
   - 하위 카테고리명 키워드로 4모드 매핑, 모호한 카테고리는 제외
   - ⚠ 기쁨이 거의 없어 불균형 심화 가능 — 채택은 실험 결과로 판단

사용법:
  python ai/emotion/prepare_aug_datasets.py \
      --voice-dir "<경로>/감정 분류를 위한 대화 음성 데이터셋" \
      --wellness "<경로>/웰니스 대화 스크립트 데이터셋/웰니스_대화_스크립트_데이터셋.xlsx" \
      --out-dir data
"""
import argparse
import json
import os
import re
from collections import Counter

VOICE_FILES = ['4차년도.csv', '5차년도.csv', '5차년도_2차.csv']
VOICE_EMO_COLS = ['1번 감정', '2번 감정', '3번 감정', '4번 감정', '5번 감정']
VOICE_TO_4 = {
    'happiness': '기쁨', 'sadness': '슬픔', 'angry': '분노',
    'disgust': '분노', 'fear': '분노', 'neutral': '일반', 'surprise': '일반',
}
MIN_VOTES = 3   # 5명 중 3표 이상 합의만 채택

# 웰니스 '감정/하위' → 4모드 (키워드 포함 매칭 · 모호하면 미매핑=제외)
WELLNESS_RULES = [
    ('기쁨', ['기쁨', '행복', '즐거움', '만족', '설렘']),
    ('슬픔', ['힘듦', '우울', '눈물', '괴로움', '슬픔', '외로움', '후회', '허무',
             '상실', '자살충동', '무기력', '서러움', '그리움', '비관']),
    ('분노', ['짜증', '화', '분노', '불안', '걱정', '억울', '스트레스', '답답',
             '두려움', '공포', '초조']),
]


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', str(s).replace('\xa0', ' ')).strip()


def build_voice(voice_dir: str) -> list[dict]:
    import pandas as pd
    frames = [pd.read_csv(os.path.join(voice_dir, f), encoding='cp949')
              for f in VOICE_FILES]
    df = pd.concat(frames, ignore_index=True)
    rows, dropped = [], 0
    for _, r in df.iterrows():
        votes = Counter(
            str(r[c]).strip().lower() for c in VOICE_EMO_COLS if str(r[c]).strip())
        label, n = votes.most_common(1)[0]
        if n < MIN_VOTES or label not in VOICE_TO_4:
            dropped += 1
            continue
        text = normalize(r['발화문'])
        if len(text) >= 2:
            rows.append({'text': text, 'emotion': VOICE_TO_4[label]})
    print(f'[음성] {len(df):,}건 → 채택 {len(rows):,} / 합의 미달·무효 {dropped:,}')
    return rows


def build_wellness(xlsx_path: str) -> list[dict]:
    import pandas as pd
    df = pd.read_excel(xlsx_path)
    rows, skipped = [], Counter()
    emo_df = df[df['구분'].astype(str).str.startswith('감정')]
    for _, r in emo_df.iterrows():
        sub = str(r['구분']).split('/', 1)[-1]
        label = next((emo for emo, kws in WELLNESS_RULES
                      if any(k in sub for k in kws)), None)
        if label is None:
            skipped[sub] += 1
            continue
        text = normalize(r['유저'])
        if len(text) >= 2:
            rows.append({'text': text, 'emotion': label})
    print(f"[웰니스] 감정/* {len(emo_df):,}건 → 채택 {len(rows):,} / 미매핑 하위 {len(skipped)}종 {sum(skipped.values())}건")
    return rows


def save(rows: list[dict], path: str):
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    dist = Counter(r['emotion'] for r in rows)
    print(f'  → {path} ({len(rows):,}건, 분포 {dict(dist)})')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--voice-dir', required=False)
    ap.add_argument('--wellness', required=False)
    ap.add_argument('--out-dir', default='data')
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    if args.voice_dir:
        save(build_voice(args.voice_dir), os.path.join(args.out_dir, 'aug_voice.jsonl'))
    if args.wellness:
        save(build_wellness(args.wellness), os.path.join(args.out_dir, 'aug_wellness.jsonl'))

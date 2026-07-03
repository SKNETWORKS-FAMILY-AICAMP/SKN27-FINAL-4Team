# -*- coding: utf-8 -*-
"""AI Hub 감성대화 말뭉치 → 학습 정제본(kcelectra_train_clean.jsonl) 재생성 스크립트.

AI Hub 데이터는 이용약관상 재배포가 금지되어 정제본을 repo에 포함하지 않는다.
각자 AI Hub에서 원천을 내려받아 이 스크립트로 동일한 정제본을 재생성한다.
(재현성 검증: 원 정제본과 58,234건 순서·내용 100% 일치 — EDA_감정분류_김한솔.ipynb §0-2)

정제 규칙:
  1) Training → Validation 순으로 순회
  2) 각 대화에서 첫 사람 발화(HS01)와 감정 대분류(E코드 첫째 자리)만 추출
  3) 공백 정규화(\xa0 → 공백, 연속 공백 → 1개, 양끝 제거)
  4) 같은 문장이 다시 나오면 건너뜀 (최초 등장의 라벨 유지 — 완전 중복·라벨 상충 제거)

사용법:
  python ai/emotion/rebuild_clean_dataset.py \
      --raw "<원천 폴더>/018.감성대화" \
      --out data/kcelectra_train_clean.jsonl

원천 폴더 구조 (AI Hub 다운로드 기준):
  018.감성대화/
    Training_221115_add/라벨링데이터/_ext/감성대화말뭉치(최종데이터)_Training.json
    Validation_221115_add/라벨링데이터/_ext/감성대화말뭉치(최종데이터)_Validation.json
"""
import argparse
import json
import os
import re

E2NAME = {'1': '분노', '2': '슬픔', '3': '불안', '4': '상처', '5': '당황', '6': '기쁨'}

TRAIN_JSON = 'Training_221115_add/라벨링데이터/_ext/감성대화말뭉치(최종데이터)_Training.json'
VAL_JSON = 'Validation_221115_add/라벨링데이터/_ext/감성대화말뭉치(최종데이터)_Validation.json'


def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()


def rebuild(raw_dir: str, out_path: str) -> int:
    dialogs = []
    for rel in (TRAIN_JSON, VAL_JSON):
        path = os.path.join(raw_dir, rel)
        with open(path, encoding='utf-8') as f:
            dialogs += json.load(f)

    seen, rows = set(), []
    for d in dialogs:
        text = normalize(d['talk']['content'].get('HS01') or '')
        etype = d['profile']['emotion']['type']  # e.g. 'E18'
        emotion = E2NAME.get(etype[1])
        if not text or emotion is None or text in seen:
            continue
        seen.add(text)
        rows.append({'text': text, 'emotion': emotion})

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return len(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='AI Hub 감성대화 → 학습 정제본 재생성')
    ap.add_argument('--raw', required=True, help='원천 폴더 (018.감성대화)')
    ap.add_argument('--out', default='data/kcelectra_train_clean.jsonl')
    args = ap.parse_args()
    n = rebuild(args.raw, args.out)
    print(f'재생성 완료: {n:,}건 → {args.out}')
    if n != 58234:
        print(f'⚠ 기대치(58,234)와 다름 — 원천 버전(221115_add) 확인 필요')

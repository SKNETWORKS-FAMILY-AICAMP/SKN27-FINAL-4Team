# -*- coding: utf-8 -*-
"""확신도 게이트 임계값 보정 — 채팅체 150 평가셋으로 임계값 스윕.

실행: repo 루트에서  python ai/emotion/calibrate_gate.py
출력: 임계값별 (모델 채택률 / 채택분 정확도 / 저확신으로 넘어간 것 중 오답 비율)
→ "채택분 정확도는 높게, LLM 재분류 부담(1-채택률)은 낮게"의 균형점 선택.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ai.emotion.emotion_model import predict_emotion_with_confidence

EVAL = Path(__file__).resolve().parents[2] / 'data' / 'chat_eval_set.jsonl'

rows = [json.loads(l) for l in open(EVAL, encoding='utf-8') if l.strip()]
print(f'평가셋 {len(rows)}문장 추론 중...')

results = []   # (정답여부, 확신도)
for r in rows:
    label, conf = predict_emotion_with_confidence(r['text'])
    results.append((label == r['emotion'], conf, r['text'], r['emotion'], label))

n = len(results)
acc_all = sum(1 for ok, *_ in results if ok) / n
print(f'\n전체 정확도(게이트 없음): {acc_all:.4f}\n')
print(f'{"임계값":>6} | {"채택률":>7} | {"채택분 정확도":>10} | {"저확신行 오답률":>12}')
for t in [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    adopted = [(ok, c) for ok, c, *_ in results if c >= t]
    low = [(ok, c) for ok, c, *_ in results if c < t]
    ar = len(adopted) / n
    aa = sum(1 for ok, _ in adopted if ok) / len(adopted) if adopted else 0
    le = sum(1 for ok, _ in low if not ok) / len(low) if low else 0
    print(f'{t:>6.2f} | {ar:>6.1%} | {aa:>10.4f} | {le:>10.1%}')

print('\n고확신 오답 (임계값을 올려도 못 거르는 것들):')
for ok, c, text, gold, pred in sorted(results, key=lambda x: -x[1]):
    if not ok and c >= 0.9:
        print(f'  {c:.3f}  {text[:30]!r}  정답={gold} 예측={pred}')

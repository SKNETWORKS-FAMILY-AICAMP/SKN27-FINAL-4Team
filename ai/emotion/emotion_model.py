# -*- coding: utf-8 -*-
"""
학습된 감정분류 산출물(ai/emotion/artifacts)을 로드해 4감정(기쁨/슬픔/분노/일반)을 추론한다.
- 산출물·torch·transformers가 없으면 조용히 None을 반환 → 호출부(_classify_emotion)가 LLM 폴백.
- 임베딩은 학습과 동일하게 KcELECTRA mean-pool(last4 concat) + L2 정규화로 재현.

산출물 경로: 기본 <repo>/ai/emotion/artifacts (환경변수 EMOTION_ARTIFACT_DIR로 변경 가능)
필요 파일: metrics.json(best_model_path·embedding_model 등), <best>.joblib, (XGBoost면) label_encoder.joblib
"""
import os
import json
import threading
from pathlib import Path

_ART = Path(os.environ.get(
    'EMOTION_ARTIFACT_DIR',
    Path(__file__).resolve().parent / 'artifacts',
))

_lock = threading.Lock()
_S = {'tried': False, 'ok': False, 'clf': None, 'le': None,
      'tok': None, 'model': None, 'meta': None}


def _load():
    """최초 1회 지연 로드. 실패해도 예외를 삼키고 ok=False."""
    if _S['tried']:
        return _S['ok']
    with _lock:
        if _S['tried']:
            return _S['ok']
        _S['tried'] = True
        try:
            meta_path = _ART / 'metrics.json'
            if not meta_path.exists():
                return False
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            import joblib
            clf = joblib.load(_ART / meta['best_model_path'])
            le = (joblib.load(_ART / 'label_encoder.joblib')
                  if meta.get('uses_label_encoder') else None)

            import torch  # noqa: F401
            from transformers import AutoTokenizer, AutoModel
            name = meta.get('embedding_model', 'beomi/KcELECTRA-base-v2022')
            tok = AutoTokenizer.from_pretrained(name)
            model = AutoModel.from_pretrained(name, output_hidden_states=True).eval()

            _S.update(clf=clf, le=le, tok=tok, model=model, meta=meta, ok=True)
            return True
        except Exception as e:  # 산출물/라이브러리 없음 등 → 폴백
            print(f'[emotion_model] 비활성(폴백 사용): {e}')
            return False


def _embed(texts):
    import numpy as np
    import torch
    tok, model = _S['tok'], _S['model']
    enc = tok(texts, padding=True, truncation=True, max_length=128, return_tensors='pt')
    with torch.no_grad():
        out = model(**enc)
    mask = enc['attention_mask'].unsqueeze(-1).float()

    def mean_pool(h):
        return (h * mask).sum(1) / mask.sum(1).clamp(min=1)

    hs = out.hidden_states[-4:]                       # 학습과 동일: 마지막 4개 레이어
    emb = torch.cat([mean_pool(h) for h in hs], dim=-1).cpu().numpy()
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)  # L2
    return emb


def predict_emotion(text: str):
    """4감정(한글 라벨: 기쁨/슬픔/분노/일반) 반환. 모델 비활성/오류면 None."""
    if not text or not _load():
        return None
    try:
        emb = _embed([text])
        if _S['le'] is not None:                      # XGBoost: 라벨 디코딩 필요
            idx = _S['clf'].predict(emb)[0]
            return _S['le'].inverse_transform([int(idx)])[0]
        return _S['clf'].predict(emb)[0]
    except Exception as e:
        print(f'[emotion_model] 추론 실패(폴백): {e}')
        return None


def is_active() -> bool:
    return _load()

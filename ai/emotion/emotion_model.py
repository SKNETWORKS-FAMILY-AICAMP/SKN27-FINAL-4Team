# -*- coding: utf-8 -*-
"""
감정분류 추론 — 4감정(기쁨/슬픔/분노/일반).

로드 우선순위:
  1) 파인튜닝 모델  ai/emotion/artifacts_ft  (KcELECTRA +voice+KOTE · lr 5e-5 · 무누수)
     — 작성체 F1 0.7059 / 채팅체 150 F1 0.7764 (final_metrics.json)
  2) 구 임베딩+XGBoost  ai/emotion/artifacts  (폴백)
  3) 둘 다 없으면 None 반환 → 호출부(analysis_node)가 LLM 폴백.

환경변수: EMOTION_FT_DIR / EMOTION_ARTIFACT_DIR 로 경로 변경 가능.
"""
import os
import json
import threading
from pathlib import Path

_BASE = Path(__file__).resolve().parent
_FT = Path(os.environ.get('EMOTION_FT_DIR', _BASE / 'artifacts_ft'))
_ART = Path(os.environ.get('EMOTION_ARTIFACT_DIR', _BASE / 'artifacts'))

# 학습 시 라벨 인코딩 순서 (실험 노트북 EMO4와 동일 — 변경 금지)
EMO4 = ['기쁨', '슬픔', '분노', '일반']

_lock = threading.Lock()
_S = {'tried': False, 'mode': None,          # 'ft' | 'xgb' | None
      'tok': None, 'model': None,            # ft: 분류 모델 / xgb: 임베딩 모델
      'clf': None, 'le': None, 'meta': None}


def _load():
    """최초 1회 지연 로드. 실패해도 예외를 삼키고 mode=None."""
    if _S['tried']:
        return _S['mode'] is not None
    with _lock:
        if _S['tried']:
            return _S['mode'] is not None
        _S['tried'] = True

        # ── 1) 파인튜닝 모델 ──
        try:
            if (_FT / 'model.safetensors').exists():
                import torch  # noqa: F401
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                tok = AutoTokenizer.from_pretrained(str(_FT))
                model = AutoModelForSequenceClassification.from_pretrained(str(_FT)).eval()
                _S.update(tok=tok, model=model, mode='ft')
                print(f'[emotion_model] 파인튜닝 모델 로드: {_FT.name}')
                return True
        except Exception as e:
            print(f'[emotion_model] 파인튜닝 로드 실패({e}) → XGBoost 폴백 시도')

        # ── 2) 구 XGBoost 파이프라인 ──
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
            _S.update(clf=clf, le=le, tok=tok, model=model, meta=meta, mode='xgb')
            return True
        except Exception as e:
            print(f'[emotion_model] 비활성(폴백 사용): {e}')
            return False


def _ft_proba(text):
    import torch
    enc = _S['tok']([text], padding=True, truncation=True, max_length=128, return_tensors='pt')
    with torch.no_grad():
        logits = _S['model'](**enc).logits
    return torch.softmax(logits, dim=-1)[0].tolist()


def _embed(texts):
    """구 XGBoost 경로 — 학습과 동일한 mean-pool(last4 concat)+L2 임베딩."""
    import numpy as np
    import torch
    tok, model = _S['tok'], _S['model']
    enc = tok(texts, padding=True, truncation=True, max_length=128, return_tensors='pt')
    with torch.no_grad():
        out = model(**enc)
    mask = enc['attention_mask'].unsqueeze(-1).float()

    def mean_pool(h):
        return (h * mask).sum(1) / mask.sum(1).clamp(min=1)

    hs = out.hidden_states[-4:]
    emb = torch.cat([mean_pool(h) for h in hs], dim=-1).cpu().numpy()
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    return emb


def predict_emotion_with_confidence(text: str):
    """(한글 라벨, 확신도 0~1) 반환 — 확신도 게이트용.
    모델 비활성이면 (None, None), 확률 미지원 분류기면 (라벨, None)."""
    if not text or not _load():
        return None, None
    try:
        if _S['mode'] == 'ft':
            proba = _ft_proba(text)
            idx = max(range(len(proba)), key=lambda i: proba[i])
            return EMO4[idx], float(proba[idx])
        # xgb 폴백
        emb = _embed([text])
        clf = _S['clf']
        if hasattr(clf, 'predict_proba'):
            proba = clf.predict_proba(emb)[0]
            idx = int(proba.argmax())
            conf = float(proba[idx])
            if _S['le'] is not None:
                return _S['le'].inverse_transform([idx])[0], conf
            return clf.classes_[idx], conf
        if _S['le'] is not None:
            idx = clf.predict(emb)[0]
            return _S['le'].inverse_transform([int(idx)])[0], None
        return clf.predict(emb)[0], None
    except Exception as e:
        print(f'[emotion_model] 추론 실패(폴백): {e}')
        return None, None


def predict_emotion(text: str):
    """4감정(한글 라벨) 반환. 모델 비활성/오류면 None."""
    label, _ = predict_emotion_with_confidence(text)
    return label


def is_active() -> bool:
    return _load()

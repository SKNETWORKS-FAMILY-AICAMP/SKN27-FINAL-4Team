# -*- coding: utf-8 -*-
"""한국어 문장 임베딩 (2026-07-12) — 기억 의미 검색·dedup 2차의 공유 인프라.

모델: jhgan/ko-sroberta-multitask (768차원, 한국어 SBERT — 로컬 추론, API 비용 0)
소비자: ① graph_memory 의미 검색 (질문 ≈ 기억 유사도)
        ② 저장 시 즉시 dedup 2차 ("발표 잘함" ≈ "발표 대박" 병합)
        ③ (향후) 리플렉션 클러스터링

안전장치: sentence-transformers 미설치·모델 로드 실패 시 embed()가 None을 반환
→ 호출부는 키워드 매칭으로 폴백 (기존 챗봇에 영향 없음 — graph_memory와 같은 no-op 철학)
"""
import threading

import os

MODEL_NAME = os.environ.get('EMBED_MODEL', 'jhgan/ko-sroberta-multitask')
_IS_OPENAI = MODEL_NAME.startswith('openai/')       # 예: openai/text-embedding-3-small
_OPENAI_MODEL = MODEL_NAME.split('/', 1)[-1]
# e5 계열은 query/passage 접두사 필요 (벤치·임베딩 공통 처리)
_IS_E5 = (not _IS_OPENAI) and 'e5' in MODEL_NAME.lower()

def _default_dim():
    if _IS_OPENAI:
        return 3072 if 'large' in _OPENAI_MODEL else 1536
    return 384 if 'small' in MODEL_NAME else 768

EMBED_DIM = int(os.environ.get('EMBED_DIM', str(_default_dim())))

_model = None
_tried = False
_lock = threading.Lock()


def _load():
    global _model, _tried
    if _model is not None:
        return _model
    if _tried:
        return None
    with _lock:
        if _model is not None or _tried:
            return _model
        _tried = True
        try:
            if _IS_OPENAI:
                from openai import OpenAI
                _model = OpenAI()          # OPENAI_API_KEY 는 .env에 이미 있음
            else:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(MODEL_NAME)
            print(f'[embedder] {MODEL_NAME} 로드 완료 (dim={EMBED_DIM})')
        except Exception as e:
            print(f'[embedder] 비활성(키워드 폴백 사용): {e}')
            _model = None
    return _model


def is_available() -> bool:
    return _load() is not None


def embed(text: str):
    """문장 → 768차원 벡터(list[float]). 실패·빈 입력이면 None."""
    if not text or not text.strip():
        return None
    model = _load()
    if model is None:
        return None
    try:
        t = text.strip()
        if _IS_OPENAI:
            r = model.embeddings.create(model=_OPENAI_MODEL, input=t)
            return r.data[0].embedding      # OpenAI는 이미 정규화돼서 옴
        if _IS_E5:
            t = 'query: ' + t   # e5 규약 — 검색 질의·문서 모두 접두사 필요
        vec = model.encode(t, normalize_embeddings=True)  # 코사인용 정규화
        return vec.tolist()
    except Exception as e:
        print(f'[embedder] 추론 실패: {e}')
        return None

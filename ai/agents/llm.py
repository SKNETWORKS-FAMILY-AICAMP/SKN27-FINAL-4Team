# -*- coding: utf-8 -*-
"""LLM 공급자 선택 — .env 로 전환.

LLM_PROVIDER=openai (기본)  → OPENAI_API_KEY + OPENAI_MODEL(기본 gpt-5.4-mini)
LLM_PROVIDER=groq           → GROQ_API_KEY + GROQ_MODEL(기본 llama-3.3-70b-versatile)

사용처: graph/nodes.py(응답 생성/판별), memory.py(장기 요약)
"""
import os

OPENAI_DEFAULT_MODEL = 'gpt-4o-mini'      # 저렴+한국어 안정. 구형 계정이면 gpt-4o-mini로 교체
GROQ_DEFAULT_MODEL = 'llama-3.3-70b-versatile'


def _provider():
    return os.environ.get('LLM_PROVIDER', 'openai').strip().lower()


def _config():
    """(api_key, base_url, model) 반환."""
    if _provider() == 'groq':
        return (
            os.environ.get('GROQ_API_KEY', '').strip(),
            os.environ.get('GROQ_BASE_URL', 'https://api.groq.com/openai/v1'),
            os.environ.get('GROQ_MODEL', GROQ_DEFAULT_MODEL),
        )
    return (
        os.environ.get('OPENAI_API_KEY', '').strip(),
        os.environ.get('OPENAI_BASE_URL') or None,   # None이면 api.openai.com
        os.environ.get('OPENAI_MODEL', OPENAI_DEFAULT_MODEL),
    )


def get_llm(temperature=0.7, max_tokens=300):
    """LangChain ChatOpenAI 인스턴스 (그래프 노드/요약용)."""
    from langchain_openai import ChatOpenAI
    api_key, base_url, model = _config()
    if not api_key:
        raise ValueError(
            f"LLM API 키가 없습니다. .env에 "
            f"{'GROQ_API_KEY' if _provider() == 'groq' else 'OPENAI_API_KEY'} 를 설정하세요.")
    kwargs = dict(model=model, api_key=api_key, temperature=temperature, max_tokens=max_tokens)
    if base_url:
        kwargs['base_url'] = base_url
    return ChatOpenAI(**kwargs)

# (get_client — 추천 질문 전용 레거시 헬퍼는 기능 폐기로 제거 — 2026-07-03)

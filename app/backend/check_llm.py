# -*- coding: utf-8 -*-
"""LLM 연결 진단 — 현재 설정된 공급자(openai/groq)로 실제 호출까지 검사.
실행: app/backend 에서  python check_llm.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent  # 레포 루트
load_dotenv(_ROOT / '.env')
sys.path.insert(0, str(_ROOT))  # ai.* import 가능하게

from ai.agents.llm import _config, _provider  # noqa: E402

print('=' * 50)
provider = _provider()
api_key, base_url, model = _config()
print(f'[1] 공급자: {provider}  |  모델: {model}')

if not api_key:
    need = 'GROQ_API_KEY' if provider == 'groq' else 'OPENAI_API_KEY'
    print(f'[2] API 키: ❌ {need} 가 .env에 없습니다.')
    sys.exit(1)
print(f'[2] API 키: ✅ 로드됨 (...{api_key[-4:]}, 길이 {len(api_key)})')

try:
    from langchain_openai import ChatOpenAI  # noqa
    import langgraph  # noqa
    print('[3] langchain_openai / langgraph: ✅ 설치됨')
except ImportError as e:
    print(f'[3] 패키지 미설치: ❌ {e} → pip install langgraph langchain-openai')
    sys.exit(1)

print(f'[4] {provider} LLM 실제 호출 중... (모델: {model})')
try:
    kwargs = dict(model=model, api_key=api_key, max_tokens=20, temperature=0)
    if base_url:
        kwargs['base_url'] = base_url
    resp = ChatOpenAI(**kwargs).invoke("'연결 성공'이라고만 답하세요.")
    print(f'[4] LLM 응답: ✅ "{resp.content.strip()}"')
    print('=' * 50)
    print('🎉 전부 정상 — 서버 재시작(docker면 --force-recreate) 후 대화하세요.')
except Exception as e:
    msg = str(e)
    print(f'[4] LLM 호출: ❌ {type(e).__name__}')
    print(f'    상세: {msg[:300]}')
    print('=' * 50)
    if '401' in msg or 'invalid_api_key' in msg or 'Incorrect API key' in msg:
        print('→ 키가 잘못됐습니다. 해당 콘솔에서 키 재발급 후 교체하세요.')
    elif '404' in msg or 'model_not_found' in msg or 'does not exist' in msg:
        print(f'→ 모델명 "{model}" 이 이 계정에서 안 됩니다.')
        print('  .env에 OPENAI_MODEL=gpt-4o-mini 로 바꿔서 다시 시도해보세요.')
    elif '429' in msg or 'quota' in msg.lower():
        print('→ 사용량/결제 한도 문제입니다. platform.openai.com에서 크레딧 확인.')
    elif 'Connection' in msg or 'connect' in msg.lower():
        print('→ 네트워크 문제. 방화벽/프록시 확인.')
    else:
        print('→ 위 상세 메시지를 그대로 보여주세요.')
    sys.exit(1)

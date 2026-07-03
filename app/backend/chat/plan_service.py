# -*- coding: utf-8 -*-
"""Plan Agent — Tavily 외부 검색 (최종_통합_흐름도 §3).

⚠️ 트리거 조건(사용자 명시 요청 vs 에이전트 자동 판단)은 미확정.
   확정 전까지 프론트 진입점 없음 — POST /api/plan-support/ 만 준비된 상태.
"""
import os

import requests
from django.conf import settings

TAVILY_URL = 'https://api.tavily.com/search'


def tavily_search(query, max_results=3):
    """Tavily 검색 결과를 컨텍스트 문자열로 반환. 키 없음/실패 시 빈 문자열."""
    api_key = getattr(settings, 'TAVILY_API_KEY', '') or os.environ.get('TAVILY_API_KEY', '')
    if not api_key or not query:
        return ''
    try:
        resp = requests.post(
            TAVILY_URL,
            json={'api_key': api_key, 'query': query, 'max_results': max_results,
                  'search_depth': 'basic'},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])
        return '\n'.join(
            f"- {r.get('title', '')}: {r.get('content', '')[:200]}" for r in results
        )
    except Exception as e:
        print(f'[plan_service] Tavily 실패: {e}')
        return ''


def plan_support(address, emotion_label='normal'):
    """위치 기반 힐링 장소 추천 (API 명세서 v6.0 §4). Tavily + WalkCuration 조인."""
    area = address or '내 주변'
    query = f'{area} 조용하고 산책하기 좋은 힐링 장소 추천'

    items = []
    raw = tavily_search(query, max_results=3)
    for line in raw.splitlines():
        line = line.lstrip('- ').strip()
        if not line:
            continue
        title, _, desc = line.partition(':')
        items.append({
            'title': title.strip(),
            'category': 'walk',
            'reason': desc.strip()[:150],
            'estimated_time': '',
            'source': 'Tavily Search',
        })

    try:
        from chat.models import WalkCuration
        for w in WalkCuration.objects.filter(emotion=emotion_label)[:2]:
            items.append({
                'title': w.name,
                'category': 'walk',
                'reason': w.description[:150],
                'estimated_time': w.duration,
                'source': 'WalkCuration DB',
            })
    except Exception:
        pass

    return {'query': query, 'items': items}

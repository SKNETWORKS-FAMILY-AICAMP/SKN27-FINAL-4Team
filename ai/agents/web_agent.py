"""Web-grounded activity suggestions for an insufficient-data mind report."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from ai.agents.llm import OPENAI_DEFAULT_MODEL


logger = logging.getLogger(__name__)


class FallbackWebAgent:
    """Return suggestions only when Tavily evidence is actually available."""

    @staticmethod
    def get_trendy_contents(age, gender, hobbies=None, interests=None, mbti=None):
        openai_key = os.environ.get('OPENAI_API_KEY', '').strip()
        tavily_key = os.environ.get('TAVILY_API_KEY', '').strip()
        if not openai_key or not tavily_key:
            return []

        try:
            evidence = FallbackWebAgent._search_tavily(
                api_key=tavily_key,
                query=FallbackWebAgent._build_search_query(age=age, gender=gender),
            )
            if not evidence:
                return []
            return FallbackWebAgent._generate_recommendations(
                api_key=openai_key,
                evidence=evidence,
                age=age,
                gender=gender,
                hobbies=hobbies,
                interests=interests,
                mbti=mbti,
            )
        except Exception:
            logger.exception('Mind-report Tavily fallback generation failed.')
            return []

    @staticmethod
    def _build_search_query(*, age, gender) -> str:
        age_group = (
            f'{age // 10 * 10}대'
            if isinstance(age, int) and not isinstance(age, bool) and age > 0
            else '성인'
        )
        gender_text = str(gender).strip() if gender else '전체'
        return (
            f'요즘 {age_group} {gender_text} 이용자가 가볍게 시도하는 '
            '기분 전환 활동 최신 트렌드'
        )

    @staticmethod
    def _search_tavily(*, api_key: str, query: str) -> list[dict[str, str]]:
        import requests

        response = requests.post(
            os.environ.get('TAVILY_SEARCH_URL', 'https://api.tavily.com/search'),
            json={
                'api_key': api_key,
                'query': query,
                'search_depth': 'basic',
                'max_results': 3,
            },
            timeout=5,
        )
        response.raise_for_status()
        evidence = []
        for result in response.json().get('results', []):
            content = str(result.get('content') or '').strip()
            if not content:
                continue
            evidence.append({
                'title': str(result.get('title') or '').strip(),
                'url': str(result.get('url') or '').strip(),
                'content': content[:1500],
            })
        return evidence

    @staticmethod
    def _generate_recommendations(
        *,
        api_key: str,
        evidence: list[dict[str, str]],
        age,
        gender,
        hobbies,
        interests,
        mbti,
    ) -> list[dict[str, str]]:
        from openai import OpenAI

        profile_context = {
            'age_group': (
                age // 10 * 10
                if isinstance(age, int) and not isinstance(age, bool) and age > 0
                else None
            ),
            'gender': str(gender).strip() if gender else None,
            'hobbies': FallbackWebAgent._string_list(hobbies),
            'interests': FallbackWebAgent._string_list(interests),
            'mbti': str(mbti).strip() if mbti else None,
        }
        prompt = {
            'task': 'web_grounded_mindreport_waiting_activity_suggestions',
            'profile_context': profile_context,
            'tavily_evidence': evidence,
            'rules': [
                'Recommend at most three light activities supported by the Tavily evidence.',
                'These are web suggestions, not conclusions inferred from the user conversations.',
                'Do not claim that the user has done, prefers, or benefits from an activity.',
                'Do not mention MBTI, age, or gender in the visible recommendation text.',
                'If the evidence does not support a concrete activity, return an empty list.',
                'Return a JSON object only.',
            ],
            'output_schema': {
                'recommendations': [{
                    'activity': 'short activity name',
                    'reason': 'why this web result makes it worth considering',
                    'how_to': 'a low-burden way to try it',
                }],
            },
        }
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', OPENAI_DEFAULT_MODEL),
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You transform supplied Tavily evidence into cautious Korean activity '
                        'suggestions. Never invent trends or user facts. Return JSON only.'
                    ),
                },
                {
                    'role': 'user',
                    'content': json.dumps(prompt, ensure_ascii=False),
                },
            ],
            temperature=0,
            response_format={'type': 'json_object'},
        )
        data: Any = json.loads(response.choices[0].message.content or '{}')
        normalized = []
        for item in data.get('recommendations', []) if isinstance(data, dict) else []:
            if not isinstance(item, dict):
                continue
            activity = str(item.get('activity') or '').strip()
            if not activity:
                continue
            normalized.append({
                'activity': activity[:100],
                'reason': str(item.get('reason') or '').strip()[:300],
                'how_to': str(item.get('how_to') or '').strip()[:300],
            })
            if len(normalized) == 3:
                break
        return normalized

    @staticmethod
    def _string_list(value) -> list[str]:
        if not isinstance(value, (list, tuple)):
            return []
        return [str(item).strip()[:100] for item in value if str(item).strip()]

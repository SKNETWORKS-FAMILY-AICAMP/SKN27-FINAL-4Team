from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import sys


BACKEND_DIR = Path(__file__).resolve().parents[3] / "app" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@dataclass(frozen=True)
class DemoQuestionResponse:
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


def load_backend_env() -> None:
    env_path = BACKEND_DIR / '.env'
    try:
        from dotenv import load_dotenv
    except ImportError:
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue
            key, value = stripped.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return

    load_dotenv(env_path)


def sample_monthly_question_responses() -> list[DemoQuestionResponse]:
    responses = [
        DemoQuestionResponse(
            1,
            '최근에 지쳤을 때, 혼자 쉬는 쪽이 더 편했어 아니면 누군가랑 얘기하거나 움직이는 쪽이 더 나았어?',
            '누군가와 이야기하는것도 좋지만 지쳤다면 혼자 쉬는게 가장 좋지',
            'IE',
            datetime(2026, 6, 1, 9, 0),
        ),
        DemoQuestionResponse(
            2,
            '최근에 생각이 복잡했던 일이 있을 때, 혼자 정리했는지 말하면서 정리했는지 떠올려봐.',
            '혼자 밖에서 걸으면서 생각을 정리했어.',
            'IE',
            datetime(2026, 6, 2, 9, 0),
        ),
        DemoQuestionResponse(
            3,
            '요즘 사람 많은 자리나 모임에 다녀온 뒤에 기분이 어땠는지 말해줘.',
            '재미는 있지만 조금 지치기도 했지',
            'IE',
            datetime(2026, 6, 3, 9, 0),
        ),
        DemoQuestionResponse(
            4,
            '최근 쉬는 날에 에너지를 회복하려고 실제로 뭘 했는지 알려줘.',
            '나는 밖에나가 걸으면서 에너지를 회복하는 편이야',
            'IE',
            datetime(2026, 6, 4, 9, 0),
        ),
        DemoQuestionResponse(
            5,
            '최근 낯선 사람이나 새로운 분위기에서 네가 보통 어떻게 행동했는지 말해줘.',
            '누군가 먼저 말을 걸어오길 기다렸지. 물론 먼저 관심을 가져주면 신나게 이야기해',
            'IE',
            datetime(2026, 6, 5, 9, 0),
        ),
        DemoQuestionResponse(
            6,
            '최근 무언가를 결정할 때, 실제 근거를 더 봤는지 가능성을 더 상상했는지 말해줘.',
            '가능성이 조금더 생각났어',
            'SN',
            datetime(2026, 6, 6, 9, 0),
        ),
        DemoQuestionResponse(
            7,
            '요즘 새로운 설명을 들을 때, 구체적인 예시가 더 도움 됐어 아니면 큰 그림이 더 도움 됐어?',
            '구체적인 예시가 더 도움이 되는 편이지',
            'SN',
            datetime(2026, 6, 7, 9, 0),
        ),
        DemoQuestionResponse(
            8,
            '최근 어떤 문제를 해결할 때, 검증된 방식대로 했는지 새로운 방법을 떠올렸는지 알려줘.',
            '검증된 방식이 더 낫지. 새로운 방법은 너무 리스크가 커',
            'SN',
            datetime(2026, 6, 8, 9, 0),
        ),
        DemoQuestionResponse(
            9,
            '요즘 관심 가는 일이 있을 때, 당장 현실적인 부분을 먼저 봤는지 앞으로의 의미를 먼저 봤는지 말해줘.',
            '당장에 현실적인 부분이 조금 더 중요했어',
            'SN',
            datetime(2026, 6, 9, 9, 0),
        ),
        DemoQuestionResponse(
            10,
            '최근 누군가 계획이나 아이디어를 말했을 때, 네가 가장 먼저 확인하고 싶었던 게 뭐였어?',
            '그게 실현 가능한지를 먼저 생각했는지야',
            'SN',
            datetime(2026, 6, 10, 9, 0),
        ),
        DemoQuestionResponse(
            11,
            '최근 누군가 고민을 말했을 때, 공감이 먼저 나왔어 아니면 해결 방법이 먼저 떠올랐어?',
            '나는 그사람의 말을 경청하고 공감하는 편이야',
            'TF',
            datetime(2026, 6, 11, 9, 0),
        ),
        DemoQuestionResponse(
            12,
            '최근 의견이 갈린 상황에서, 네가 판단할 때 가장 중요하게 본 기준이 뭐였어?',
            '상대방의 의견이 근거가 있는지야.',
            'TF',
            datetime(2026, 6, 12, 9, 0),
        ),
        DemoQuestionResponse(
            13,
            '요즘 불편한 말을 해야 할 때, 솔직하게 말하는 쪽이 편했어 아니면 분위기를 살피는 쪽이 편했어?',
            '일단 불편한 말을 할때는 조금 분위기를 더 살피는 편이지 .',
            'TF',
            datetime(2026, 6, 13, 9, 0),
        ),
        DemoQuestionResponse(
            14,
            '최근 누군가와 갈등이 생겼을 때, 맞고 틀린 문제를 먼저 봤는지 상대 기분을 먼저 봤는지 말해줘.',
            ' 아무래도 사람의 기분이 먼저이긴했지 그래서 나는 반박을 많이 안해.',
            'TF',
            datetime(2026, 6, 14, 9, 0),
        ),
        DemoQuestionResponse(
            15,
            '최근 중요한 선택을 할 때, 효율과 원칙을 더 봤는지 사람들과의 관계를 더 봤는지 알려줘.',
            '사람의 관계가 조금 더 중요하긴해',
            'TF',
            datetime(2026, 6, 15, 9, 0),
        ),
        DemoQuestionResponse(
            16,
            '최근 할 일이 많았을 때, 미리 정리해서 처리했는지 상황 보면서 바꿔갔는지 말해줘.',
            '상황을 보면서 바꾸는 편이지 대부분',
            'JP',
            datetime(2026, 6, 16, 9, 0),
        ),
        DemoQuestionResponse(
            17,
            '요즘 일정이 갑자기 바뀌면, 바로 다시 계획을 세우는 편이야 아니면 흐름에 맞춰 움직이는 편이야?',
            '계획을 세우긴하는데 상세하게 세우진않아서 실제로는 그냥 흐름에 맞추는경우가 대부분이야',
            'JP',
            datetime(2026, 6, 17, 9, 0),
        ),
        DemoQuestionResponse(
            18,
            '최근 마감이나 약속이 있었을 때, 얼마나 미리 준비했는지 떠올려봐.',
            '대부분 일찍일찍 준비하는 편이야',
            'JP',
            datetime(2026, 6, 18, 9, 0),
        ),
        DemoQuestionResponse(
            19,
            '쉬는 날 계획을 잡을 때, 미리 정해두는 게 편했어 아니면 그날 기분대로 하는 게 편했어?',
            '그때그때 기분에 따라서 다르게 행동하지. 주말 계획까지 상세하게 하는건 힘들어',
            'JP',
            datetime(2026, 6, 19, 9, 0),
        ),
        DemoQuestionResponse(
            19,
            '최근 선택지가 여러 개 있었을 때, 빨리 정하고 싶었는지 좀 더 열어두고 싶었는지 말해줘.',
            '꽤나 심사숙고하는 편이지',
            'JP',
            datetime(2026, 6, 19, 9, 0),
        ),
        DemoQuestionResponse(
            20,
            '최근 일상에서 기억에 남는 일을 편하게 말해줘.',
            '이 응답은 MBTI 축이 아니므로 월간 집계에서 제외되어야 합니다.',
            'XX',
            datetime(2026, 6, 20, 9, 0),
        ),
    ]
    return responses


def build_demo_monthly_question_batch():
    from mbti.services.monthly_questions import (
        build_monthly_question_batch,
        resolve_month_period,
    )

    period_key, period_start, period_end = resolve_month_period(period_key='2026-06')
    responses = sample_monthly_question_responses()
    batch = build_monthly_question_batch(
        user_id=1,
        period_key=period_key,
        period_start=period_start,
        period_end=period_end,
        responses=responses,
    )
    return responses, batch

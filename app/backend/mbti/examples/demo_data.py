from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
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
    return [
        DemoQuestionResponse(
            1,
            '긴 하루가 끝난 뒤 에너지를 어떻게 회복하나요?',
            '혼자 방에 누워서 OTT를 보면 회복됩니다.',
            'IE',
            datetime(2026, 6, 1, 9, 0),
        ),
        DemoQuestionResponse(
            2,
            '주말 약속이 없다면 보통 무엇을 하나요?',
            '밖에 나가서 혼자 오랫동안 걷다들어옵니다.',
            'IE',
            datetime(2026, 6, 2, 9, 0),
        ),
        DemoQuestionResponse(
            3,
            '새로운 생각을 정리할 때 어떤 방식이 편한가요?',
            '혼자 멍때리면서 그 생각에 대해 계속 생각합니다.',
            'IE',
            datetime(2026, 6, 3, 9, 0),
        ),
        DemoQuestionResponse(
            4,
            '새로운 모임에서는 보통 어떻게 행동하나요?',
            '분위기를 계속 살피다가 누군가 관심을 가지면 적극적으로 대화합니다.',
            'IE',
            datetime(2026, 6, 4, 9, 0),
        ),
        DemoQuestionResponse(
            5,
            '이번 달 에너지가 가장 많이 올라간 순간은 언제였나요?',
            '그다지 없었습니다.',
            'IE',
            datetime(2026, 6, 5, 9, 0),
        ),
        DemoQuestionResponse(
            6,
            '새로운 정보를 이해할 때 무엇부터 확인하나요?',
            '정보의 흐름을 우선 파악합니다.',
            'SN',
            datetime(2026, 6, 6, 9, 0),
        ),
        DemoQuestionResponse(
            7,
            '설명을 들을 때 어떤 방식이 가장 도움이 되나요?',
            '머리속으로 흐름의 그림을 그리면 설명이 도움이 됩니다.',
            'SN',
            datetime(2026, 6, 7, 9, 0),
        ),
        DemoQuestionResponse(
            8,
            '낯선 일을 시작할 때 어떻게 접근하나요?',
            '어떻게 진행되어야하는지에 대해서 큰 그림을 먼저그립니다.',
            'SN',
            datetime(2026, 6, 8, 9, 0),
        ),
        DemoQuestionResponse(
            9,
            '문제를 볼 때 가장 먼저 떠오르는 것은 무엇인가요?',
            '어떤 방식으로 해결해야하는지를 상세히 떠올려봅니다.',
            'SN',
            datetime(2026, 6, 9, 9, 0),
        ),
        DemoQuestionResponse(
            10,
            '아이디어를 평가할 때 어떤 기준을 쓰나요?',
            '멋진 상상보다는 실제 구현 가능성과 필요한 자원을 먼저 따져보는 편입니다.',
            'SN',
            datetime(2026, 6, 10, 9, 0),
        ),
        DemoQuestionResponse(
            11,
            '중요한 결정을 할 때 무엇을 먼저 보나요?',
            '사람들의 의향을 종합합니다.',
            'TF',
            datetime(2026, 6, 11, 9, 0),
        ),
        DemoQuestionResponse(
            12,
            '피드백을 줄 때 어떤 점을 신경 쓰나요?',
            '상대방이 언짢아하지않도록 어조를 최대한 신경습니다.',
            'TF',
            datetime(2026, 6, 12, 9, 0),
        ),
        DemoQuestionResponse(
            13,
            '회의에서 의견 충돌이 생기면 무엇이 중요하다고 보나요?',
            '일단 상대방의 의견이 무엇인지 상세히 파악하는게 중요합니다.',
            'TF',
            datetime(2026, 6, 13, 9, 0),
        ),
        DemoQuestionResponse(
            14,
            '비판을 들었을 때 첫 반응은 어떤가요?',
            ' 말투가 차갑게 느껴지거나 공격적이면 일단 방어적으로 움츠러듭니다. .',
            'TF',
            datetime(2026, 6, 14, 9, 0),
        ),
        DemoQuestionResponse(
            15,
            '무엇이 당신을 설득하나요?',
            '구체적인 이유과 근거가 있어야 설득이 될것갔습니다.',
            'TF',
            datetime(2026, 6, 15, 9, 0),
        ),
        DemoQuestionResponse(
            16,
            '이번 달 일정 관리는 어떤 편이었나요?',
            '개판이었습니다. 일정을 정리했었지만 제대로 지키지못해 매번 쫒겼습니다.',
            'JP',
            datetime(2026, 6, 16, 9, 0),
        ),
        DemoQuestionResponse(
            17,
            '갑작스러운 변경이 생기면 어떻게 대응하나요?',
            '계획과 우선순위를 바로 최적화적용합니다.',
            'JP',
            datetime(2026, 6, 17, 9, 0),
        ),
        DemoQuestionResponse(
            18,
            '마감이 있는 일은 어떻게 처리하나요?',
            '마감까지 최대한 숙고하여 이것저것 검증합니다.',
            'JP',
            datetime(2026, 6, 18, 9, 0),
        ),
        DemoQuestionResponse(
            19,
            '여행을 간다면 어떤 준비를 하나요?',
            '숙소와 이동 경로는 미리 정하지만, 현지에서 끌리는 장소를 즉흥적으로 넣는 것도 좋아합니다.',
            'JP',
            datetime(2026, 6, 19, 9, 0),
        ),
        DemoQuestionResponse(
            19,
            '할 일이 여러 개 있어. 너라면 하나씩 끝내가며 진행하는 게 편할 것 같아?',
            '나라면 우선순위를 정하지못해서 무리하게 멀티태스킹할것같아.',
            'JP',
            datetime(2026, 6, 19, 9, 0),
        ),
        DemoQuestionResponse(
            20,
            '잘못된 축 예시',
            '이 응답은 MBTI 축이 아니므로 월간 집계에서 제외되어야 합니다.',
            'XX',
            datetime(2026, 6, 20, 9, 0),
        ),
    ]


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

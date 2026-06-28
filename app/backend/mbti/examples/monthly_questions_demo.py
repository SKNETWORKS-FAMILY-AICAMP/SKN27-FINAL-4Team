from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mbti.services.monthly_questions import (  # noqa: E402
    build_monthly_question_batch,
    resolve_month_period,
)


@dataclass(frozen=True)
class FakeQuestionResponse:
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


def _fake_responses() -> list[FakeQuestionResponse]:
    return [
        FakeQuestionResponse(
            id=1,
            question_text='낯선 모임에서 먼저 말을 거는 편인가요?',
            answer_text='거의 말을 걸지 않습니다.',
            target_axis='IE',
            answered_at=datetime(2026, 6, 2, 9, 0),
        ),
        FakeQuestionResponse(
            id=2,
            question_text='새로운 일을 볼 때 가능성을 먼저 보나요?',
            answer_text='아니요 당장의 일',
            target_axis='SN',
            answered_at=datetime(2026, 6, 3, 9, 0),
        ),
        FakeQuestionResponse(
            id=3,
            question_text='결정할 때 기준과 감정 중 무엇을 더 보나요?',
            answer_text='먼저 기준을 정하고 사실관계를 확인한 뒤 결정합니다.',
            target_axis='TF',
            answered_at=datetime(2026, 6, 4, 9, 0),
        ),
        FakeQuestionResponse(
            id=4,
            question_text='계획이 정해진 여행과 즉흥 여행 중 무엇이 편한가요?',
            answer_text='큰 일정은 정해두고 세부는 현장에서 바꾸는 게 좋습니다.',
            target_axis='JP',
            answered_at=datetime(2026, 6, 5, 9, 0),
        ),
        FakeQuestionResponse(
            id=5,
            question_text='낯선 환경에서 에너지를 어떻게 쓰나요?',
            answer_text='처음엔 조용히 관찰하다가 익숙해지면 조금씩 말합니다.',
            target_axis='IE',
            answered_at=datetime(2026, 6, 6, 9, 0),
        ),
        FakeQuestionResponse(
            id=6,
            question_text='잘못된 축 예시',
            answer_text='이 응답은 집계에서 제외되어야 합니다.',
            target_axis='XX',
            answered_at=datetime(2026, 6, 7, 9, 0),
        ),
        FakeQuestionResponse(
            id=5,
            question_text='낯선 환경에서 에너지를 어떻게 쓰나요?',
            answer_text='처음엔 조용히 관찰하다가 익숙해지면 조금씩 말합니다.',
            target_axis='IE',
            answered_at=datetime(2026, 6, 6, 9, 0),
        ),
    ]


def main() -> None:
    period_key, period_start, period_end = resolve_month_period(period_key='2026-06')
    responses = _fake_responses()
    batch = build_monthly_question_batch(
        user_id=1,
        period_key=period_key,
        period_start=period_start,
        period_end=period_end,
        responses=responses,
    )

    print('[INPUT]')
    print(f'user_id: {batch.user_id}')
    print(f'period_key request: 2026-06')
    print(f'raw_response_count: {len(responses)}')
    for response in responses:
        print(
            f'- id={response.id}, axis={response.target_axis}, '
            f'answered_at={response.answered_at.isoformat()}, '
            f'question={response.question_text}'
        )

    print('\n[OUTPUT: A]')
    print(f'period_key: {batch.period_key}')
    print(f'period_start: {batch.period_start.isoformat()}')
    print(f'period_end: {batch.period_end.isoformat()}')

    print('\n[OUTPUT: B]')
    print(f'axis_counts: {batch.axis_counts}')
    print(f'total_count: {batch.total_count}')
    for axis, items in batch.axis_responses.items():
        print(f'\n{axis} responses ({len(items)}):')
        if not items:
            print('  - none')
            continue
        for item in items:
            print(
                f'  - id={item.id}, answered_at={item.answered_at.isoformat()}, '
                f'question={item.question_text}, answer={item.answer_text}'
            )


if __name__ == '__main__':
    main()

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
from mbti.services.opening_rules import evaluate_primary_opening_from_batch  # noqa: E402


@dataclass(frozen=True)
class FakeQuestionResponse:
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


def _fake_responses() -> list[FakeQuestionResponse]:
    rows: list[FakeQuestionResponse] = []
    next_id = 1

    for axis, count in {'IE': 5, 'SN': 4, 'TF': 6, 'JP': 0}.items():
        for index in range(count):
            rows.append(
                FakeQuestionResponse(
                    id=next_id,
                    question_text=f'{axis} question {index + 1}',
                    answer_text=f'{axis} answer {index + 1}',
                    target_axis=axis,
                    answered_at=datetime(2026, 6, min(index + 1, 28), 9, 0),
                )
            )
            next_id += 1

    return rows


def main() -> None:
    period_key, period_start, period_end = resolve_month_period(period_key='2026-06')
    batch = build_monthly_question_batch(
        user_id=1,
        period_key=period_key,
        period_start=period_start,
        period_end=period_end,
        responses=_fake_responses(),
    )
    opening = evaluate_primary_opening_from_batch(batch)

    print('[INPUT]')
    print(f'user_id: {batch.user_id}')
    print(f'period_key: {batch.period_key}')
    print(f'period_start: {batch.period_start.isoformat()}')
    print(f'period_end: {batch.period_end.isoformat()}')
    print(f'axis_counts: {batch.axis_counts}')

    print('\n[OUTPUT: C -> D/G]')
    for axis, result in opening.axis_results.items():
        branch = 'D: score responses with LLM' if result.primary_open else 'G: apply baseline letter'
        print(
            f'{axis}: qna_count={result.qna_count}, '
            f'required={result.required_qna_count}, '
            f'primary_open={result.primary_open}, '
            f'next={branch}, '
            f'data_status={result.data_status}'
        )

    print(f'\nscoring_axes: {opening.scoring_axes}')
    print(f'baseline_axes: {opening.baseline_axes}')


if __name__ == '__main__':
    main()

from __future__ import annotations

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mbti.examples.demo_data import build_demo_monthly_question_batch  # noqa: E402


def main() -> None:
    responses, batch = build_demo_monthly_question_batch()

    print('[INPUT]')
    print(f'user_id: {batch.user_id}')
    print('period_key request: 2026-06')
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

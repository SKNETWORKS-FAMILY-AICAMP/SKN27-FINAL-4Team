from __future__ import annotations

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mbti.examples.demo_data import build_demo_monthly_question_batch  # noqa: E402
from mbti.services.opening_rules import evaluate_primary_opening_from_batch  # noqa: E402


def main() -> None:
    _, batch = build_demo_monthly_question_batch()
    opening = evaluate_primary_opening_from_batch(batch)

    print('[INPUT: A -> B]')
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

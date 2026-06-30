from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mbti.examples.demo_data import (  # noqa: E402
    build_demo_monthly_question_batch,
    load_backend_env,
)
from mbti.services.llm_config import build_scoring_llm_config  # noqa: E402
from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline  # noqa: E402


def _require_real_llm_demo() -> None:
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError(
            'OPENAI_API_KEY is required because this demo reads scores from real response_scoring.'
        )
    if importlib.util.find_spec('langchain_openai') is None:
        raise RuntimeError(
            'The langchain-openai package is required. Install app/backend/requirements.txt first.'
        )


def _format_ratios(axis_ratios: dict[str, float]) -> str:
    return ' / '.join(
        f'{letter} {ratio:.0%}'
        for letter, ratio in axis_ratios.items()
    )


def main() -> None:
    _, batch = build_demo_monthly_question_batch()
    llm_config = build_scoring_llm_config()

    print('[INPUT: demo_data -> A -> B]')
    print(f'user_id: {batch.user_id}')
    print(f'period_key: {batch.period_key}')
    print(f'axis_counts: {batch.axis_counts}')

    print('\n[CONFIG: D/K]')
    print('LLM runtime: langchain-openai ChatOpenAI')
    print(f'LLM provider: {llm_config.provider}')
    print(f'LLM model: {llm_config.model}')
    print(f'temperature: {llm_config.temperature}')

    _require_real_llm_demo()
    result = run_monthly_mbti_pipeline(
        batch=batch,
        previous_axis_letters={
            'IE': 'I',
            'SN': 'N',
            'TF': 'F',
        },
        previous_period_key='2026-05',
        previous_estimated_mbti_type='INFP',
        onboarding_mbti_type='INFP',
        scoring_config=llm_config,
    )

    print('\n[PIPELINE CHECK: C -> D -> E]')
    print(f'primary scoring_axes: {result.primary_opening.scoring_axes}')
    print(f'primary baseline_axes: {result.primary_opening.baseline_axes}')
    print(f'response_score_count: {len(result.response_scores)}')
    print(f'graph_score_axes: {result.secondary_opening.graph_score_axes}')
    print(f'baseline_axes_after_E: {result.secondary_opening.baseline_axes}')

    print('\n[GRAPH SCORE INPUT: from response_scoring]')
    for score in result.response_scores:
        print(
            f'- response_id={score.response_id}, axis={score.axis}, '
            f'score={score.score}, coding_status={score.coding_status}'
        )

    print('\n[OUTPUT: F -> H -> I/G]')
    for axis, axis_result in result.graph_result.axis_results.items():
        if axis_result.axis_avg is None:
            print(
                f'{axis}: no graph score, next=G, '
                f'data_status={axis_result.data_status}'
            )
            continue

        selected = axis_result.selected_letter or 'baseline'
        print(
            f'{axis}: axis_avg={axis_result.axis_avg:.3f}, '
            f'ratios={_format_ratios(axis_result.axis_ratios)}, '
            f'selected_letter={selected}, '
            f'next={axis_result.next_step}, '
            f'data_status={axis_result.data_status}'
        )

    print(f'\nselected_axes: {result.graph_result.selected_axes}')
    print(f'tie_axes: {result.graph_result.tie_axes}')
    print(f'graph_baseline_axes: {result.graph_result.baseline_axes}')
    print(f'estimated_mbti_type_after_MJ: {result.monthly_result.estimated_mbti_type}')
    print(f'report_section_count_after_K: {len(result.report.report_sections)}')


if __name__ == '__main__':
    load_backend_env()
    try:
        main()
    except RuntimeError as exc:
        print(f'[DEMO NOT RUN] {exc}')
        raise SystemExit(2)

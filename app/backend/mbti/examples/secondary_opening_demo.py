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
from mbti.examples.monthly_demo_payload import (  # noqa: E402
    DEMO_PAYLOAD_PATH,
    build_changed_axis_display_text,
    write_demo_payload,
)
from mbti.services.baseline_sources import UserBaselineSnapshot  # noqa: E402
from mbti.services.llm_config import build_scoring_llm_config  # noqa: E402
from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline  # noqa: E402
from mbti.services.reports import ReportSection  # noqa: E402


class DemoScoringClient:
    def score_axis_responses(self, *, axis, responses, config):
        score_by_axis = {
            'IE': [-1.0, -0.5, -0.5, 0.5, 0.0],
            'SN': [1.0, 0.5, 0.5, -0.5, 1.0],
            'TF': [1.0, 0.5, 1.0, 0.0, 0.5],
        }
        return {
            'scores': [
                {
                    'response_id': response.id,
                    'score': score,
                    'coding_status': 'coded',
                    'reason': f'demo fallback score for {axis}',
                }
                for response, score in zip(responses, score_by_axis.get(axis, []), strict=False)
            ]
        }


class DemoReportClient:
    def generate_sections(self, *, monthly_result, axis_results, evidence_items):
        change_text = build_changed_axis_display_text(
            monthly_result=monthly_result,
            axis_results=axis_results,
        )
        top_evidence = evidence_items[0] if evidence_items else None
        if top_evidence:
            evidence_text = (
                f'{top_evidence.axis}축 응답 {top_evidence.question_response_id} '
                f'(score={top_evidence.score}, '
                f'delta_contribution={top_evidence.score_delta_contribution}, '
                f'impact={top_evidence.impact_score:.2f}, '
                f'answer="{top_evidence.answer_text}")'
            )
        else:
            evidence_text = '없음'

        return (
            ReportSection(
                title='이번 달 축 변화 요약',
                content=(
                    f'{monthly_result.period_key} 월간 MBTI는 '
                    f'{monthly_result.estimated_mbti_type}입니다. '
                    f'{change_text}'
                ),
            ),
            ReportSection(
                title='점수 변화에 영향을 준 대표 응답',
                content=f'이번 달 점수와 경향 선택에 가장 크게 반영된 대표 근거는 {evidence_text}입니다.',
            ),
            ReportSection(
                title='월간 MBTI 유형 설명',
                content=(
                    f'{monthly_result.estimated_mbti_type} 유형 설명은 실제 운영에서는 '
                    '리포트 LLM이 최종 유형 자체에 대해서만 짧게 생성합니다.'
                ),
            ),
        )


def _can_run_real_llm_demo() -> bool:
    return bool(os.getenv('OPENAI_API_KEY')) and (
        importlib.util.find_spec('langchain_openai') is not None
    )


def _format_ratios(axis_ratios: dict[str, float]) -> str:
    return ' / '.join(
        f'{letter} {ratio:.0%}'
        for letter, ratio in axis_ratios.items()
    )


def main() -> None:
    _, batch = build_demo_monthly_question_batch()
    llm_config = build_scoring_llm_config()
    real_llm_mode = _can_run_real_llm_demo()
    baseline_snapshot = UserBaselineSnapshot(
        user_id=batch.user_id,
        previous_axis_letters={
            'IE': 'I',
            'SN': 'N',
            'TF': 'F',
        },
        previous_axis_period_keys={
            'IE': '2026-05',
            'SN': '2026-05',
            'TF': '2026-05',
        },
        previous_axis_avgs={
            'IE': -0.35,
            'SN': -0.30,
            'TF': -0.45,
        },
        previous_axis_ratios={
            'IE': {'I': 0.68, 'E': 0.32},
            'SN': {'N': 0.65, 'S': 0.35},
            'TF': {'F': 0.72, 'T': 0.28},
        },
        previous_period_key='2026-05',
        previous_estimated_mbti_type='INFP',
        onboarding_mbti_type='INFP',
    )

    print('[INPUT: A -> B]')
    print(f'user_id: {batch.user_id}')
    print(f'period_key: {batch.period_key}')
    print(f'period_start: {batch.period_start.isoformat()}')
    print(f'period_end: {batch.period_end.isoformat()}')
    print(f'axis_counts: {batch.axis_counts}')

    print('\n[CONFIG: D/K]')
    print('pipeline: demo_data -> monthly_pipeline')
    print(f'LLM provider: {llm_config.provider}')
    print(f'LLM model: {llm_config.model}')
    print(f'temperature: {llm_config.temperature}')
    if real_llm_mode:
        print('demo_mode: real LangChain OpenAI scoring/report')
        scoring_client = None
        report_client = None
    else:
        print('demo_mode: local deterministic fallback scoring/report')
        scoring_client = DemoScoringClient()
        report_client = DemoReportClient()

    result = run_monthly_mbti_pipeline(
        batch=batch,
        baseline_snapshot=baseline_snapshot,
        scoring_client=scoring_client,
        scoring_config=llm_config,
        report_client=report_client,
    )

    print('\n[OUTPUT: C -> D/G]')
    print(f'primary scoring_axes: {result.primary_opening.scoring_axes}')
    print(f'primary baseline_axes: {result.primary_opening.baseline_axes}')

    print('\n[OUTPUT: D]')
    for score in result.response_scores:
        print(
            f'- response_id={score.response_id}, axis={score.axis}, '
            f'score={score.score}, coding_status={score.coding_status}, '
            f'reason={score.reason}'
        )

    print('\n[OUTPUT: E -> F/G]')
    for axis, axis_result in result.secondary_opening.axis_results.items():
        branch = 'F: calculate graph display score' if axis_result.secondary_open else 'G: apply baseline letter'
        print(
            f'{axis}: primary_open={axis_result.primary_open}, '
            f'scored_count={axis_result.scored_count}, '
            f'required={axis_result.required_scored_count}, '
            f'secondary_open={axis_result.secondary_open}, '
            f'next={branch}, '
            f'data_status={axis_result.data_status}'
        )
    print(f'graph_score_axes: {result.secondary_opening.graph_score_axes}')
    print(f'baseline_axes: {result.secondary_opening.baseline_axes}')

    print('\n[OUTPUT: F -> H -> I/G]')
    for axis, graph_axis in result.graph_result.axis_results.items():
        if graph_axis.axis_avg is None:
            print(f'{axis}: no graph score, next=G, data_status={graph_axis.data_status}')
            continue
        selected = graph_axis.selected_letter or 'baseline'
        print(
            f'{axis}: axis_avg={graph_axis.axis_avg:.3f}, '
            f'ratios={_format_ratios(graph_axis.axis_ratios)}, '
            f'selected_letter={selected}, '
            f'next={graph_axis.next_step}, '
            f'data_status={graph_axis.data_status}'
        )

    print('\n[OUTPUT: M -> J -> K -> L]')
    for axis, axis_result in result.final_axis_results.items():
        score_delta = (
            axis_result.axis_avg - axis_result.previous_axis_avg
            if axis_result.data_status == 'current_month'
            and axis_result.axis_avg is not None
            and axis_result.previous_axis_avg is not None
            else None
        )
        print(
            f'{axis}: selected_letter={axis_result.selected_letter}, '
            f'axis_avg={axis_result.axis_avg}, '
            f'previous_axis_avg={axis_result.previous_axis_avg}, '
            f'score_delta={score_delta}, '
            f'data_status={axis_result.data_status}, '
            f'baseline_source={axis_result.baseline_source}'
        )
    print(f'estimated_mbti_type: {result.monthly_result.estimated_mbti_type}')
    print(f'changed_axes: {result.monthly_result.changed_axes}')
    print(f'status: {result.monthly_result.status}')
    print(f'evidence_count: {len(result.evidence_items)}')
    print(f'report_section_count: {len(result.report.report_sections)}')
    print(f'payload estimated_mbti_type: {result.mypage_payload["estimated_mbti_type"]}')

    frontend_payload = write_demo_payload(result)
    print(f'frontend_payload_path: {DEMO_PAYLOAD_PATH}')
    print(f'frontend_payload_source: {frontend_payload["source"]}')

    print('\n[REPORT SECTIONS]')
    for section in result.report.report_sections:
        print(f'- {section.title}: {section.content}')


if __name__ == '__main__':
    load_backend_env()
    main()

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from mbti.examples.demo_data import build_demo_monthly_question_batch
from mbti.services.baseline_sources import UserBaselineSnapshot
from mbti.services.llm_config import build_scoring_llm_config
from mbti.services.monthly_pipeline import MonthlyMbtiPipelineResult, run_monthly_mbti_pipeline
from mbti.services.reports import ReportSection


DEMO_PAYLOAD_PATH = Path(__file__).resolve().with_name('monthly_demo_payload.json')


class DemoScoringClient:
    def score_axis_responses(self, *, axis, responses, config):
        score_by_axis = {
            'IE': [-1.0, -0.5, -0.5, 0.5, 0.0],
            'SN': [1.0, 0.5, 0.5, -0.5, 1.0],
            'TF': [1.0, 0.5, 1.0, 0.0, 0.5],
            'JP': [-1.0, 0.5, -0.5, 0.0, -1.0],
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
        evidence_text = (
            f'{top_evidence.axis}축 응답 원문: "{top_evidence.answer_text}"'
            if top_evidence
            else '선호 경향 전환을 설명할 대표 응답 없음'
        )

        return (
            ReportSection(
                title='이번 달 축 변화 요약',
                content=(
                    f'{monthly_result.period_key} 월간 MBTI는 '
                    f'{monthly_result.estimated_mbti_type or "산출 불가"}입니다. '
                    f'{change_text}'
                ),
            ),
            ReportSection(
                title='점수 변화에 영향을 준 대표 응답',
                content=evidence_text,
            ),
            ReportSection(
                title='월간 MBTI 유형 설명',
                content=(
                    f'{monthly_result.estimated_mbti_type or "이번 달 MBTI"}는 현재 월간 분석에서 '
                    '산출된 최종 유형 자체에 대한 간단 설명 영역입니다.'
                ),
            ),
        )


def display_score_for_letter(ratios: dict[str, float], letter: str | None) -> int | None:
    if not letter or letter not in ratios:
        return None
    return round(ratios[letter] * 100)


def build_changed_axis_display_text(*, monthly_result, axis_results) -> str:
    index_by_axis = {'IE': 0, 'SN': 1, 'TF': 2, 'JP': 3}
    parts = []
    previous_type = monthly_result.previous_estimated_mbti_type
    for axis, result in axis_results.items():
        if (
            result.data_status != 'current_month'
            or not previous_type
            or len(previous_type) != 4
            or not result.selected_letter
        ):
            continue
        previous_letter = previous_type[index_by_axis[axis]]
        if previous_letter == result.selected_letter:
            continue
        previous_score = display_score_for_letter(result.previous_axis_ratios, previous_letter)
        current_score = display_score_for_letter(result.axis_ratios, result.selected_letter)
        if previous_score is None or current_score is None:
            parts.append(f'{axis} {previous_letter}->{result.selected_letter}')
            continue
        parts.append(
            f'{axis} {previous_letter}->{result.selected_letter}'
            f'({previous_score}%->{current_score}%, {current_score - previous_score:+d}%p)'
        )
    return ', '.join(parts) if parts else '이번 달 실제 선호 경향이 바뀐 축은 없습니다.'


def build_demo_baseline_snapshot(user_id: int) -> UserBaselineSnapshot:
    return UserBaselineSnapshot(
        user_id=user_id,
        previous_axis_letters={'IE': 'I', 'SN': 'N', 'TF': 'F', 'JP': 'P'},
        previous_axis_period_keys={'IE': '2026-05', 'SN': '2026-05', 'TF': '2026-05', 'JP': '2026-05'},
        previous_axis_avgs={'IE': -0.35, 'SN': -0.30, 'TF': -0.45, 'JP': -0.20},
        previous_axis_ratios={
            'IE': {'I': 0.68, 'E': 0.32},
            'SN': {'N': 0.65, 'S': 0.35},
            'TF': {'F': 0.72, 'T': 0.28},
            'JP': {'P': 0.60, 'J': 0.40},
        },
        previous_period_key='2026-05',
        previous_estimated_mbti_type='INFP',
        onboarding_mbti_type='INFP',
    )


def run_local_monthly_demo_pipeline() -> MonthlyMbtiPipelineResult:
    _, batch = build_demo_monthly_question_batch()
    return run_monthly_mbti_pipeline(
        batch=batch,
        baseline_snapshot=build_demo_baseline_snapshot(batch.user_id),
        scoring_client=DemoScoringClient(),
        scoring_config=build_scoring_llm_config(),
        report_client=DemoReportClient(),
    )


def axis_score_for_frontend(axis_result: dict[str, Any]) -> int:
    selected = axis_result.get('selected_letter')
    ratios = axis_result.get('axis_ratios') or axis_result.get('previous_axis_ratios') or {}
    if selected and selected in ratios:
        return round(ratios[selected] * 100)
    return 50


def build_frontend_payload_from_pipeline_result(
    pipeline_result: MonthlyMbtiPipelineResult,
    *,
    source: str,
) -> dict[str, Any]:
    payload = pipeline_result.mypage_payload
    current_type = payload.get('estimated_mbti_type') or '----'
    previous_type = payload.get('previous_estimated_mbti_type') or '----'
    axis_results = payload.get('axis_results', [])

    return {
        'view_mode': 'monthly_analysis',
        'status': payload.get('status', 'ready'),
        'period_key': payload.get('period_key'),
        'source': source,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'has_monthly_analysis': True,
        'onboarding_mbti_type': 'INFP',
        'previous_estimated_mbti_type': previous_type,
        'estimated_mbti_type': current_type,
        'changed_axes': payload.get('changed_axes', []),
        'mbti_view_mode': 'onboardingNext',
        'mbti_data': {
            'onboarding': {
                'type': 'INFP',
                'period': '온보딩 시점 기준 (데모 데이터)',
                'description': 'INFP는 보통 개인의 가치와 의미를 중시하고, 자기만의 기준으로 경험을 해석하는 경향으로 설명됩니다.',
                'report': [
                    '현재 화면은 데이터베이스 구축 전 데모 API 응답을 반영합니다.',
                    '온보딩 MBTI는 월간 계산값이 없을 때 기준값으로 사용될 수 있습니다.',
                    '월간 분석이 가능해지면 실제 Q&A 기반 결과가 우선 표시됩니다.',
                ],
            },
            'previous': {
                'type': previous_type,
                'monthLabel': '이전 기준(2026-05) 데모',
            },
            'current': {
                'type': current_type,
                'monthLabel': f'{payload.get("period_key", "2026-06")} 데모',
                'axes': [
                    {
                        'label': axis.get('selected_letter') or '-',
                        'pair': axis['axis'],
                        'score': axis_score_for_frontend(axis),
                    }
                    for axis in axis_results
                ],
            },
            'report': [
                f'[{section["title"]}] {section["content"]}'
                for section in payload.get('report_sections', [])
            ],
        },
        'raw': payload,
    }


def write_demo_payload(
    pipeline_result: MonthlyMbtiPipelineResult,
    *,
    path: Path = DEMO_PAYLOAD_PATH,
) -> dict[str, Any]:
    payload = build_frontend_payload_from_pipeline_result(
        pipeline_result,
        source='example_secondary_opening_demo',
    )
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return payload


def read_demo_payload(path: Path = DEMO_PAYLOAD_PATH) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding='utf-8'))

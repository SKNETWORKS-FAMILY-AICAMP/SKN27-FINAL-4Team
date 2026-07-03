from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from mbti.services.graph_scores import GraphScoreResult
from mbti.services.monthly_questions import MBTI_AXES, MbtiMonthlyQuestionBatch


AXIS_TYPE_INDEX = {
    'IE': 0,
    'SN': 1,
    'TF': 2,
    'JP': 3,
}
AXIS_ALLOWED_LETTERS = {
    'IE': {'I', 'E'},
    'SN': {'S', 'N'},
    'TF': {'T', 'F'},
    'JP': {'J', 'P'},
}


@dataclass(frozen=True)
class BaselinePreference:
    axis: str
    selected_letter: str
    baseline_source: str
    baseline_period_key: str | None = None
    axis_avg: float | None = None
    axis_ratios: dict[str, float] | None = None


@dataclass(frozen=True)
class FinalAxisPreference:
    axis: str
    qna_count: int
    scored_count: int
    axis_avg: float | None
    axis_ratios: dict[str, float]
    previous_axis_avg: float | None
    previous_axis_ratios: dict[str, float]
    selected_letter: str | None
    data_status: str
    calculation_status: str
    baseline_letter: str | None
    baseline_source: str | None
    baseline_period_key: str | None


@dataclass(frozen=True)
class MonthlyMbtiResult:
    user_id: int
    period_key: str
    previous_estimated_mbti_type: str | None
    estimated_mbti_type: str | None
    changed_axes: tuple[str, ...]
    status: str
    axis_results: dict[str, FinalAxisPreference]


def extract_onboarding_baselines(
    onboarding_mbti_type: str | None,
) -> dict[str, BaselinePreference]:
    if onboarding_mbti_type is None:
        return {}

    mbti_type = onboarding_mbti_type.strip().upper()
    if len(mbti_type) != 4:
        return {}

    baselines: dict[str, BaselinePreference] = {}
    for axis in MBTI_AXES:
        letter = mbti_type[AXIS_TYPE_INDEX[axis]]
        if letter in AXIS_ALLOWED_LETTERS[axis]:
            baselines[axis] = BaselinePreference(
                axis=axis,
                selected_letter=letter,
                baseline_source='onboarding',
                baseline_period_key=None,
            )
    return baselines


def build_previous_monthly_baselines(
    *,
    previous_axis_letters: Mapping[str, str],
    previous_period_key: str | None,
    previous_axis_period_keys: Mapping[str, str | None] | None = None,
    previous_axis_avgs: Mapping[str, float | None] | None = None,
    previous_axis_ratios: Mapping[str, dict[str, float]] | None = None,
) -> dict[str, BaselinePreference]:
    baselines: dict[str, BaselinePreference] = {}
    axis_period_keys = previous_axis_period_keys or {}
    axis_avgs = previous_axis_avgs or {}
    axis_ratios = previous_axis_ratios or {}
    for axis in MBTI_AXES:
        letter = previous_axis_letters.get(axis)
        if letter in AXIS_ALLOWED_LETTERS[axis]:
            baselines[axis] = BaselinePreference(
                axis=axis,
                selected_letter=letter,
                baseline_source='latest_monthly_result',
                baseline_period_key=axis_period_keys.get(axis, previous_period_key),
                axis_avg=axis_avgs.get(axis),
                axis_ratios=dict(axis_ratios.get(axis, {})),
            )
    return baselines


def resolve_axis_baseline(
    *,
    axis: str,
    previous_baselines: Mapping[str, BaselinePreference],
    onboarding_baselines: Mapping[str, BaselinePreference],
) -> BaselinePreference | None:
    return previous_baselines.get(axis) or onboarding_baselines.get(axis)


def finalize_monthly_axis_preferences(
    *,
    batch: MbtiMonthlyQuestionBatch,
    graph_result: GraphScoreResult,
    previous_baselines: Mapping[str, BaselinePreference] | None = None,
    onboarding_mbti_type: str | None = None,
) -> dict[str, FinalAxisPreference]:
    previous = previous_baselines or {}
    onboarding = extract_onboarding_baselines(onboarding_mbti_type)
    final_results: dict[str, FinalAxisPreference] = {}

    for axis in MBTI_AXES:
        graph_axis = graph_result.axis_results[axis]
        calculation_status = graph_axis.data_status

        if graph_axis.selected_letter is not None:
            selected_letter = graph_axis.selected_letter
            data_status = 'current_month'
            baseline = resolve_axis_baseline(
                axis=axis,
                previous_baselines=previous,
                onboarding_baselines=onboarding,
            )
            axis_avg = graph_axis.axis_avg
            axis_ratios = graph_axis.axis_ratios
        else:
            baseline = resolve_axis_baseline(
                axis=axis,
                previous_baselines=previous,
                onboarding_baselines=onboarding,
            )
            selected_letter = baseline.selected_letter if baseline else None
            if baseline is None:
                data_status = 'insufficient_axis_data'
            elif baseline.baseline_source == 'latest_monthly_result':
                data_status = 'carried_from_previous'
            else:
                data_status = 'carried_from_onboarding'
            axis_avg = baseline.axis_avg if baseline else graph_axis.axis_avg
            axis_ratios = (
                dict(baseline.axis_ratios)
                if baseline and baseline.axis_ratios
                else graph_axis.axis_ratios
            )

        final_results[axis] = FinalAxisPreference(
            axis=axis,
            qna_count=batch.axis_counts.get(axis, 0),
            scored_count=graph_axis.scored_count,
            axis_avg=axis_avg,
            axis_ratios=axis_ratios,
            previous_axis_avg=baseline.axis_avg if baseline else None,
            previous_axis_ratios=(
                dict(baseline.axis_ratios)
                if baseline and baseline.axis_ratios
                else {}
            ),
            selected_letter=selected_letter,
            data_status=data_status,
            calculation_status=calculation_status,
            baseline_letter=baseline.selected_letter if baseline else None,
            baseline_source=baseline.baseline_source if baseline else None,
            baseline_period_key=baseline.baseline_period_key if baseline else None,
        )

    return final_results


def combine_monthly_mbti(
    *,
    user_id: int,
    period_key: str,
    axis_results: Mapping[str, FinalAxisPreference],
    previous_estimated_mbti_type: str | None = None,
) -> MonthlyMbtiResult:
    letters: list[str] = []
    has_all_required_qna = True
    for axis in MBTI_AXES:
        selected_letter = axis_results[axis].selected_letter
        if selected_letter is None:
            return MonthlyMbtiResult(
                user_id=user_id,
                period_key=period_key,
                previous_estimated_mbti_type=previous_estimated_mbti_type,
                estimated_mbti_type=None,
                changed_axes=(),
                status='insufficient_data',
                axis_results=dict(axis_results),
            )
        # 모든 축에서 사용자가 실제로 5개 이상의 답변을 했는지 확인
        if axis_results[axis].qna_count < 5:
            has_all_required_qna = False
        letters.append(selected_letter)

    if not has_all_required_qna:
        return MonthlyMbtiResult(
            user_id=user_id,
            period_key=period_key,
            previous_estimated_mbti_type=previous_estimated_mbti_type,
            estimated_mbti_type=None,
            changed_axes=(),
            status='insufficient_data',
            axis_results=dict(axis_results),
        )

    estimated_mbti_type = ''.join(letters)
    changed_axes: list[str] = []
    if previous_estimated_mbti_type and len(previous_estimated_mbti_type) == 4:
        previous = previous_estimated_mbti_type.upper()
        for axis in MBTI_AXES:
            index = AXIS_TYPE_INDEX[axis]
            if previous[index] != axis_results[axis].selected_letter:
                changed_axes.append(axis)

    return MonthlyMbtiResult(
        user_id=user_id,
        period_key=period_key,
        previous_estimated_mbti_type=previous_estimated_mbti_type,
        estimated_mbti_type=estimated_mbti_type,
        changed_axes=tuple(changed_axes),
        status='complete',
        axis_results=dict(axis_results),
    )

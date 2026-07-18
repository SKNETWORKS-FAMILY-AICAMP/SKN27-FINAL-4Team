from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from mbti.services.monthly_questions import MBTI_AXES
from mbti.services.opening_rules import SecondaryOpeningResult


from mbti.services.mbti_utils import AXIS_LETTER_DIRECTIONS
TIE_EPSILON = 1e-12


class ResponseScoreLike(Protocol):
    axis: str
    score: float | None
    coding_status: str


@dataclass(frozen=True)
class AxisGraphScore:
    axis: str
    scored_count: int
    axis_avg: float | None
    axis_ratios: dict[str, float]
    selected_direction: str | None
    selected_letter: str | None
    next_step: str
    data_status: str


@dataclass(frozen=True)
class GraphScoreResult:
    axis_results: dict[str, AxisGraphScore]
    selected_axes: tuple[str, ...]
    tie_axes: tuple[str, ...]
    baseline_axes: tuple[str, ...]


def calculate_axis_graph_score(
    *,
    axis: str,
    scores: Iterable[float],
) -> AxisGraphScore:
    """Flow F->H->I core: convert coded score average into display ratios."""
    if axis not in MBTI_AXES:
        raise ValueError(f'Unsupported MBTI axis: {axis}')

    score_values = tuple(scores)
    if not score_values:
        raise ValueError('scores must contain at least one value.')

    axis_avg = sum(score_values) / len(score_values)
    axis_avg = max(-1.0, min(1.0, axis_avg))
    positive_ratio = (axis_avg + 1.0) / 2.0
    negative_ratio = 1.0 - positive_ratio
    letters = AXIS_LETTER_DIRECTIONS[axis]

    axis_ratios = {
        letters['negative']: negative_ratio,
        letters['positive']: positive_ratio,
    }

    if abs(positive_ratio - negative_ratio) <= TIE_EPSILON:
        selected_direction = None
        selected_letter = None
        next_step = 'apply_baseline_letter'
        data_status = 'tie_carried'
    elif positive_ratio > negative_ratio:
        selected_direction = 'positive'
        selected_letter = letters['positive']
        next_step = 'decide_current_month_preference'
        data_status = 'current_month'
    else:
        selected_direction = 'negative'
        selected_letter = letters['negative']
        next_step = 'decide_current_month_preference'
        data_status = 'current_month'

    return AxisGraphScore(
        axis=axis,
        scored_count=len(score_values),
        axis_avg=axis_avg,
        axis_ratios=axis_ratios,
        selected_direction=selected_direction,
        selected_letter=selected_letter,
        next_step=next_step,
        data_status=data_status,
    )


def calculate_monthly_graph_scores(
    *,
    secondary_opening: SecondaryOpeningResult,
    response_scores: Iterable[ResponseScoreLike],
) -> GraphScoreResult:
    """Flow F/H/I: calculate display scores and select current-month letters."""
    graph_score_axes = set(secondary_opening.graph_score_axes)
    score_values_by_axis: dict[str, list[float]] = {axis: [] for axis in MBTI_AXES}

    for response_score in response_scores:
        if response_score.axis not in graph_score_axes:
            continue
        if response_score.coding_status != 'coded':
            continue
        if response_score.score is None:
            continue
        score_values_by_axis[response_score.axis].append(float(response_score.score))

    axis_results: dict[str, AxisGraphScore] = {}
    selected_axes: list[str] = []
    tie_axes: list[str] = []
    baseline_axes: list[str] = list(secondary_opening.baseline_axes)

    for axis in MBTI_AXES:
        if axis not in graph_score_axes:
            secondary_axis = secondary_opening.axis_results[axis]
            axis_results[axis] = AxisGraphScore(
                axis=axis,
                scored_count=secondary_axis.scored_count,
                axis_avg=None,
                axis_ratios={},
                selected_direction=None,
                selected_letter=None,
                next_step='apply_baseline_letter',
                data_status=secondary_axis.data_status,
            )
            continue

        result = calculate_axis_graph_score(
            axis=axis,
            scores=score_values_by_axis[axis],
        )
        axis_results[axis] = result

        if result.selected_letter is None:
            tie_axes.append(axis)
            baseline_axes.append(axis)
        else:
            selected_axes.append(axis)

    return GraphScoreResult(
        axis_results=axis_results,
        selected_axes=tuple(selected_axes),
        tie_axes=tuple(tie_axes),
        baseline_axes=tuple(baseline_axes),
    )

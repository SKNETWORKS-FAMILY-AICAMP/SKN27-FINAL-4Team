from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from mbti.services.monthly_questions import MBTI_AXES, MbtiMonthlyQuestionBatch


DEFAULT_REQUIRED_QNA_COUNT = 5
DEFAULT_REQUIRED_SCORED_COUNT = 1


class ResponseScoreLike(Protocol):
    axis: str
    score: float | None
    coding_status: str


@dataclass(frozen=True)
class PrimaryAxisOpening:
    axis: str
    qna_count: int
    required_qna_count: int
    primary_open: bool
    next_step: str
    data_status: str


@dataclass(frozen=True)
class PrimaryOpeningResult:
    axis_results: dict[str, PrimaryAxisOpening]
    scoring_axes: tuple[str, ...]
    baseline_axes: tuple[str, ...]


@dataclass(frozen=True)
class SecondaryAxisOpening:
    axis: str
    primary_open: bool
    scored_count: int
    required_scored_count: int
    secondary_open: bool
    next_step: str
    data_status: str


@dataclass(frozen=True)
class SecondaryOpeningResult:
    axis_results: dict[str, SecondaryAxisOpening]
    graph_score_axes: tuple[str, ...]
    baseline_axes: tuple[str, ...]


def evaluate_primary_opening(
    axis_counts: Mapping[str, int],
    *,
    required_qna_count: int = DEFAULT_REQUIRED_QNA_COUNT,
) -> PrimaryOpeningResult:
    """Flow C: split axes into LLM scoring targets(D) or baseline targets(G)."""
    axis_results: dict[str, PrimaryAxisOpening] = {}
    scoring_axes: list[str] = []
    baseline_axes: list[str] = []

    for axis in MBTI_AXES:
        qna_count = axis_counts.get(axis, 0)
        primary_open = qna_count >= required_qna_count

        if primary_open:
            next_step = 'score_responses'
            data_status = 'primary_open'
            scoring_axes.append(axis)
        else:
            next_step = 'apply_baseline_letter'
            data_status = 'primary_closed'
            baseline_axes.append(axis)

        axis_results[axis] = PrimaryAxisOpening(
            axis=axis,
            qna_count=qna_count,
            required_qna_count=required_qna_count,
            primary_open=primary_open,
            next_step=next_step,
            data_status=data_status,
        )

    return PrimaryOpeningResult(
        axis_results=axis_results,
        scoring_axes=tuple(scoring_axes),
        baseline_axes=tuple(baseline_axes),
    )


def evaluate_primary_opening_from_batch(
    batch: MbtiMonthlyQuestionBatch,
    *,
    required_qna_count: int = DEFAULT_REQUIRED_QNA_COUNT,
) -> PrimaryOpeningResult:
    return evaluate_primary_opening(
        batch.axis_counts,
        required_qna_count=required_qna_count,
    )


def evaluate_secondary_opening(
    primary_opening: PrimaryOpeningResult,
    response_scores: Iterable[ResponseScoreLike],
    *,
    required_scored_count: int = DEFAULT_REQUIRED_SCORED_COUNT,
) -> SecondaryOpeningResult:
    """Flow E: split primary-open axes into graph-score targets(F) or baseline targets(G)."""
    scored_counts = {axis: 0 for axis in MBTI_AXES}

    primary_open_axes = set(primary_opening.scoring_axes)
    for response_score in response_scores:
        if response_score.axis not in primary_open_axes:
            continue
        if response_score.coding_status != 'coded':
            continue
        if response_score.score is None:
            continue

        scored_counts[response_score.axis] += 1

    axis_results: dict[str, SecondaryAxisOpening] = {}
    graph_score_axes: list[str] = []
    baseline_axes: list[str] = []

    for axis in MBTI_AXES:
        primary_axis = primary_opening.axis_results[axis]
        scored_count = scored_counts[axis]

        if not primary_axis.primary_open:
            secondary_open = False
            next_step = 'apply_baseline_letter'
            data_status = primary_axis.data_status
            baseline_axes.append(axis)
        else:
            secondary_open = scored_count >= required_scored_count
            if secondary_open:
                next_step = 'calculate_graph_score'
                data_status = 'secondary_open'
                graph_score_axes.append(axis)
            else:
                next_step = 'apply_baseline_letter'
                data_status = 'secondary_closed'
                baseline_axes.append(axis)

        axis_results[axis] = SecondaryAxisOpening(
            axis=axis,
            primary_open=primary_axis.primary_open,
            scored_count=scored_count,
            required_scored_count=required_scored_count,
            secondary_open=secondary_open,
            next_step=next_step,
            data_status=data_status,
        )

    return SecondaryOpeningResult(
        axis_results=axis_results,
        graph_score_axes=tuple(graph_score_axes),
        baseline_axes=tuple(baseline_axes),
    )

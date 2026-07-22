from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from mbti.services.baseline_sources import (
    UserBaselineSnapshot,
    load_user_baseline_snapshot,
)
from mbti.services.graph_scores import GraphScoreResult, calculate_monthly_graph_scores
from mbti.services.llm_config import MbtiScoringLlmConfig
from mbti.services.monthly_questions import (
    MbtiMonthlyQuestionBatch,
    load_monthly_question_batch,
)
from mbti.services.monthly_results import (
    FinalAxisPreference,
    MonthlyMbtiResult,
    build_previous_monthly_baselines,
    combine_monthly_mbti,
    finalize_monthly_axis_preferences,
)
from mbti.services.opening_rules import (
    PrimaryOpeningResult,
    SecondaryOpeningResult,
    evaluate_primary_opening_from_batch,
    evaluate_secondary_opening,
)
from mbti.services.reports import (
    EvidenceItem,
    MonthlyReport,
    MonthlyReportNarrativeClient,
    build_mypage_payload,
    generate_monthly_report,
    select_report_evidence,
)
from mbti.services.response_scoring import (
    MbtiResponseScore,
    MbtiScoringClient,
    score_primary_open_axes,
)


@dataclass(frozen=True)
class MonthlyMbtiPipelineResult:
    batch: MbtiMonthlyQuestionBatch
    primary_opening: PrimaryOpeningResult
    response_scores: tuple[MbtiResponseScore, ...]
    secondary_opening: SecondaryOpeningResult
    graph_result: GraphScoreResult
    final_axis_results: dict[str, FinalAxisPreference]
    monthly_result: MonthlyMbtiResult
    evidence_items: tuple[EvidenceItem, ...]
    report: MonthlyReport
    mypage_payload: dict


def run_monthly_mbti_pipeline(
    *,
    batch: MbtiMonthlyQuestionBatch,
    previous_axis_letters: Mapping[str, str] | None = None,
    previous_period_key: str | None = None,
    previous_estimated_mbti_type: str | None = None,
    onboarding_mbti_type: str | None = None,
    baseline_snapshot: UserBaselineSnapshot | None = None,
    scoring_client: MbtiScoringClient | None = None,
    scoring_config: MbtiScoringLlmConfig | None = None,
    report_client: MonthlyReportNarrativeClient | None = None,
) -> MonthlyMbtiPipelineResult:
    """Run the current MBTI flow from B through L for one user-month batch."""
    if baseline_snapshot is not None and baseline_snapshot.user_id != batch.user_id:
        raise ValueError('baseline_snapshot.user_id must match batch.user_id.')

    resolved_previous_axis_letters = (
        baseline_snapshot.previous_axis_letters
        if baseline_snapshot is not None
        else previous_axis_letters
    )
    resolved_previous_axis_period_keys = (
        baseline_snapshot.previous_axis_period_keys
        if baseline_snapshot is not None
        else None
    )
    resolved_previous_axis_avgs = (
        baseline_snapshot.previous_axis_avgs
        if baseline_snapshot is not None
        else None
    )
    resolved_previous_axis_ratios = (
        baseline_snapshot.previous_axis_ratios
        if baseline_snapshot is not None
        else None
    )
    resolved_previous_period_key = (
        baseline_snapshot.previous_period_key
        if baseline_snapshot is not None
        else previous_period_key
    )
    resolved_previous_estimated_mbti_type = (
        baseline_snapshot.previous_estimated_mbti_type
        if baseline_snapshot is not None
        else previous_estimated_mbti_type
    )
    resolved_onboarding_mbti_type = (
        baseline_snapshot.onboarding_mbti_type
        if baseline_snapshot is not None
        else onboarding_mbti_type
    )

    primary = evaluate_primary_opening_from_batch(batch)
    response_scores = score_primary_open_axes(
        batch=batch,
        primary_opening=primary,
        client=scoring_client,
        config=scoring_config,
    )
    secondary = evaluate_secondary_opening(primary, response_scores)
    graph = calculate_monthly_graph_scores(
        secondary_opening=secondary,
        response_scores=response_scores,
    )
    previous_baselines = build_previous_monthly_baselines(
        previous_axis_letters=resolved_previous_axis_letters or {},
        previous_period_key=resolved_previous_period_key,
        previous_axis_period_keys=resolved_previous_axis_period_keys,
        previous_axis_avgs=resolved_previous_axis_avgs,
        previous_axis_ratios=resolved_previous_axis_ratios,
    )
    final_axes = finalize_monthly_axis_preferences(
        batch=batch,
        graph_result=graph,
        previous_baselines=previous_baselines,
        onboarding_mbti_type=resolved_onboarding_mbti_type,
    )
    monthly = combine_monthly_mbti(
        user_id=batch.user_id,
        period_key=batch.period_key,
        axis_results=final_axes,
        previous_estimated_mbti_type=resolved_previous_estimated_mbti_type,
        previous_period_key=resolved_previous_period_key,
    )
    evidence = select_report_evidence(
        batch=batch,
        monthly_result=monthly,
        response_scores=response_scores,
    )
    report = generate_monthly_report(
        monthly_result=monthly,
        axis_results=final_axes,
        evidence_items=evidence,
        report_client=report_client,
    )
    payload = build_mypage_payload(
        monthly_result=monthly,
        report=report,
    )

    return MonthlyMbtiPipelineResult(
        batch=batch,
        primary_opening=primary,
        response_scores=response_scores,
        secondary_opening=secondary,
        graph_result=graph,
        final_axis_results=final_axes,
        monthly_result=monthly,
        evidence_items=evidence,
        report=report,
        mypage_payload=payload,
    )


def run_monthly_mbti_pipeline_for_user_month(
    *,
    user_id: int,
    period_key: str | None = None,
    scoring_client: MbtiScoringClient | None = None,
    scoring_config: MbtiScoringLlmConfig | None = None,
    report_client: MonthlyReportNarrativeClient | None = None,
    persist_result: bool = True,
) -> MonthlyMbtiPipelineResult:
    """DB-backed entry point for one user's monthly MBTI analysis."""
    batch = load_monthly_question_batch(
        user_id=user_id,
        period_key=period_key,
    )
    baseline_snapshot = load_user_baseline_snapshot(
        user_id=user_id,
        current_period_key=batch.period_key,
    )

    result = run_monthly_mbti_pipeline(
        batch=batch,
        baseline_snapshot=baseline_snapshot,
        scoring_client=scoring_client,
        scoring_config=scoring_config,
        report_client=report_client,
    )
    if persist_result:
        from mbti.services.persistence import save_monthly_pipeline_result

        save_monthly_pipeline_result(result)

    return result

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from mbti.constants import AXIS_LETTER_DIRECTIONS
from mbti.services.monthly_pipeline import MonthlyMbtiPipelineResult
from mbti.services.response_scoring import MbtiResponseScore


@dataclass(frozen=True)
class PersistedMonthlyMbtiResult:
    monthly_result_id: int
    report_id: int
    response_score_count: int
    axis_result_count: int


def _direction_from_score(axis: str, score: float | None) -> str:
    if score is None:
        return 'unknown'
    if score == 0:
        return 'neutral'

    directions = AXIS_LETTER_DIRECTIONS[axis]
    if score > 0:
        letter = directions['positive']
        strength = 'strong' if score >= 1.0 else 'slightly'
    else:
        letter = directions['negative']
        strength = 'strong' if score <= -1.0 else 'slightly'
    return f'{strength}_{letter}'


def _apply_fields(instance, fields: dict) -> None:
    for key, value in fields.items():
        setattr(instance, key, value)


def save_response_scores(
    *,
    response_scores: tuple[MbtiResponseScore, ...],
) -> int:
    from mbti.models import MbtiQuestionResponse, MbtiResponseScore as ScoreModel

    saved_count = 0
    now = timezone.now()
    question_by_id = {
        row.id: row
        for row in MbtiQuestionResponse.objects.filter(
            id__in=[score.response_id for score in response_scores],
        )
    }

    for score in response_scores:
        question = question_by_id.get(score.response_id)
        if question is None:
            continue

        defaults = {
            'user_id': question.user_id,
            'period_key': question.period_key,
            'axis': score.axis,
            'score': score.score,
            'direction': _direction_from_score(score.axis, score.score),
            'coding_status': score.coding_status,
            'evidence_span': question.answer_text if score.score is not None else None,
            'reason': score.reason,
            'model': score.model,
            'scored_at': now,
            'updated_at': now,
        }
        score_record, created = ScoreModel.objects.get_or_create(
            question_response=question,
            defaults={
                **defaults,
                'created_at': now,
            },
        )
        if not created:
            _apply_fields(score_record, defaults)
            score_record.save()
        saved_count += 1

    return saved_count


@transaction.atomic
def save_monthly_pipeline_result(
    result: MonthlyMbtiPipelineResult,
) -> PersistedMonthlyMbtiResult:
    from mbti.models import (
        MbtiMonthlyAxisResult,
        MbtiMonthlyReport,
        MbtiMonthlyResultRecord,
    )

    now = timezone.now()
    response_score_count = save_response_scores(
        response_scores=result.response_scores,
    )

    monthly_defaults = {
        'previous_estimated_mbti_type': result.monthly_result.previous_estimated_mbti_type,
        'previous_period_key': result.monthly_result.previous_period_key,
        'estimated_mbti_type': result.monthly_result.estimated_mbti_type,
        'changed_axes_json': list(result.monthly_result.changed_axes),
        'status': result.monthly_result.status,
        'analyzed_at': now,
        'updated_at': now,
    }
    monthly_record, created = MbtiMonthlyResultRecord.objects.get_or_create(
        user_id=result.monthly_result.user_id,
        period_key=result.monthly_result.period_key,
        defaults={
            **monthly_defaults,
            'created_at': now,
        },
    )
    if not created:
        _apply_fields(monthly_record, monthly_defaults)
        monthly_record.save()

    axis_result_count = 0
    for axis, axis_result in result.final_axis_results.items():
        axis_defaults = {
            'user_id': result.monthly_result.user_id,
            'period_key': result.monthly_result.period_key,
            'qna_count': axis_result.qna_count,
            'required_qna_count': 5,
            'primary_open': axis in result.primary_opening.scoring_axes,
            'scored_count': axis_result.scored_count,
            'required_scored_count': 1,
            'secondary_open': axis in result.secondary_opening.graph_score_axes,
            'axis_avg': axis_result.axis_avg,
            'axis_ratios_json': axis_result.axis_ratios,
            'selected_letter': axis_result.selected_letter,
            'data_status': axis_result.data_status,
            'calculation_status': axis_result.calculation_status,
            'baseline_letter': axis_result.baseline_letter,
            'baseline_source': axis_result.baseline_source,
            'baseline_period_key': axis_result.baseline_period_key,
            'updated_at': now,
        }
        axis_record, created = MbtiMonthlyAxisResult.objects.get_or_create(
            monthly_result=monthly_record,
            axis=axis,
            defaults={
                **axis_defaults,
                'created_at': now,
            },
        )
        if not created:
            _apply_fields(axis_record, axis_defaults)
            axis_record.save()
        axis_result_count += 1

    report_sections_json = [
        {
            'title': section.title,
            'content': section.content,
        }
        for section in result.report.report_sections
    ]
    evidence_items_json = [
        {
            'axis': item.axis,
            'question_response_id': item.question_response_id,
            'score': item.score,
            'question_text': item.question_text,
            'answer_text': item.answer_text,
            'evidence_span': item.evidence_span,
            'reason': item.reason,
            'role': item.role,
            'score_delta_contribution': item.score_delta_contribution,
            'impact_score': item.impact_score,
        }
        for item in result.report.evidence_items
    ]
    report_defaults = {
        'report_sections_json': report_sections_json,
        'evidence_items_json': evidence_items_json,
        'generated_at': now,
        'updated_at': now,
    }
    report_record, created = MbtiMonthlyReport.objects.get_or_create(
        monthly_result=monthly_record,
        defaults={
            **report_defaults,
            'created_at': now,
        },
    )
    if not created:
        _apply_fields(report_record, report_defaults)
        report_record.save()

    return PersistedMonthlyMbtiResult(
        monthly_result_id=monthly_record.id,
        report_id=report_record.id,
        response_score_count=response_score_count,
        axis_result_count=axis_result_count,
    )

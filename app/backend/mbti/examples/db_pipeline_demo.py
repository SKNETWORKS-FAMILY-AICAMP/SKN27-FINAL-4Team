from __future__ import annotations

import argparse
import csv
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import os
import sys
import uuid


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from mbti.examples.demo_data import load_backend_env, sample_monthly_question_responses  # noqa: E402


DEMO_USER_ID = 1
DEMO_PERIOD_KEY = '2026-06'
DEMO_CONVERSATION_ID = -2704
DEMO_LOG_DIR = Path(__file__).resolve().parent / 'logs'
DEMO_LOG_PATH = DEMO_LOG_DIR / 'db_pipeline_demo_runs.jsonl'
DEMO_RUN_SUMMARY_CSV_PATH = DEMO_LOG_DIR / 'db_pipeline_demo_result_summary.csv'
MBTI_AXIS_ORDER = ('IE', 'SN', 'TF', 'JP')
MBTI_AXIS_TYPE_INDEX = {
    'IE': 0,
    'SN': 1,
    'TF': 2,
    'JP': 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Seed demo MBTI Q&A into DB and run the DB-backed monthly MBTI pipeline.',
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use deterministic local demo scoring/report clients instead of real LangChain OpenAI calls.',
    )
    return parser.parse_args()


def setup_django() -> None:
    load_backend_env()
    import django

    django.setup()


def _serialize_datetime(value) -> str | None:
    return value.isoformat() if value else None


def _append_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open('a', encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def _display_score(axis_result) -> int | None:
    selected = axis_result.selected_letter
    ratios = axis_result.axis_ratios or {}
    if selected and selected in ratios:
        return round(float(ratios[selected]) * 100)
    return None


def _changed_preference_text(result) -> str:
    previous_type = result.monthly_result.previous_estimated_mbti_type
    current_type = result.monthly_result.estimated_mbti_type
    if not previous_type or not current_type:
        return ''

    changes = []
    for axis in result.monthly_result.changed_axes:
        index = MBTI_AXIS_TYPE_INDEX.get(axis)
        if index is None or index >= len(previous_type) or index >= len(current_type):
            continue
        changes.append(f'{axis}:{previous_type[index]}->{current_type[index]}')
    return '; '.join(changes)


def _write_demo_run_csv_logs(
    *,
    run_id: str,
    logged_at: str,
    demo_mode: str,
    result,
    monthly_record,
    frontend_payload: dict | None,
) -> None:
    row = {
        'run_id': run_id,
        'logged_at': logged_at,
        'demo_mode': demo_mode,
        'period_key': DEMO_PERIOD_KEY,
        'monthly_result_id': monthly_record.id,
        'previous_mbti': result.monthly_result.previous_estimated_mbti_type,
        'final_mbti': result.monthly_result.estimated_mbti_type,
        'changed_axes': ','.join(result.monthly_result.changed_axes),
        'changed_preferences': _changed_preference_text(result),
        'frontend_mbti': (
            frontend_payload.get('estimated_mbti_type')
            if frontend_payload else None
        ),
    }
    for axis in MBTI_AXIS_ORDER:
        axis_result = result.final_axis_results[axis]
        row[f'{axis}_letter'] = axis_result.selected_letter
        row[f'{axis}_display_score'] = _display_score(axis_result)
        row[f'{axis}_axis_avg'] = axis_result.axis_avg
        row[f'{axis}_data_status'] = axis_result.data_status

    _append_csv_rows(
        DEMO_RUN_SUMMARY_CSV_PATH,
        [
            'run_id',
            'logged_at',
            'demo_mode',
            'period_key',
            'monthly_result_id',
            'previous_mbti',
            'final_mbti',
            'changed_axes',
            'changed_preferences',
            'IE_letter',
            'IE_display_score',
            'IE_axis_avg',
            'IE_data_status',
            'SN_letter',
            'SN_display_score',
            'SN_axis_avg',
            'SN_data_status',
            'TF_letter',
            'TF_display_score',
            'TF_axis_avg',
            'TF_data_status',
            'JP_letter',
            'JP_display_score',
            'JP_axis_avg',
            'JP_data_status',
            'frontend_mbti',
        ],
        [row],
    )


def _write_demo_run_log(
    *,
    demo_mode: str,
    result,
    monthly_record,
    report,
    frontend_payload: dict | None,
) -> Path:
    run_id = uuid.uuid4().hex
    logged_at = datetime.now().isoformat(timespec='seconds')
    question_rows = [
        {
            'response_id': item.id,
            'axis': item.target_axis,
            'question_text': item.question_text,
            'answer_text': item.answer_text,
            'answered_at': _serialize_datetime(item.answered_at),
        }
        for axis_items in result.batch.axis_responses.values()
        for item in axis_items
    ]
    response_scores = [
        {
            'response_id': score.response_id,
            'axis': score.axis,
            'score': score.score,
            'coding_status': score.coding_status,
            'reason': score.reason,
            'model': score.model,
        }
        for score in result.response_scores
    ]
    axis_results = [
        {
            'axis': axis,
            'qna_count': axis_result.qna_count,
            'scored_count': axis_result.scored_count,
            'axis_avg': axis_result.axis_avg,
            'axis_ratios': axis_result.axis_ratios,
            'selected_letter': axis_result.selected_letter,
            'data_status': axis_result.data_status,
            'calculation_status': axis_result.calculation_status,
            'baseline_letter': axis_result.baseline_letter,
            'baseline_source': axis_result.baseline_source,
            'baseline_period_key': axis_result.baseline_period_key,
        }
        for axis, axis_result in result.final_axis_results.items()
    ]
    evidence_items = [
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
        for item in result.evidence_items
    ]
    payload = {
        'run_id': run_id,
        'logged_at': logged_at,
        'demo_mode': demo_mode,
        'user_id': DEMO_USER_ID,
        'period_key': DEMO_PERIOD_KEY,
        'conversation_id': DEMO_CONVERSATION_ID,
        'db': {
            'monthly_result_id': monthly_record.id,
            'report_id': report.id,
        },
        'input': {
            'axis_counts': result.batch.axis_counts,
            'total_count': result.batch.total_count,
            'question_rows': question_rows,
        },
        'pipeline': {
            'primary_scoring_axes': result.primary_opening.scoring_axes,
            'primary_baseline_axes': result.primary_opening.baseline_axes,
            'secondary_graph_score_axes': result.secondary_opening.graph_score_axes,
            'secondary_baseline_axes': result.secondary_opening.baseline_axes,
            'response_scores': response_scores,
            'axis_results': axis_results,
            'monthly_result': {
                'previous_estimated_mbti_type': result.monthly_result.previous_estimated_mbti_type,
                'estimated_mbti_type': result.monthly_result.estimated_mbti_type,
                'changed_axes': result.monthly_result.changed_axes,
                'status': result.monthly_result.status,
            },
            'evidence_items': evidence_items,
            'report_sections': [
                {
                    'title': section.title,
                    'content': section.content,
                }
                for section in result.report.report_sections
            ],
        },
        'frontend_payload': {
            'source': frontend_payload.get('source') if frontend_payload else None,
            'previous_estimated_mbti_type': (
                frontend_payload.get('previous_estimated_mbti_type')
                if frontend_payload else None
            ),
            'estimated_mbti_type': (
                frontend_payload.get('estimated_mbti_type')
                if frontend_payload else None
            ),
            'changed_axes': frontend_payload.get('changed_axes') if frontend_payload else None,
            'mbti_data': frontend_payload.get('mbti_data') if frontend_payload else None,
        },
    }
    DEMO_LOG_DIR.mkdir(parents=True, exist_ok=True)
    with DEMO_LOG_PATH.open('a', encoding='utf-8') as log_file:
        log_file.write(json.dumps(payload, ensure_ascii=False, default=str))
        log_file.write('\n')
    _write_demo_run_csv_logs(
        run_id=run_id,
        logged_at=logged_at,
        demo_mode=demo_mode,
        result=result,
        monthly_record=monthly_record,
        frontend_payload=frontend_payload,
    )
    return DEMO_LOG_PATH


def seed_demo_rows() -> None:
    from django.utils import timezone
    from mbti.models import (
        MbtiMonthlyAnalysisJob,
        MbtiMonthlyAxisResult,
        MbtiMonthlyReport,
        MbtiMonthlyResultRecord,
        MbtiOnboardingProfile,
        MbtiQuestionResponse,
        MbtiResponseScore,
    )

    now = timezone.now()
    demo_questions = MbtiQuestionResponse.objects.filter(
        user_id=DEMO_USER_ID,
        period_key=DEMO_PERIOD_KEY,
        conversation_id=DEMO_CONVERSATION_ID,
    )
    demo_question_ids = list(demo_questions.values_list('id', flat=True))
    if demo_question_ids:
        MbtiResponseScore.objects.filter(question_response_id__in=demo_question_ids).delete()

    demo_monthlies = MbtiMonthlyResultRecord.objects.filter(
        user_id=DEMO_USER_ID,
        period_key=DEMO_PERIOD_KEY,
    )
    demo_monthly_ids = list(demo_monthlies.values_list('id', flat=True))
    if demo_monthly_ids:
        MbtiMonthlyReport.objects.filter(monthly_result_id__in=demo_monthly_ids).delete()
        MbtiMonthlyAxisResult.objects.filter(monthly_result_id__in=demo_monthly_ids).delete()
        MbtiMonthlyAnalysisJob.objects.filter(monthly_result_id__in=demo_monthly_ids).update(monthly_result=None)
        demo_monthlies.delete()

    demo_questions.delete()

    for row in sample_monthly_question_responses():
        if row.target_axis not in {'IE', 'SN', 'TF', 'JP'}:
            continue
        answered_at = timezone.make_aware(row.answered_at) if row.answered_at.tzinfo is None else row.answered_at
        MbtiQuestionResponse.objects.create(
            user_id=DEMO_USER_ID,
            conversation_id=DEMO_CONVERSATION_ID,
            question_message_id=None,
            answer_message_id=None,
            question_text=row.question_text,
            answer_text=row.answer_text,
            target_axis=row.target_axis,
            period_key=DEMO_PERIOD_KEY,
            answered_at=answered_at,
            created_at=now,
        )

    onboarding, created = MbtiOnboardingProfile.objects.get_or_create(
        user_id=DEMO_USER_ID,
        defaults={
            'mbti_type': 'INFP',
            'created_at': now,
            'updated_at': now,
        },
    )
    if not created:
        onboarding.mbti_type = 'INFJ'
        onboarding.updated_at = now
        onboarding.save()


def main() -> None:
    args = parse_args()
    setup_django()

    from mbti.models import (
        MbtiMonthlyAxisResult,
        MbtiMonthlyReport,
        MbtiMonthlyResultRecord,
        MbtiQuestionResponse,
        MbtiResponseScore,
    )
    from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline_for_user_month
    from mbti.services.dashboard_payload import load_latest_frontend_payload

    if args.mock:
        from mbti.examples.monthly_demo_payload import DemoReportClient, DemoScoringClient

        scoring_client = DemoScoringClient()
        report_client = DemoReportClient()
        demo_mode = 'mock'
    else:
        if not os.getenv('OPENAI_API_KEY'):
            raise RuntimeError(
                'OPENAI_API_KEY is required for the real LLM demo. '
                'Use --mock to run without LLM calls.'
            )
        if importlib.util.find_spec('langchain_openai') is None:
            raise RuntimeError(
                'langchain-openai is required for the real LLM demo. '
                'Install app/backend/requirements.txt or use --mock.'
            )
        scoring_client = None
        report_client = None
        demo_mode = 'real_langchain_openai'

    seed_demo_rows()
    result = run_monthly_mbti_pipeline_for_user_month(
        user_id=DEMO_USER_ID,
        period_key=DEMO_PERIOD_KEY,
        scoring_client=scoring_client,
        report_client=report_client,
        persist_result=True,
    )

    monthly_record = MbtiMonthlyResultRecord.objects.get(
        user_id=DEMO_USER_ID,
        period_key=DEMO_PERIOD_KEY,
    )
    report = MbtiMonthlyReport.objects.get(monthly_result=monthly_record)
    frontend_payload = load_latest_frontend_payload(
        user_id=DEMO_USER_ID,
        period_key=DEMO_PERIOD_KEY,
    )
    log_path = _write_demo_run_log(
        demo_mode=demo_mode,
        result=result,
        monthly_record=monthly_record,
        report=report,
        frontend_payload=frontend_payload,
    )

    print('[DB DEMO INPUT]')
    print(f'user_id: {DEMO_USER_ID}')
    print(f'period_key: {DEMO_PERIOD_KEY}')
    print(f'demo_mode: {demo_mode}')
    print(f'question_rows: {MbtiQuestionResponse.objects.filter(user_id=DEMO_USER_ID, period_key=DEMO_PERIOD_KEY).count()}')

    print('\n[PIPELINE RESULT]')
    print(f'estimated_mbti_type: {result.monthly_result.estimated_mbti_type}')
    print(f'previous_estimated_mbti_type: {result.monthly_result.previous_estimated_mbti_type}')
    print(f'changed_axes: {result.monthly_result.changed_axes}')
    print(f'status: {result.monthly_result.status}')
    print(f'primary_scoring_axes: {result.primary_opening.scoring_axes}')
    print(f'secondary_graph_score_axes: {result.secondary_opening.graph_score_axes}')

    print('\n[DB OUTPUT]')
    print(f'monthly_result_id: {monthly_record.id}')
    print(f'response_scores: {MbtiResponseScore.objects.filter(user_id=DEMO_USER_ID, period_key=DEMO_PERIOD_KEY).count()}')
    for status in ('coded', 'insufficient_context', 'failed'):
        count = MbtiResponseScore.objects.filter(
            user_id=DEMO_USER_ID,
            period_key=DEMO_PERIOD_KEY,
            coding_status=status,
        ).count()
        print(f'response_scores.{status}: {count}')
    print(f'axis_results: {MbtiMonthlyAxisResult.objects.filter(monthly_result=monthly_record).count()}')
    print(f'report_id: {report.id}')
    print(f'demo_log_path: {log_path}')
    print(f'demo_csv_path: {DEMO_RUN_SUMMARY_CSV_PATH}')

    print('\n[REPORT SECTIONS]')
    for section in report.report_sections_json:
        print(f'- {section["title"]}: {section["content"]}')


if __name__ == '__main__':
    main()

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
from pathlib import Path
import os
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from mbti.examples.demo_data import load_backend_env, sample_monthly_question_responses  # noqa: E402


DEMO_USER_ID = 1
DEMO_PERIOD_KEY = '2026-06'
DEMO_CONVERSATION_ID = -2704


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

    print('\n[REPORT SECTIONS]')
    for section in report.report_sections_json:
        print(f'- {section["title"]}: {section["content"]}')


if __name__ == '__main__':
    main()

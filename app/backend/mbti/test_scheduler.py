from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from mbti.models import (
    MbtiMonthlyAnalysisJob,
    MbtiMonthlyResultRecord,
    MbtiOnboardingProfile,
    MbtiQuestionResponse,
)
from mbti.services.job_service import (
    build_user_month_input_hash,
    enqueue_user_month_job,
    process_next_job,
)
from mbti.services.llm_config import build_scoring_llm_config
from mbti.services.scheduler import next_monthly_run, previous_period_key
from user.models import User


class MonthlySchedulerTimeTests(TestCase):
    def test_previous_period_and_next_run_use_seoul_month_boundary(self):
        reference = timezone.make_aware(datetime(2026, 7, 22, 12, 0))

        self.assertEqual(previous_period_key(reference), '2026-06')
        self.assertEqual(
            next_monthly_run(reference, hour=0, minute=5).isoformat(),
            '2026-08-01T00:05:00+09:00',
        )

    def test_next_run_on_first_before_schedule_is_same_day(self):
        reference = timezone.make_aware(datetime(2026, 8, 1, 0, 1))

        self.assertEqual(
            next_monthly_run(reference, hour=0, minute=5).isoformat(),
            '2026-08-01T00:05:00+09:00',
        )


class MonthlyAnalysisJobTests(TestCase):
    period_key = '2026-06'

    def setUp(self):
        self.user = User.objects.create_user(
            email='monthly-job@example.com',
            password='password',
            nickname='월간작업',
            onboarding_done=True,
        )
        MbtiOnboardingProfile.objects.create(
            user_id=self.user.id,
            mbti_type='INTJ',
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self._add_answers(5)

    def _add_answers(self, count, axis='IE'):
        for index in range(count):
            answered_at = timezone.now()
            MbtiQuestionResponse.objects.create(
                user_id=self.user.id,
                question_text=f'질문 {axis} {index}',
                answer_text=f'답변 {axis} {index}',
                target_axis=axis,
                period_key=self.period_key,
                answered_at=answered_at,
                created_at=answered_at,
            )

    def test_enqueue_is_idempotent_for_same_input(self):
        first = enqueue_user_month_job(
            user_id=self.user.id,
            period_key=self.period_key,
            trigger_source='monthly_scheduler',
        )
        second = enqueue_user_month_job(
            user_id=self.user.id,
            period_key=self.period_key,
            trigger_source='monthly_scheduler',
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.job.id, second.job.id)
        self.assertEqual(MbtiMonthlyAnalysisJob.objects.count(), 1)

    def test_new_answer_changes_hash_and_supersedes_pending_job(self):
        first = enqueue_user_month_job(
            user_id=self.user.id,
            period_key=self.period_key,
            trigger_source='monthly_scheduler',
        )
        self._add_answers(1)
        second = enqueue_user_month_job(
            user_id=self.user.id,
            period_key=self.period_key,
            trigger_source='monthly_scheduler',
        )

        first.job.refresh_from_db()
        self.assertNotEqual(first.job.input_hash, second.job.input_hash)
        self.assertEqual(first.job.status, 'skipped')
        self.assertEqual(second.job.status, 'pending')

    def test_input_hash_does_not_store_plain_answer_in_job(self):
        config = build_scoring_llm_config()
        digest = build_user_month_input_hash(
            user_id=self.user.id,
            period_key=self.period_key,
            scoring_model=config.model,
            prompt_version='test-v1',
        )

        self.assertEqual(len(digest), 64)
        self.assertNotIn('답변', digest)

    @patch('mbti.services.monthly_pipeline.run_monthly_mbti_pipeline_for_user_month')
    def test_worker_completes_a_queued_job(self, mock_run):
        queued = enqueue_user_month_job(
            user_id=self.user.id,
            period_key=self.period_key,
            trigger_source='monthly_scheduler',
        )

        def persist_result(**kwargs):
            MbtiMonthlyResultRecord.objects.create(
                user_id=kwargs['user_id'],
                period_key=kwargs['period_key'],
                estimated_mbti_type='INTJ',
                status='complete',
                analyzed_at=timezone.now(),
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
            return SimpleNamespace()

        mock_run.side_effect = persist_result
        processed = process_next_job(max_retries=0)

        self.assertEqual(processed.id, queued.job.id)
        self.assertEqual(processed.status, 'completed')
        self.assertIsNotNone(processed.monthly_result_id)
        mock_run.assert_called_once_with(
            user_id=self.user.id,
            period_key=self.period_key,
            persist_result=True,
        )

    @patch('mbti.services.monthly_pipeline.run_monthly_mbti_pipeline_for_user_month')
    def test_worker_marks_exhausted_job_failed(self, mock_run):
        mock_run.side_effect = RuntimeError('provider unavailable')
        enqueue_user_month_job(
            user_id=self.user.id,
            period_key=self.period_key,
            trigger_source='monthly_scheduler',
        )

        processed = process_next_job(max_retries=0)

        self.assertEqual(processed.status, 'failed')
        self.assertEqual(processed.retry_count, 1)
        self.assertIn('provider unavailable', processed.error_message)


class MonthlyAnalysisApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='monthly-api@example.com',
            password='password',
            nickname='월간API',
            onboarding_done=True,
        )
        self.client.force_authenticate(self.user)
        MbtiOnboardingProfile.objects.create(
            user_id=self.user.id,
            mbti_type='ENFP',
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

    def test_post_enqueues_analysis_and_get_exposes_job_status(self):
        period_key = timezone.localtime().strftime('%Y-%m')
        for index in range(5):
            MbtiQuestionResponse.objects.create(
                user_id=self.user.id,
                question_text=f'질문 {index}',
                answer_text=f'답변 {index}',
                target_axis='IE',
                period_key=period_key,
                answered_at=timezone.now(),
                created_at=timezone.now(),
            )

        response = self.client.post('/api/mbti/monthly-analysis/', {}, format='json')
        dashboard = self.client.get('/api/mbti/monthly-demo/')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['analysis_job']['status'], 'pending')

    def test_post_does_not_enqueue_when_primary_threshold_is_missing(self):
        response = self.client.post('/api/mbti/monthly-analysis/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'not_eligible')
        self.assertEqual(MbtiMonthlyAnalysisJob.objects.count(), 0)

    def test_get_remains_read_only_when_legacy_force_query_is_supplied(self):
        period_key = timezone.localtime().strftime('%Y-%m')
        for index in range(5):
            MbtiQuestionResponse.objects.create(
                user_id=self.user.id,
                question_text=f'질문 {index}',
                answer_text=f'답변 {index}',
                target_axis='IE',
                period_key=period_key,
                answered_at=timezone.now(),
                created_at=timezone.now(),
            )

        response = self.client.get('/api/mbti/monthly-demo/', {'force': 'true'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(MbtiMonthlyAnalysisJob.objects.count(), 0)

    def test_post_requeues_a_failed_job_for_the_same_input(self):
        period_key = timezone.localtime().strftime('%Y-%m')
        for index in range(5):
            MbtiQuestionResponse.objects.create(
                user_id=self.user.id,
                question_text=f'질문 {index}',
                answer_text=f'답변 {index}',
                target_axis='IE',
                period_key=period_key,
                answered_at=timezone.now(),
                created_at=timezone.now(),
            )
        queued = enqueue_user_month_job(
            user_id=self.user.id,
            period_key=period_key,
            trigger_source='dashboard_on_demand',
        )
        MbtiMonthlyAnalysisJob.objects.filter(id=queued.job.id).update(
            status='failed',
            retry_count=3,
            finished_at=timezone.now(),
            error_message='provider unavailable',
        )

        response = self.client.post('/api/mbti/monthly-analysis/', {}, format='json')
        queued.job.refresh_from_db()

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(queued.job.status, 'pending')
        self.assertEqual(queued.job.retry_count, 0)
        self.assertIsNone(queued.job.error_message)

    def test_dashboard_without_period_returns_latest_completed_month(self):
        latest_period = previous_period_key()
        MbtiMonthlyResultRecord.objects.create(
            user_id=self.user.id,
            period_key=latest_period,
            estimated_mbti_type='ENFP',
            status='complete',
            analyzed_at=timezone.now(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        dashboard = self.client.get('/api/mbti/monthly-demo/')
        current_period = timezone.localtime().strftime('%Y-%m')
        current_dashboard = self.client.get(
            '/api/mbti/monthly-demo/',
            {'period_key': current_period},
        )

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['period_key'], latest_period)
        self.assertEqual(current_dashboard.status_code, 200)
        self.assertEqual(current_dashboard.data['period_key'], current_period)
        self.assertEqual(current_dashboard.data['status'], 'preparing')

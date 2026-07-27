from datetime import date, datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from mindreport.services.runtime import _schedule_due, generate_scheduled_reports


class MindReportScheduleBoundaryTests(SimpleTestCase):
    def test_weekly_schedule_becomes_due_on_monday_at_configured_time(self):
        before = timezone.make_aware(datetime(2026, 7, 27, 0, 4))
        due = timezone.make_aware(datetime(2026, 7, 27, 0, 5))

        self.assertFalse(
            _schedule_due(period_type='week', hour=0, minute=5, reference=before)
        )
        self.assertTrue(
            _schedule_due(period_type='week', hour=0, minute=5, reference=due)
        )

    def test_monthly_schedule_becomes_due_on_first_day(self):
        before = timezone.make_aware(datetime(2026, 8, 1, 0, 9))
        due = timezone.make_aware(datetime(2026, 8, 1, 0, 10))

        self.assertFalse(
            _schedule_due(period_type='month', hour=0, minute=10, reference=before)
        )
        self.assertTrue(
            _schedule_due(period_type='month', hour=0, minute=10, reference=due)
        )


class MindReportScheduledGenerationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='mindreport-scheduler@example.com',
            password='password',
            nickname='리포트 스케줄러 테스트',
        )

    @patch('mindreport.services.runtime._active_user_ids')
    @patch('mindreport.services.runtime.MindReportService')
    def test_weekly_generation_uses_the_previous_completed_week(
        self,
        service_class,
        active_user_ids,
    ):
        active_user_ids.return_value = [self.user.pk]
        service_class.return_value.ensure_period_report.return_value = {'id': 'weekly'}

        count = generate_scheduled_reports(
            period_type='week',
            reference_date=date(2026, 7, 27),
        )

        self.assertEqual(count, 1)
        service_class.return_value.ensure_period_report.assert_called_once_with(
            user=self.user,
            period_type='week',
            period_name='주간',
            target_date=date(2026, 7, 26),
        )

    @patch('mindreport.services.runtime._active_user_ids')
    @patch('mindreport.services.runtime.MindReportService')
    def test_monthly_generation_uses_the_previous_calendar_month(
        self,
        service_class,
        active_user_ids,
    ):
        active_user_ids.return_value = [self.user.pk]
        service_class.return_value.ensure_period_report.return_value = {'id': 'monthly'}

        count = generate_scheduled_reports(
            period_type='month',
            reference_date=date(2026, 8, 1),
        )

        self.assertEqual(count, 1)
        service_class.return_value.ensure_period_report.assert_called_once_with(
            user=self.user,
            period_type='month',
            period_name='월간',
            year=2026,
            month=7,
        )

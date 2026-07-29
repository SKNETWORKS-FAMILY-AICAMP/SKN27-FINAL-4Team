"""Background scheduling for completed weekly and monthly mind reports."""

from __future__ import annotations

from datetime import timedelta
import logging
import os
from pathlib import Path
import sys
import threading
import time

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.utils import timezone

from chat.models import ChatMessage
from mindreport.constants import PERIOD_LABELS, PERIOD_MONTH, PERIOD_WEEK
from mindreport.services.periods import (
    last_completed_month,
    last_completed_week_target_date,
    resolve_period_window,
)
from mindreport.services.report_service import MindReportService


logger = logging.getLogger(__name__)

_start_lock = threading.Lock()
_started = False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def should_start_background_service() -> bool:
    if not _env_bool('MINDREPORT_BACKGROUND_ENABLED', True):
        return False

    executable = Path(sys.argv[0]).name.lower()
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if executable in {'manage.py', 'django-admin', 'django-admin.exe'}:
        if command != 'runserver':
            return False
        if '--noreload' not in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return False
    return True


def _schedule_due(*, period_type: str, hour: int, minute: int, reference=None) -> bool:
    local_now = timezone.localtime(reference or timezone.now())
    if period_type == PERIOD_WEEK:
        due_date = local_now.date() - timedelta(days=local_now.weekday())
    elif period_type == PERIOD_MONTH:
        due_date = local_now.date().replace(day=1)
    else:
        raise ValueError(f'Unsupported mindreport period_type: {period_type}')
    due_at = local_now.replace(
        year=due_date.year,
        month=due_date.month,
        day=due_date.day,
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    return local_now >= due_at


def _active_user_ids(*, period_type: str, target_date=None, year=None, month=None):
    window = resolve_period_window(
        period_type=period_type,
        target_date=target_date,
        year=year,
        month=month,
    )
    return list(
        ChatMessage.objects.filter(
            role='user',
            session__user__isnull=False,
            session__user__is_active=True,
            created_at__gte=window.start,
            created_at__lt=window.end_exclusive,
        )
        .values_list('session__user_id', flat=True)
        .distinct()
    )


def generate_scheduled_reports(*, period_type: str, reference_date=None) -> int:
    """Generate one missing report per active user for the last completed period."""
    resolved_date = reference_date or timezone.localdate()
    if period_type == PERIOD_WEEK:
        period_kwargs = {
            'target_date': last_completed_week_target_date(resolved_date),
        }
    elif period_type == PERIOD_MONTH:
        year, month = last_completed_month(resolved_date)
        period_kwargs = {'year': year, 'month': month}
    else:
        raise ValueError(f'Unsupported mindreport period_type: {period_type}')

    user_ids = _active_user_ids(period_type=period_type, **period_kwargs)
    # Materialize the queryset before processing users. QuerySet.iterator() keeps
    # a database cursor open, but the per-user cleanup below may close its
    # connection when CONN_MAX_AGE is 0 (Django's default).
    users = list(
        get_user_model().objects.filter(pk__in=user_ids, is_active=True)
    )
    generated_count = 0
    failed_count = 0
    service = MindReportService()
    for user in users:
        try:
            result = service.ensure_period_report(
                user=user,
                period_type=period_type,
                period_name=PERIOD_LABELS[period_type],
                **period_kwargs,
            )
            generated_count += int(result is not None)
        except Exception:
            failed_count += 1
            logger.exception(
                'Scheduled mind report failed user=%s period=%s.',
                user.pk,
                period_type,
            )
        finally:
            close_old_connections()
    if failed_count:
        raise RuntimeError(
            f'{failed_count} scheduled mind report generation(s) failed.'
        )
    return generated_count


def _background_loop():
    weekly_hour = int(os.environ.get('MINDREPORT_WEEKLY_RUN_HOUR', '0'))
    weekly_minute = int(os.environ.get('MINDREPORT_WEEKLY_RUN_MINUTE', '5'))
    monthly_hour = int(os.environ.get('MINDREPORT_MONTHLY_RUN_HOUR', '0'))
    monthly_minute = int(os.environ.get('MINDREPORT_MONTHLY_RUN_MINUTE', '10'))
    poll_seconds = max(
        5,
        int(os.environ.get('MINDREPORT_SCHEDULER_POLL_SECONDS', '60')),
    )
    last_week_key = None
    last_month_key = None

    if not 0 <= weekly_hour <= 23 or not 0 <= monthly_hour <= 23:
        logger.error('Mind report scheduler hour must be between 0 and 23.')
        return
    if not 0 <= weekly_minute <= 59 or not 0 <= monthly_minute <= 59:
        logger.error('Mind report scheduler minute must be between 0 and 59.')
        return

    logger.info(
        'Mind report scheduler started (weekly Monday %02d:%02d, monthly day 1 %02d:%02d).',
        weekly_hour,
        weekly_minute,
        monthly_hour,
        monthly_minute,
    )
    while True:
        try:
            close_old_connections()
            local_date = timezone.localdate()
            week_target = last_completed_week_target_date(local_date)
            week_key = week_target.isoformat()
            if (
                week_key != last_week_key
                and _schedule_due(
                    period_type=PERIOD_WEEK,
                    hour=weekly_hour,
                    minute=weekly_minute,
                )
            ):
                count = generate_scheduled_reports(
                    period_type=PERIOD_WEEK,
                    reference_date=local_date,
                )
                last_week_key = week_key
                logger.info(
                    'Weekly mind reports generated: period=%s count=%s.',
                    week_key,
                    count,
                )

            month_key = last_completed_month(local_date)
            if (
                month_key != last_month_key
                and _schedule_due(
                    period_type=PERIOD_MONTH,
                    hour=monthly_hour,
                    minute=monthly_minute,
                )
            ):
                count = generate_scheduled_reports(
                    period_type=PERIOD_MONTH,
                    reference_date=local_date,
                )
                last_month_key = month_key
                logger.info(
                    'Monthly mind reports generated: period=%04d-%02d count=%s.',
                    month_key[0],
                    month_key[1],
                    count,
                )
        except Exception:
            close_old_connections()
            logger.exception('Mind report scheduler iteration failed; retrying.')
        time.sleep(poll_seconds)


def start_background_service() -> bool:
    global _started
    if not should_start_background_service():
        return False
    with _start_lock:
        if _started:
            return False
        thread = threading.Thread(
            target=_background_loop,
            name='mindreport-background',
            daemon=True,
        )
        thread.start()
        _started = True
        return True

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
import threading
import time

from django.db import close_old_connections, connection
from django.utils import timezone

from mbti.services.job_service import (
    enqueue_monthly_jobs,
    process_next_job,
    recover_stale_running_jobs,
)
from mbti.services.scheduler import previous_period_key


logger = logging.getLogger(__name__)

_start_lock = threading.Lock()
_started = False
_ANALYSIS_JOB_TABLE = 'mbti_monthly_analysis_jobs'


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def should_start_background_service() -> bool:
    if not _env_bool('MBTI_BACKGROUND_ENABLED', True):
        return False

    executable = Path(sys.argv[0]).name.lower()
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if executable in {'manage.py', 'django-admin', 'django-admin.exe'}:
        if command != 'runserver':
            return False
        # Django 개발 서버의 autoreloader 부모 프로세스에서는 시작하지 않는다.
        if '--noreload' not in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return False
    return True


def _monthly_schedule_is_due(*, hour: int, minute: int) -> bool:
    local_now = timezone.localtime()
    due_at = local_now.replace(
        day=1,
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    return local_now >= due_at


def _analysis_job_table_exists() -> bool:
    """Return False while deployments are waiting for the MBTI migration."""
    return _ANALYSIS_JOB_TABLE in connection.introspection.table_names()


def _background_loop():
    hour = int(os.environ.get('MBTI_MONTHLY_RUN_HOUR', '0'))
    minute = int(os.environ.get('MBTI_MONTHLY_RUN_MINUTE', '5'))
    poll_seconds = max(1, int(os.environ.get('MBTI_WORKER_POLL_SECONDS', '5')))
    between_jobs = max(0, int(os.environ.get('MBTI_WORKER_BETWEEN_JOBS_SECONDS', '2')))
    max_retries = max(0, int(os.environ.get('MBTI_WORKER_MAX_RETRIES', '2')))
    retry_delay = max(1, int(os.environ.get('MBTI_WORKER_RETRY_DELAY_SECONDS', '900')))
    stale_after = max(60, int(os.environ.get('MBTI_WORKER_STALE_AFTER_SECONDS', '3600')))
    last_scheduled_period = None
    stale_jobs_recovered = False
    table_wait_logged = False
    table_ready = False

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        logger.error('Invalid MBTI monthly schedule: hour=%s minute=%s', hour, minute)
        return

    logger.info(
        'MBTI background service started (monthly=%02d:%02d Asia/Seoul).',
        hour,
        minute,
    )
    while True:
        try:
            close_old_connections()
            if not table_ready:
                table_ready = _analysis_job_table_exists()
            if not table_ready:
                if not table_wait_logged:
                    logger.warning(
                        'MBTI background service is waiting for migration 0003; '
                        'run `python manage.py migrate`.'
                    )
                    table_wait_logged = True
                time.sleep(max(5, poll_seconds))
                continue
            table_wait_logged = False
            if not stale_jobs_recovered:
                recovered = recover_stale_running_jobs(stale_after_seconds=stale_after)
                stale_jobs_recovered = True
                if recovered:
                    logger.warning('Recovered %s stale MBTI job(s).', recovered)
            if _monthly_schedule_is_due(hour=hour, minute=minute):
                target_period = previous_period_key()
                if target_period != last_scheduled_period:
                    result = enqueue_monthly_jobs(period_key=target_period)
                    last_scheduled_period = target_period
                    logger.info(
                        'MBTI monthly jobs scheduled: period=%s created=%s existing=%s',
                        result.period_key,
                        result.created_count,
                        result.existing_count,
                    )

            job = process_next_job(
                max_retries=max_retries,
                retry_delay_seconds=retry_delay,
            )
            close_old_connections()
            if job is None:
                time.sleep(poll_seconds)
            elif between_jobs:
                time.sleep(between_jobs)
        except Exception:
            close_old_connections()
            logger.exception('MBTI background service iteration failed; retrying.')
            time.sleep(max(5, poll_seconds))


def start_background_service() -> bool:
    global _started
    if not should_start_background_service():
        return False
    with _start_lock:
        if _started:
            return False
        thread = threading.Thread(
            target=_background_loop,
            name='mbti-monthly-background',
            daemon=True,
        )
        thread.start()
        _started = True
        return True

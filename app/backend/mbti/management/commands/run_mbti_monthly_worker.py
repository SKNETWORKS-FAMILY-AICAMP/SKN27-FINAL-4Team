import os
import time

from django.core.management.base import BaseCommand

from mbti.services.job_service import process_next_job, recover_stale_running_jobs


class Command(BaseCommand):
    help = '예약된 MBTI 월간 분석 작업을 한 번에 하나씩 처리합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        poll_seconds = max(1, int(os.environ.get('MBTI_WORKER_POLL_SECONDS', '5')))
        max_retries = max(0, int(os.environ.get('MBTI_WORKER_MAX_RETRIES', '2')))
        retry_delay = max(1, int(os.environ.get('MBTI_WORKER_RETRY_DELAY_SECONDS', '900')))
        stale_after = max(60, int(os.environ.get('MBTI_WORKER_STALE_AFTER_SECONDS', '3600')))
        recovered = recover_stale_running_jobs(stale_after_seconds=stale_after)
        if recovered:
            self.stdout.write(f'Recovered {recovered} stale MBTI job(s).')

        while True:
            job = process_next_job(
                max_retries=max_retries,
                retry_delay_seconds=retry_delay,
            )
            if job is not None:
                self.stdout.write(
                    f'MBTI job id={job.id} user={job.user_id} '
                    f'period={job.period_key} status={job.status}'
                )
            if options['once']:
                return
            if job is None:
                time.sleep(poll_seconds)

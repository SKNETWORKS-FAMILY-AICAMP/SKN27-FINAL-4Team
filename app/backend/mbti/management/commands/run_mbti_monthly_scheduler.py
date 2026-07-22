import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from mbti.services.scheduler import next_monthly_run, previous_period_key, seconds_until


class Command(BaseCommand):
    help = '매월 1일 지정 시각에 지난달 MBTI 분석 작업을 예약합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--no-catch-up', action='store_true')

    def _schedule(self):
        period_key = previous_period_key()
        call_command('schedule_mbti_monthly', period_key=period_key)

    def handle(self, *args, **options):
        hour = int(os.environ.get('MBTI_MONTHLY_RUN_HOUR', '0'))
        minute = int(os.environ.get('MBTI_MONTHLY_RUN_MINUTE', '5'))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError('MBTI monthly schedule must use a valid hour and minute.')

        if options['once']:
            self._schedule()
            return

        if not options['no_catch_up']:
            self.stdout.write('MBTI scheduler startup catch-up check')
            self._schedule()

        while True:
            target = next_monthly_run(hour=hour, minute=minute)
            self.stdout.write(
                f'Next MBTI monthly schedule: {target.isoformat()} '
                f'(now={timezone.localtime().isoformat()})'
            )
            while seconds_until(target) > 0:
                time.sleep(min(60, seconds_until(target)))
            self._schedule()

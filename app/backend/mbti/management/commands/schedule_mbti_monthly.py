from django.core.management.base import BaseCommand, CommandError

from mbti.services.job_service import enqueue_monthly_jobs
from mbti.services.scheduler import previous_period_key


class Command(BaseCommand):
    help = '지난달(또는 지정 월)의 MBTI 분석 대상자를 선별해 작업 큐에 넣습니다.'

    def add_arguments(self, parser):
        parser.add_argument('--period-key')
        parser.add_argument('--retry-failed', action='store_true')

    def handle(self, *args, **options):
        period_key = options.get('period_key') or previous_period_key()
        try:
            result = enqueue_monthly_jobs(
                period_key=period_key,
                trigger_source='monthly_scheduler',
                revive_failed=options['retry_failed'],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f'period={result.period_key} candidates={result.candidate_count} '
                f'created={result.created_count} existing={result.existing_count} '
                f'ineligible={result.ineligible_count}'
            )
        )

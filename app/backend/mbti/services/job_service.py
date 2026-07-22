from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import os
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import Count
from django.utils import timezone

from mbti.constants import (
    DEFAULT_MONTHLY_PROMPT_VERSION,
    DEFAULT_REQUIRED_QNA_COUNT,
    MBTI_AXES,
)
from mbti.models import (
    MbtiMonthlyAnalysisJob,
    MbtiMonthlyResultRecord,
    MbtiOnboardingProfile,
    MbtiQuestionResponse,
)
from mbti.services.baseline_sources import (
    extract_axis_letters_from_mbti_type,
    load_user_baseline_snapshot,
)
from mbti.services.llm_config import build_scoring_llm_config
from mbti.services.monthly_questions import resolve_month_period


@dataclass(frozen=True)
class EnqueueResult:
    job: MbtiMonthlyAnalysisJob | None
    created: bool
    eligible: bool
    reason: str


@dataclass(frozen=True)
class BatchEnqueueResult:
    period_key: str
    candidate_count: int
    created_count: int
    existing_count: int
    ineligible_count: int


def _prompt_version() -> str:
    return (
        os.environ.get('MBTI_MONTHLY_PROMPT_VERSION', '').strip()
        or DEFAULT_MONTHLY_PROMPT_VERSION
    )


def _validate_period_key(period_key: str) -> str:
    resolved, _, _ = resolve_month_period(period_key=period_key)
    return resolved


def _axis_counts(*, user_id: int, period_key: str) -> dict[str, int]:
    counts = {axis: 0 for axis in MBTI_AXES}
    rows = (
        MbtiQuestionResponse.objects
        .filter(user_id=user_id, period_key=period_key, target_axis__in=MBTI_AXES)
        .values('target_axis')
        .annotate(total=Count('id'))
    )
    for row in rows:
        counts[row['target_axis']] = row['total']
    return counts


def is_user_month_eligible(*, user_id: int, period_key: str) -> tuple[bool, str]:
    period_key = _validate_period_key(period_key)
    user_exists = get_user_model().objects.filter(id=user_id, is_active=True).exists()
    if not user_exists:
        return False, 'inactive_or_missing_user'

    counts = _axis_counts(user_id=user_id, period_key=period_key)
    scoring_axes = {
        axis for axis, count in counts.items()
        if count >= DEFAULT_REQUIRED_QNA_COUNT
    }
    if not scoring_axes:
        return False, 'no_axis_reached_primary_threshold'

    baseline = load_user_baseline_snapshot(
        user_id=user_id,
        current_period_key=period_key,
    )
    available_baseline_axes = set(baseline.previous_axis_letters)
    available_baseline_axes.update(
        extract_axis_letters_from_mbti_type(baseline.onboarding_mbti_type)
    )
    missing_axes = [
        axis for axis in MBTI_AXES
        if axis not in scoring_axes and axis not in available_baseline_axes
    ]
    if missing_axes:
        return False, 'missing_baseline_for_closed_axes:' + ','.join(missing_axes)
    return True, 'eligible'


def _serialize_datetime(value):
    return value.isoformat() if value is not None else None


def build_user_month_input_hash(
    *,
    user_id: int,
    period_key: str,
    scoring_model: str,
    prompt_version: str,
) -> str:
    period_key = _validate_period_key(period_key)
    responses = list(
        MbtiQuestionResponse.objects
        .filter(user_id=user_id, period_key=period_key, target_axis__in=MBTI_AXES)
        .order_by('id')
        .values(
            'id',
            'target_axis',
            'question_text',
            'answer_text',
            'answered_at',
        )
    )
    for response in responses:
        response['answered_at'] = _serialize_datetime(response['answered_at'])

    onboarding = (
        MbtiOnboardingProfile.objects
        .filter(user_id=user_id)
        .order_by('-updated_at', '-id')
        .values('id', 'mbti_type', 'updated_at')
        .first()
    )
    if onboarding:
        onboarding['updated_at'] = _serialize_datetime(onboarding['updated_at'])

    previous = (
        MbtiMonthlyResultRecord.objects
        .filter(user_id=user_id, period_key__lt=period_key, status='complete')
        .prefetch_related('axis_results')
        .order_by('-period_key', '-id')
        .first()
    )
    previous_payload = None
    if previous is not None:
        previous_payload = {
            'id': previous.id,
            'period_key': previous.period_key,
            'estimated_mbti_type': previous.estimated_mbti_type,
            'updated_at': _serialize_datetime(previous.updated_at),
            'axes': [
                {
                    'axis': axis.axis,
                    'selected_letter': axis.selected_letter,
                    'axis_avg': axis.axis_avg,
                    'axis_ratios': axis.axis_ratios_json,
                }
                for axis in previous.axis_results.all().order_by('axis')
            ],
        }

    payload = {
        'user_id': user_id,
        'period_key': period_key,
        'scoring_model': scoring_model,
        'prompt_version': prompt_version,
        'responses': responses,
        'onboarding': onboarding,
        'previous': previous_payload,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


@transaction.atomic
def enqueue_user_month_job(
    *,
    user_id: int,
    period_key: str,
    trigger_source: str,
    scheduled_at=None,
    revive_failed: bool = False,
) -> EnqueueResult:
    period_key = _validate_period_key(period_key)
    eligible, reason = is_user_month_eligible(user_id=user_id, period_key=period_key)
    if not eligible:
        return EnqueueResult(job=None, created=False, eligible=False, reason=reason)

    scoring_model = build_scoring_llm_config().model
    prompt_version = _prompt_version()
    input_hash = build_user_month_input_hash(
        user_id=user_id,
        period_key=period_key,
        scoring_model=scoring_model,
        prompt_version=prompt_version,
    )
    now = timezone.now()

    MbtiMonthlyAnalysisJob.objects.filter(
        user_id=user_id,
        period_key=period_key,
        status='pending',
    ).exclude(input_hash=input_hash).update(
        status='skipped',
        finished_at=now,
        error_message='superseded_by_newer_input',
    )

    job, created = MbtiMonthlyAnalysisJob.objects.get_or_create(
        user_id=user_id,
        period_key=period_key,
        input_hash=input_hash,
        prompt_version=prompt_version,
        defaults={
            'status': 'pending',
            'trigger_source': trigger_source,
            'scoring_model': scoring_model,
            'scheduled_at': scheduled_at or now,
        },
    )
    if not created and revive_failed and job.status == 'failed':
        job.status = 'pending'
        job.trigger_source = trigger_source
        job.retry_count = 0
        job.scheduled_at = scheduled_at or now
        job.started_at = None
        job.finished_at = None
        job.error_message = None
        job.save()
    return EnqueueResult(job=job, created=created, eligible=True, reason='eligible')


def eligible_user_ids(period_key: str) -> list[int]:
    period_key = _validate_period_key(period_key)
    threshold_rows = (
        MbtiQuestionResponse.objects
        .filter(period_key=period_key, target_axis__in=MBTI_AXES)
        .values('user_id', 'target_axis')
        .annotate(total=Count('id'))
        .filter(total__gte=DEFAULT_REQUIRED_QNA_COUNT)
        .values_list('user_id', flat=True)
        .distinct()
    )
    active_ids = get_user_model().objects.filter(
        id__in=threshold_rows,
        is_active=True,
    ).values_list('id', flat=True)
    return list(active_ids)


def enqueue_monthly_jobs(
    *,
    period_key: str,
    trigger_source: str = 'monthly_scheduler',
    user_ids: Iterable[int] | None = None,
    revive_failed: bool = False,
) -> BatchEnqueueResult:
    period_key = _validate_period_key(period_key)
    candidates = list(user_ids) if user_ids is not None else eligible_user_ids(period_key)
    created_count = 0
    existing_count = 0
    ineligible_count = 0
    for user_id in candidates:
        result = enqueue_user_month_job(
            user_id=user_id,
            period_key=period_key,
            trigger_source=trigger_source,
            revive_failed=revive_failed,
        )
        if not result.eligible:
            ineligible_count += 1
        elif result.created:
            created_count += 1
        else:
            existing_count += 1
    return BatchEnqueueResult(
        period_key=period_key,
        candidate_count=len(candidates),
        created_count=created_count,
        existing_count=existing_count,
        ineligible_count=ineligible_count,
    )


def _claim_next_job():
    now = timezone.now()
    with transaction.atomic():
        queryset = MbtiMonthlyAnalysisJob.objects.filter(
            status='pending',
            scheduled_at__lte=now,
        ).order_by('scheduled_at', 'id')
        if connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        else:
            queryset = queryset.select_for_update()
        job = queryset.first()
        if job is None:
            return None
        job.status = 'running'
        job.started_at = now
        job.finished_at = None
        job.error_message = None
        job.save(update_fields=[
            'status', 'started_at', 'finished_at', 'error_message', 'updated_at',
        ])
        return job


def _mark_job_skipped(job, reason: str):
    now = timezone.now()
    MbtiMonthlyAnalysisJob.objects.filter(id=job.id).update(
        status='skipped',
        finished_at=now,
        error_message=reason[:2000],
        updated_at=now,
    )


def _mark_job_failed_or_retry(job, exc: Exception, *, max_retries: int, retry_delay_seconds: int):
    now = timezone.now()
    retry_count = job.retry_count + 1
    will_retry = retry_count <= max_retries
    MbtiMonthlyAnalysisJob.objects.filter(id=job.id).update(
        status='pending' if will_retry else 'failed',
        retry_count=retry_count,
        scheduled_at=now + timedelta(seconds=retry_delay_seconds) if will_retry else job.scheduled_at,
        finished_at=None if will_retry else now,
        error_message=f'{exc.__class__.__name__}: {exc}'[:2000],
        updated_at=now,
    )


def process_next_job(*, max_retries: int = 2, retry_delay_seconds: int = 900):
    job = _claim_next_job()
    if job is None:
        return None

    current_hash = build_user_month_input_hash(
        user_id=job.user_id,
        period_key=job.period_key,
        scoring_model=job.scoring_model,
        prompt_version=job.prompt_version,
    )
    if current_hash != job.input_hash:
        _mark_job_skipped(job, 'input_changed_after_job_was_queued')
        return MbtiMonthlyAnalysisJob.objects.get(id=job.id)

    try:
        from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline_for_user_month

        pipeline_result = run_monthly_mbti_pipeline_for_user_month(
            user_id=job.user_id,
            period_key=job.period_key,
            persist_result=True,
        )
        monthly_result = MbtiMonthlyResultRecord.objects.get(
            user_id=job.user_id,
            period_key=job.period_key,
        )
        response_scores = tuple(getattr(pipeline_result, 'response_scores', ()))
        if response_scores and all(score.coding_status == 'failed' for score in response_scores):
            raise RuntimeError('all LLM scoring responses failed')

        pipeline_status = getattr(
            getattr(pipeline_result, 'monthly_result', None),
            'status',
            monthly_result.status,
        )
        now = timezone.now()
        MbtiMonthlyAnalysisJob.objects.filter(id=job.id).update(
            status='completed' if pipeline_status == 'complete' else 'skipped',
            monthly_result=monthly_result,
            finished_at=now,
            error_message=None if pipeline_status == 'complete' else pipeline_status,
            updated_at=now,
        )
    except Exception as exc:
        _mark_job_failed_or_retry(
            job,
            exc,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
        )
    return MbtiMonthlyAnalysisJob.objects.get(id=job.id)


def recover_stale_running_jobs(*, stale_after_seconds: int = 3600) -> int:
    now = timezone.now()
    stale_before = now - timedelta(seconds=stale_after_seconds)
    return MbtiMonthlyAnalysisJob.objects.filter(
        status='running',
        started_at__lt=stale_before,
    ).update(
        status='pending',
        scheduled_at=now,
        started_at=None,
        error_message='recovered_stale_running_job',
        updated_at=now,
    )


def latest_job_payload(*, user_id: int, period_key: str) -> dict | None:
    job = (
        MbtiMonthlyAnalysisJob.objects
        .filter(user_id=user_id, period_key=period_key)
        .order_by('-created_at', '-id')
        .first()
    )
    if job is None:
        return None
    return {
        'id': job.id,
        'period_key': job.period_key,
        'status': job.status,
        'trigger_source': job.trigger_source,
        'retry_count': job.retry_count,
        'scheduled_at': _serialize_datetime(job.scheduled_at),
        'started_at': _serialize_datetime(job.started_at),
        'finished_at': _serialize_datetime(job.finished_at),
        'error_message': 'analysis_failed' if job.status == 'failed' else None,
    }

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.db import DatabaseError

from mbti.services.baseline_sources import load_onboarding_snapshot
from mbti.constants import AXIS_TYPE_INDEX, MBTI_AXES, MBTI_TYPE_DESCRIPTIONS
from mbti.services.mbti_utils import is_valid_mbti_type




def _axis_score_for_frontend(axis_result) -> int:
    selected = axis_result.selected_letter
    ratios = axis_result.axis_ratios_json or {}
    if selected and selected in ratios:
        return round(float(ratios[selected]) * 100)
    return 50


def _onboarding_payload(user_id: int) -> dict[str, Any]:
    try:
        onboarding = load_onboarding_snapshot(user_id=user_id)
    except (AppRegistryNotReady, ImproperlyConfigured, DatabaseError):
        onboarding = None
    onboarding_type = is_valid_mbti_type(onboarding.mbti_type if onboarding else None)
    description = MBTI_TYPE_DESCRIPTIONS.get(onboarding_type or '')

    if description:
        return {
            'type': onboarding_type,
            'period': '온보딩 기준',
            'description': description['summary'],
            'report': description['points'],
        }

    return {
        'type': '----',
        'period': '온보딩 기준',
        'description': '온보딩 MBTI 기준값이 아직 확인되지 않았습니다.',
        'report': [
            '온보딩 MBTI가 저장되면 해당 유형의 일반 성향, 강점, 대인관계, 의사결정 방식, 주의점을 보여줍니다.',
        ],
    }


def _changed_axes_from_types(
    previous_type: str | None,
    current_type: str | None,
) -> list[str]:
    if not is_valid_mbti_type(previous_type) or not is_valid_mbti_type(current_type):
        return []

    changed_axes = []
    for axis in MBTI_AXES:
        index = AXIS_TYPE_INDEX[axis]
        if previous_type[index] != current_type[index]:
            changed_axes.append(axis)
    return changed_axes


def _axis_sort_key(axis_result) -> int:
    try:
        return MBTI_AXES.index(axis_result.axis)
    except ValueError:
        return len(MBTI_AXES)


def build_frontend_payload_from_monthly_record(monthly_result) -> dict[str, Any]:
    axis_results = sorted(
        list(monthly_result.axis_results.all()),
        key=_axis_sort_key,
    )
    report = getattr(monthly_result, 'report', None)
    report_sections = report.report_sections_json if report else []
    onboarding_payload = _onboarding_payload(monthly_result.user_id)
    onboarding_type = is_valid_mbti_type(onboarding_payload['type'])
    current_type = is_valid_mbti_type(monthly_result.estimated_mbti_type) or '----'
    if monthly_result.status != 'complete' or current_type == '----':
        return build_frontend_preparing_payload(
            user_id=monthly_result.user_id,
            period_key=monthly_result.period_key,
        )

    stored_previous_type = is_valid_mbti_type(monthly_result.previous_estimated_mbti_type)
    previous_type = stored_previous_type or onboarding_type or '----'
    previous_label = (
        f'{monthly_result.previous_period_key} 기준'
        if monthly_result.previous_period_key
        else '온보딩 기준'
        if previous_type == onboarding_type and onboarding_type
        else '이전 기준 없음'
    )
    changed_axes = (
        monthly_result.changed_axes_json
        if monthly_result.changed_axes_json
        else _changed_axes_from_types(previous_type, current_type)
    )

    return {
        'view_mode': 'monthly_analysis',
        'status': monthly_result.status or 'ready',
        'period_key': monthly_result.period_key,
        'source': 'database_monthly_result',
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'has_monthly_analysis': True,
        'onboarding_mbti_type': onboarding_payload['type'],
        'previous_estimated_mbti_type': previous_type,
        'estimated_mbti_type': current_type,
        'changed_axes': changed_axes,
        'mbti_view_mode': 'onboardingNext',
        'mbti_data': {
            'onboarding': onboarding_payload,
            'previous': {
                'type': previous_type,
                'monthLabel': previous_label,
            },
            'current': {
                'type': current_type,
                'monthLabel': f'{monthly_result.period_key} 월간 분석',
                'axes': [
                    {
                        'label': axis.selected_letter or '-',
                        'pair': axis.axis,
                        'score': _axis_score_for_frontend(axis),
                    }
                    for axis in axis_results
                ],
            },
            'report': [
                f'[{section.get("title", "")}] {section.get("content", "")}'
                for section in report_sections
            ],
        },
        'raw': {
            'user_id': monthly_result.user_id,
            'period_key': monthly_result.period_key,
            'stored_previous_estimated_mbti_type': monthly_result.previous_estimated_mbti_type,
            'previous_estimated_mbti_type': previous_type,
            'previous_basis': (
                'monthly_result'
                if stored_previous_type and monthly_result.previous_period_key
                else 'onboarding'
                if onboarding_type
                else None
            ),
            'estimated_mbti_type': monthly_result.estimated_mbti_type,
            'changed_axes': changed_axes,
            'status': monthly_result.status,
            'axis_results': [
                {
                    'axis': axis.axis,
                    'qna_count': axis.qna_count,
                    'scored_count': axis.scored_count,
                    'axis_avg': axis.axis_avg,
                    'axis_ratios': axis.axis_ratios_json,
                    'selected_letter': axis.selected_letter,
                    'data_status': axis.data_status,
                    'baseline_source': axis.baseline_source,
                    'baseline_letter': axis.baseline_letter,
                    'baseline_period_key': axis.baseline_period_key,
                }
                for axis in axis_results
            ],
            'report_sections': report_sections,
            'evidence_items': report.evidence_items_json if report else [],
        },
    }


def build_frontend_preparing_payload(
    *,
    user_id: int,
    period_key: str | None = None,
) -> dict[str, Any]:
    onboarding_payload = _onboarding_payload(user_id)
    onboarding_type = is_valid_mbti_type(onboarding_payload['type'])
    previous_type = onboarding_type or '----'
    resolved_period_key = period_key or datetime.now().strftime('%Y-%m')

    return {
        'view_mode': 'monthly_analysis_preparing',
        'status': 'preparing',
        'period_key': resolved_period_key,
        'source': 'empty_monthly_result',
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'has_monthly_analysis': False,
        'onboarding_mbti_type': onboarding_payload['type'],
        'previous_estimated_mbti_type': previous_type,
        'estimated_mbti_type': '----',
        'changed_axes': [],
        'mbti_view_mode': 'onboardingNext',
        'mbti_data': {
            'onboarding': onboarding_payload,
            'previous': {
                'type': previous_type,
                'monthLabel': '온보딩 기준' if onboarding_type else '이전 기준 없음',
            },
            'current': {
                'type': '----',
                'monthLabel': f'{resolved_period_key} 월간 분석 준비 중',
                'axes': [],
            },
            'report': [],
        },
        'raw': {
            'user_id': user_id,
            'period_key': resolved_period_key,
            'previous_basis': 'onboarding' if onboarding_type else None,
            'status': 'preparing',
            'axis_results': [],
            'report_sections': [],
            'evidence_items': [],
        },
    }


def load_latest_frontend_payload(
    *,
    user_id: int,
    period_key: str | None = None,
) -> dict[str, Any] | None:
    from mbti.models import MbtiMonthlyResultRecord

    queryset = (
        MbtiMonthlyResultRecord.objects
        .filter(user_id=user_id)
        .prefetch_related('axis_results')
        .select_related('report')
        .order_by('-period_key', '-id')
    )
    if period_key:
        queryset = queryset.filter(period_key=period_key)

    monthly_result = queryset.first()
    if monthly_result is None:
        return build_frontend_preparing_payload(user_id=user_id, period_key=period_key)

    return build_frontend_payload_from_monthly_record(monthly_result)

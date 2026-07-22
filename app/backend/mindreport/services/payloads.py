"""Build and normalize the public mind-report payload contract."""

from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

from mindreport.constants import (
    EMOTION_STATE_ICONS,
    FRONTEND_LIST_FIELDS,
    FRONTEND_REQUIRED_TEXT_FIELDS,
    GRAPH_FALLBACK_PAYLOAD_STATUS,
    GRAPH_REPORT_PAYLOAD_STATUSES,
    PERIOD_MONTH,
)
from mindreport.exceptions import MindReportPayloadError
from mindreport.models import MindReport
from mindreport.services.periods import period_label, period_range_text
from mindreport.services.scoring import emotion_state_from_score


def build_report_payload_from_state(state: dict[str, Any]) -> dict[str, Any]:
    """Convert validated graph outputs into the stable frontend contract."""
    scoring_result = state['scoring_result']
    cause_result = state['cause_result']
    narrative = state['narrative_result'].narrative

    stress_causes = [
        keyword.keyword
        for keyword in cause_result.cause_keywords
        if keyword.cause_type == 'stress'
    ]
    relief_causes = [
        keyword.keyword
        for keyword in cause_result.cause_keywords
        if keyword.cause_type == 'relief'
    ]
    cause_labels = [
        {
            'keyword': label['keyword'],
            'causeType': label['cause_type'],
            'emphasis': label['emphasis'],
            'displayWeight': label['display_weight'],
        }
        for label in state['label_result'].labels
    ]
    emotions = []
    for score in scoring_result.emotion_scores:
        emotion_state = emotion_state_from_score(score.emotion_score)
        emotions.append({
            'day': f'{score.source_date.day:02d}일',
            'icon': EMOTION_STATE_ICONS[emotion_state],
            'emotion_state': emotion_state,
            'emotion_label': score.emotion_label,
        })

    recommendations = list(narrative.action_recommendations)
    recipient_name = report_recipient_name(state['user'])
    return normalize_public_payload({
        'id': f"report-{state['user'].id}-{int(timezone.now().timestamp())}",
        'type': report_period_name(state),
        'range': report_range_text(state),
        'title': narrative.title,
        'summary': narrative.summary,
        '_recipientName': recipient_name,
        'comfortMessage': select_comfort_message(
            summary=narrative.summary,
            analysis=narrative.analysis_sentences,
            recommendations=recommendations,
            recipient_name=recipient_name,
        ),
        'stressCauses': stress_causes,
        'reliefCauses': relief_causes,
        'causeLabels': cause_labels,
        'emotions': emotions,
        'analysis': list(narrative.analysis_sentences) + recommendations,
        'recommendations': recommendations,
        'is_fallback': False,
        'is_safety_response': False,
    })


def payload_from_graph_state(state: dict[str, Any]) -> dict[str, Any]:
    """Select the graph's terminal payload and enforce its public shape."""
    status = state.get('status')
    if status in GRAPH_REPORT_PAYLOAD_STATUSES:
        payload = state.get('report_payload')
    elif status == GRAPH_FALLBACK_PAYLOAD_STATUS:
        payload = state.get('fallback_payload')
    else:
        payload = None

    if not payload:
        raise MindReportPayloadError(
            f'Mind report graph ended without a payload (status={status!r}).'
        )
    return normalize_public_payload(payload)


def normalize_public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    recipient_name = str(normalized.pop('_recipientName', '') or '').strip()
    missing_text_fields = [
        field
        for field in FRONTEND_REQUIRED_TEXT_FIELDS
        if not isinstance(normalized.get(field), str)
        or not normalized[field].strip()
    ]
    if missing_text_fields:
        raise MindReportPayloadError(
            'Mind report payload has missing or invalid fields: '
            + ', '.join(missing_text_fields)
        )
    for field in FRONTEND_LIST_FIELDS:
        value = normalized.get(field)
        normalized[field] = list(value) if isinstance(value, (list, tuple)) else []
    normalized['comfortMessage'] = select_comfort_message(
        summary=normalized['summary'],
        analysis=normalized['analysis'],
        recommendations=normalized['recommendations'],
        recipient_name=recipient_name,
    )
    normalized['is_fallback'] = bool(normalized.get('is_fallback', False))
    normalized['is_safety_response'] = bool(
        normalized.get('is_safety_response', False)
    )
    return normalized


def serialize_report(report: MindReport) -> dict[str, Any]:
    is_monthly = report.report_type.startswith(period_label(PERIOD_MONTH))
    prefix = 'monthly' if is_monthly else 'weekly'
    if report.is_safety_response:
        prefix = f'safety-{prefix}'
    elif report.is_fallback:
        prefix = f'fallback-{prefix}'
    recipient_name = report_recipient_name(report.user)
    return {
        'id': f'{prefix}-{report.id}',
        'type': report.report_type,
        'range': report.range_text,
        'title': report.title,
        'summary': report.summary,
        'comfortMessage': select_comfort_message(
            summary=report.summary,
            analysis=report.analysis,
            recommendations=report.recommendations,
            recipient_name=recipient_name,
        ),
        'stressCauses': list(report.stress_causes),
        'reliefCauses': list(report.relief_causes),
        'causeLabels': list(report.cause_labels),
        'emotions': list(report.emotions),
        'analysis': list(report.analysis),
        'recommendations': list(report.recommendations),
        'is_fallback': report.is_fallback,
        'is_safety_response': report.is_safety_response,
    }


def select_comfort_message(
    *,
    summary: str,
    analysis,
    recommendations,
    recipient_name: str = '',
) -> str:
    """Select a natural comfort line from fields already stored on the report."""
    clean_summary = str(summary or '').strip()
    recommendation_set = {
        str(item or '').strip()
        for item in recommendations or []
        if str(item or '').strip()
    }
    candidates = [
        str(item or '').strip()
        for item in analysis or []
        if str(item or '').strip()
        and str(item or '').strip() not in recommendation_set
        and not str(item or '').strip().startswith('✅')
        and '왜 추천하나요?' not in str(item)
        and '어떻게 시작할까요?' not in str(item)
    ]
    if not candidates:
        return clean_summary

    for candidate in reversed(candidates):
        sentences = [
            sentence.strip()
            for sentence in re.split(r'(?<=[.!?。])\s+', candidate)
            if sentence.strip()
        ]
        for sentence in reversed(sentences):
            compact_length = len(re.sub(r'\s+', '', sentence))
            has_recipient_name = (
                recipient_name in sentence
                if recipient_name
                else bool(re.search(r'[^\s,]{1,30}님(?:은|는|이|가|에게|의|께)', sentence))
            )
            if 20 <= compact_length <= 60 and has_recipient_name:
                return sentence
    return clean_summary


def report_recipient_name(user) -> str:
    nickname = str(getattr(user, 'nickname', '') or '').strip()
    if not nickname:
        nickname = '회원'
    return nickname if nickname.endswith('님') else f'{nickname}님'


def report_period_name(state: dict[str, Any]) -> str:
    return period_label(state['period_type'], state.get('period_name', ''))


def report_range_text(state: dict[str, Any]) -> str:
    return period_range_text(
        period_type=state['period_type'],
        target_date=state.get('target_date'),
        year=state.get('year'),
        month=state.get('month'),
    )

"""Build and normalize the public mind-report payload contract."""

from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

from mindreport.constants import (
    EMOTION_SCORE_NEGATIVE_MAX,
    EMOTION_SCORE_POSITIVE_MIN,
    FRONTEND_LIST_FIELDS,
    FRONTEND_REQUIRED_TEXT_FIELDS,
    GRAPH_FALLBACK_PAYLOAD_STATUS,
    GRAPH_REPORT_PAYLOAD_STATUSES,
    PERIOD_MONTH,
)
from mindreport.exceptions import MindReportPayloadError
from mindreport.models import MindReport
from mindreport.services.periods import period_label, period_range_text


def _emotion_scale_payload() -> dict[str, float]:
    return {
        'heavyMax': float(EMOTION_SCORE_NEGATIVE_MAX),
        'lightMin': float(EMOTION_SCORE_POSITIVE_MIN),
    }


def _normalize_suggestion_cards(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, (list, tuple)):
        return []

    cards = []
    for item in value:
        if not isinstance(item, dict):
            continue
        card = {
            'title': ' '.join(str(item.get('title') or '').split()),
            'reason': ' '.join(str(item.get('reason') or '').split()),
            'how': ' '.join(str(item.get('how') or '').split()),
            'sourceCandidate': str(
                item.get('sourceCandidate') or item.get('source_candidate') or ''
            ).strip(),
            'relatedCause': str(
                item.get('relatedCause') or item.get('related_cause') or ''
            ).strip(),
            'timing': str(item.get('timing') or '').strip(),
        }
        if card['title'] and card['reason']:
            cards.append(card)
        if len(cards) >= 3:
            break
    return cards


def _suggestion_cards_to_analysis(cards: list[dict[str, str]]) -> list[str]:
    lines = []
    for card in cards:
        lines.extend((
            f"✅ {card['title']}",
            f"  - 왜 추천하나요?: {card['reason']}",
        ))
        if card['how']:
            lines.append(f"  - 어떻게 시작할까요?: {card['how']}")
        if card['relatedCause']:
            lines.append(f"  - 연결된 마음의 원인: {card['relatedCause']}")
        if card['timing']:
            lines.append(f"  - 제안 시점: {card['timing']}")
        if card['sourceCandidate']:
            lines.append(f"  - 감정 흐름 후보: {card['sourceCandidate']}")
    return lines


def _suggestion_cards_from_analysis(analysis: Any) -> list[dict[str, str]]:
    if not isinstance(analysis, (list, tuple)):
        return []

    cards = []
    current = None
    label_fields = (
        ('왜 추천하나요?', 'reason'),
        ('웹 추천 이유', 'reason'),
        ('어떻게 시작할까요?', 'how'),
        ('가볍게 시작하기', 'how'),
        ('연결된 마음의 원인', 'relatedCause'),
        ('제안 시점', 'timing'),
        ('감정 흐름 후보', 'sourceCandidate'),
    )
    for raw in analysis:
        line = str(raw or '').strip()
        if line.startswith('✅'):
            current = {
                'title': line.removeprefix('✅').strip(),
                'reason': '',
                'how': '',
                'sourceCandidate': '',
                'relatedCause': '',
                'timing': '',
            }
            cards.append(current)
            continue
        if current is None:
            continue
        for label, field in label_fields:
            if label not in line:
                continue
            current[field] = line.split(label, 1)[1].lstrip(' :-').strip()
            break
    return _normalize_suggestion_cards(cards)


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
    cause_labels = []
    for label in state['label_result'].labels:
        cause_type = label['cause_type']
        harmony_summary = (
            cause_result.stress_report
            if cause_type == 'stress'
            else cause_result.relief_report
            if cause_type == 'relief'
            else ''
        )
        cause_labels.append({
            'keyword': label['keyword'],
            'causeType': cause_type,
            'emphasis': label['emphasis'],
            'displayWeight': label['display_weight'],
            'momentDescription': label.get('moment_description', ''),
            'harmonySummary': harmony_summary,
            'graphEventIds': list(label.get('graph_event_ids', ())),
            'evidenceDates': list(label.get('evidence_dates', ())),
        })
    hard_moments = _moments_from_labels(cause_labels, cause_type='stress')
    relief_moments = _moments_from_labels(cause_labels, cause_type='relief')
    emotions = []
    for score in scoring_result.emotion_scores:
        emotions.append({
            'day': f'{score.source_date.day:02d}일',
            # The frontend uses this value only to position and color the flow point.
            # It deliberately presents a qualitative phrase instead of the
            # numeric score so the report does not read like a diagnosis.
            'emotion_score': round(float(score.emotion_score), 2),
        })

    recommendations = list(narrative.action_recommendations)
    suggestion_cards = [
        {
            'title': card.title,
            'reason': card.reason,
            'how': card.how,
            'sourceCandidate': card.source_candidate,
            'relatedCause': card.related_cause,
            'timing': card.timing,
        }
        for card in narrative.suggestion_cards
    ]
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
        'hardMoments': hard_moments,
        'reliefMoments': relief_moments,
        'stressReport': cause_result.stress_report,
        'reliefReport': cause_result.relief_report,
        'emotions': emotions,
        'analysis': list(narrative.analysis_sentences),
        'recommendations': recommendations,
        'suggestionCards': suggestion_cards,
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
    suggestion_cards = _normalize_suggestion_cards(normalized['suggestionCards'])
    stored_cards = _suggestion_cards_from_analysis(normalized['analysis'])
    if suggestion_cards and not stored_cards:
        normalized['analysis'].extend(
            _suggestion_cards_to_analysis(suggestion_cards)
        )
    normalized['suggestionCards'] = suggestion_cards or stored_cards
    # Keep the graph bands aligned with the server-side scoring policy without
    # exposing the numeric score on the report itself.
    normalized['emotionScale'] = _emotion_scale_payload()
    normalized['stressReport'] = (
        _normalize_cause_report(
            normalized.get('stressReport'),
            cause_type='stress',
        )
        or _cause_report_from_labels(
            normalized['causeLabels'],
            cause_type='stress',
        )
    )
    normalized['reliefReport'] = (
        _normalize_cause_report(
            normalized.get('reliefReport'),
            cause_type='relief',
        )
        or _cause_report_from_labels(
            normalized['causeLabels'],
            cause_type='relief',
        )
    )
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
    cause_labels = list(report.cause_labels)
    return {
        'id': f'{prefix}-{report.id}',
        'type': report.report_type,
        'range': report.range_text,
        'generatedAt': timezone.localtime(report.created_at).isoformat(),
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
        'causeLabels': cause_labels,
        'hardMoments': _moments_from_labels(cause_labels, cause_type='stress'),
        'reliefMoments': _moments_from_labels(cause_labels, cause_type='relief'),
        'stressReport': _cause_report_from_labels(cause_labels, cause_type='stress'),
        'reliefReport': _cause_report_from_labels(cause_labels, cause_type='relief'),
        'emotions': list(report.emotions),
        'emotionScale': _emotion_scale_payload(),
        'analysis': list(report.analysis),
        'recommendations': list(report.recommendations),
        'suggestionCards': _suggestion_cards_from_analysis(report.analysis),
        'is_fallback': report.is_fallback,
        'is_safety_response': report.is_safety_response,
    }


def _moments_from_labels(
    labels: list[Any],
    *,
    cause_type: str,
) -> list[dict[str, Any]]:
    moments = []
    seen_texts = set()
    for label in labels:
        if not isinstance(label, dict) or label.get('causeType') != cause_type:
            continue
        keyword = str(label.get('keyword') or '').strip()
        text = ' '.join(str(label.get('momentDescription') or '').split()).strip()
        if text and not re.search(r'요[.!?。]$', text):
            text = ''
        normalized = ''.join(text.split())
        if not text or normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        moments.append({
            'text': text,
            'keyword': keyword,
            'evidenceDates': list(label.get('evidenceDates') or []),
        })
    return moments[:4]


def _normalize_cause_report(value: Any, *, cause_type: str) -> str:
    text = ' '.join(str(value or '').split()).strip()
    explanatory_markers = (
        '때문', '덕분', '작용', '도움', '도와', '이어지', '맞물',
        '겹치', '압박', '여유', '가라앉', '누그러', '풀어', '숨을 고르',
        '함께', '과정', '상황', '맥락', '반복',
    )
    direction_markers = (
        ('편안', '안정', '회복', '위안', '쉬', '누그러', '숨을 고르')
        if cause_type == 'relief'
        else ('부담', '긴장', '불편', '지치', '무거', '압박', '걱정')
    )
    sentences = [
        sentence.strip()
        for sentence in re.split(r'(?<=[.!?。])\s+', text)
        if sentence.strip()
    ]
    has_explanation = any(marker in text for marker in explanatory_markers)
    is_verified_scene = (
        20 <= len(text) <= 100
        and any(marker in text for marker in direction_markers)
    )
    if (
        not text
        or len(text) > 180
        or not 1 <= len(sentences) <= 2
        or not all(re.search(r'요[.!?。]$', sentence) for sentence in sentences)
        or not any(marker in text for marker in direction_markers)
        or not (has_explanation or is_verified_scene)
        or any(term in text for term in (
            '우울증', '공황장애', '치료가 필요', '성격상', '반드시 해야', '당신'
        ))
        or bool(re.search(r'(?:^|\s)(?:\d+[.)]|[-•])\s*', text))
    ):
        return ''
    return text


def _cause_report_from_labels(
    labels: list[Any],
    *,
    cause_type: str,
) -> str:
    for label in labels:
        if not isinstance(label, dict) or label.get('causeType') != cause_type:
            continue
        stored_summary = _normalize_cause_report(
            label.get('harmonySummary'),
            cause_type=cause_type,
        )
        if stored_summary:
            return stored_summary
    for label in labels:
        if not isinstance(label, dict) or label.get('causeType') != cause_type:
            continue
        verified_moment = _normalize_cause_report(
            label.get('momentDescription'),
            cause_type=cause_type,
        )
        if verified_moment:
            return verified_moment
    return ''


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
        and '연결된 마음의 원인' not in str(item)
        and '제안 시점' not in str(item)
        and '감정 흐름 후보' not in str(item)
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

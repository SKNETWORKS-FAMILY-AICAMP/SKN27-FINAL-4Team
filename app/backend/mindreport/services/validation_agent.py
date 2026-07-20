from __future__ import annotations

from datetime import date, timedelta
import re
from typing import Iterable

from django.utils import timezone

from mindreport.services.emotion_flow import analyze_emotion_flow
from mindreport.services.graph_state import (
    MindReportGraphState,
    MindReportValidationIssue,
    append_trace,
)


VALIDATION_ROUTE_FORMAT = 'format'
VALIDATION_ROUTE_CRITERIA = 'criteria'
VALIDATION_ROUTE_EMOTION = 'emotion'
VALIDATION_ROUTE_CAUSE = 'cause_keywords'
VALIDATION_ROUTE_NARRATIVE = 'narrative'
VALIDATION_ROUTE_SAFETY = 'safety'
VALIDATION_ROUTE_FALLBACK = 'fallback'

_REVISION_PRIORITY = (
    VALIDATION_ROUTE_CRITERIA,
    VALIDATION_ROUTE_EMOTION,
    VALIDATION_ROUTE_CAUSE,
    VALIDATION_ROUTE_NARRATIVE,
)

_ASSERTIVE_PHRASES = (
    '분명', '확실', '틀림없이', '반드시', '원인입니다', '때문입니다',
    'definitely', 'certainly', 'must be',
)
_DIAGNOSIS_PATTERNS = (
    r'(우울증|공황장애|불안장애|조현병|양극성장애|adhd).{0,12}(입니다|진단|확실)',
    r'(diagnosed|diagnosis|you have).{0,20}(depression|disorder|adhd)',
    r'(완치|치료됩니다|치료 효과가 보장|반드시 낫)',
)
_OVERLY_POSITIVE_PHRASES = (
    '무조건 잘될', '모든 일이 잘될', '걱정할 필요가 전혀 없',
    '당신은 항상 옳', '무조건 당신 편', 'everything will be fine',
    'you are always right',
)
_RISK_PHRASES = (
    '죽고 싶', '죽어버리고 싶', '자살', '극단적 선택', '자해',
    '살고 싶지 않', '사라지고 싶', 'suicide', 'kill myself',
    'self-harm', 'want to die',
)
_SAFETY_RESPONSE_PHRASES = (
    '응급', '긴급', '안전', '도움', '의료기관', '전문가', '주변 사람',
    'emergency', 'immediate help', 'professional help',
)
_DATE_PATTERN = re.compile(r'\b(20\d{2})[-./](\d{1,2})[-./](\d{1,2})\b')
_QUOTED_PATTERN = re.compile(r'["“”](.{3,80}?)["“”]')
_PII_PATTERNS = (
    re.compile(r'\b\d{6}-?[1-4]\d{6}\b'),
    re.compile(r'\b01[016789]-?\d{3,4}-?\d{4}\b'),
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
)
_INTERNAL_ANALYSIS_PATTERNS = (
    re.compile(r'\b\d{1,3}(?:\.\d+)?\s*점'),
    re.compile(r'\b\d{1,3}(?:\.\d+)?\s*%'),
    re.compile(r'감정\s*(점수|상태)'),
    re.compile(r'(확신도|각성도|positive_affect|negative_affect|scoring_method)', re.IGNORECASE),
    re.compile(r'(긍정|부정|중립)\s*(감정|상태)'),
    re.compile(r'(상승|하락|유지|변동(?:성)?)\s*(흐름|패턴|상태)'),
    re.compile(r'(초록|빨강|회색)\s*유지'),
    re.compile(r'(당신은|현재\s*상태는).{0,30}(상태|보입니다|판단됩니다)'),
)


class MindReportValidationAgent:
    """Validates graph evidence, analysis consistency, and report safety."""

    def run(self, state: MindReportGraphState) -> MindReportGraphState:
        issues: list[MindReportValidationIssue] = []
        issues.extend(self._validate_data(state))
        issues.extend(self._validate_analysis(state))
        issues.extend(self._validate_safety(state))

        if not issues:
            validation_result = {
                'status': 'passed',
                'issues': [],
                'message': 'Mind report validation passed.',
            }
            next_state: MindReportGraphState = {
                **state,
                'validation_result': validation_result,
                'revision_target': '',
                'revision_instructions': [],
                'status': 'running',
                'error': None,
            }
        else:
            target = self._select_target(issues)
            retry_count = state.get('retry_count', 0)
            max_retries = state.get('max_retries', 1)
            if target == VALIDATION_ROUTE_SAFETY:
                validation_status = 'blocked'
                status = 'blocked'
            elif target == VALIDATION_ROUTE_FALLBACK or retry_count >= max_retries:
                target = VALIDATION_ROUTE_FALLBACK
                validation_status = 'blocked'
                status = 'blocked'
            else:
                retry_count += 1
                validation_status = 'needs_revision'
                status = 'needs_revision'

            validation_result = {
                'status': validation_status,
                'issues': issues,
                'message': 'Mind report validation found issues.',
            }
            next_state = {
                **state,
                'validation_result': validation_result,
                'revision_target': target,
                'revision_instructions': [issue['message'] for issue in issues],
                'retry_count': retry_count,
                'status': status,
                'error': validation_result['message'],
            }

        return append_trace(
            next_state,
            node='report_validation',
            status=next_state['validation_result']['status'],
            message=next_state['validation_result']['message'],
            payload={
                'issue_count': len(issues),
                'issue_codes': [issue['code'] for issue in issues],
                'revision_target': next_state.get('revision_target', ''),
                'retry_count': next_state.get('retry_count', 0),
            },
        )

    @staticmethod
    def route(state: MindReportGraphState) -> str:
        validation_result = state.get('validation_result')
        if validation_result and validation_result['status'] == 'passed':
            return VALIDATION_ROUTE_FORMAT
        return state.get('revision_target') or VALIDATION_ROUTE_FALLBACK

    def _validate_data(
        self,
        state: MindReportGraphState,
    ) -> list[MindReportValidationIssue]:
        issues: list[MindReportValidationIssue] = []
        collection = state.get('collection_result')
        scoring = state.get('scoring_result')
        if collection is None or scoring is None:
            return [self._issue(
                'missing_analysis_data',
                'Required collection or scoring output is missing.',
                'error',
                VALIDATION_ROUTE_CRITERIA,
            )]

        eligibility = collection.eligibility
        if (
            not eligibility.get('is_eligible')
            or eligibility.get('current_count', 0)
            < eligibility.get('required_count', 0)
        ):
            issues.append(self._issue(
                'generation_criteria_not_met',
                'Weekly or monthly generation criteria are not met.',
                'error',
                VALIDATION_ROUTE_FALLBACK,
            ))

        source_by_id = {
            message.message_id: message for message in collection.source_messages
        }
        collection_ids = set(source_by_id)
        scoring_ids = {message.message_id for message in scoring.source_messages}
        if collection_ids != scoring_ids:
            issues.append(self._issue(
                'source_message_set_mismatch',
                'Scoring used a different message set from data collection.',
                'error',
                VALIDATION_ROUTE_CRITERIA,
            ))

        for message in collection.source_messages:
            if not self._is_in_period(message.source_date, state):
                issues.append(self._issue(
                    'source_outside_analysis_period',
                    f'Message {message.message_id} is outside the analysis period.',
                    'error',
                    VALIDATION_ROUTE_CRITERIA,
                ))

        for score in scoring.emotion_scores:
            if not set(score.evidence_message_ids).issubset(collection_ids):
                issues.append(self._issue(
                    'unknown_scoring_evidence',
                    'Emotion scoring cites a message that does not exist.',
                    'error',
                    VALIDATION_ROUTE_EMOTION,
                ))
            if not self._is_in_period(score.source_date, state):
                issues.append(self._issue(
                    'unknown_scoring_date',
                    'Emotion scoring cites a date outside the analysis period.',
                    'error',
                    VALIDATION_ROUTE_EMOTION,
                ))

        for evidence_owner in self._keyword_evidence(state):
            evidence_ids = set(evidence_owner.evidence_message_ids)
            if not evidence_ids or not evidence_ids.issubset(collection_ids):
                issues.append(self._issue(
                    'unsupported_keyword_evidence',
                    f'Keyword "{evidence_owner.keyword}" has no valid source evidence.',
                    'error',
                    VALIDATION_ROUTE_CAUSE,
                ))
                continue
            actual_dates = {
                source_by_id[message_id].source_date.isoformat()
                for message_id in evidence_ids
            }
            if set(evidence_owner.evidence_dates) != actual_dates:
                issues.append(self._issue(
                    'keyword_evidence_date_mismatch',
                    f'Keyword "{evidence_owner.keyword}" cites inconsistent dates.',
                    'error',
                    VALIDATION_ROUTE_CAUSE,
                ))

        narrative_text = self._narrative_text(state)
        source_dates = {
            message.source_date for message in collection.source_messages
        }
        for cited_date in self._extract_dates(narrative_text):
            if cited_date not in source_dates:
                issues.append(self._issue(
                    'unknown_narrative_date',
                    f'Narrative cites an unsupported date: {cited_date.isoformat()}.',
                    'error',
                    VALIDATION_ROUTE_NARRATIVE,
                ))

        return issues

    def _validate_analysis(
        self,
        state: MindReportGraphState,
    ) -> list[MindReportValidationIssue]:
        issues: list[MindReportValidationIssue] = []
        scoring = state.get('scoring_result')
        emotion_flow = state.get('emotion_flow')
        cause_result = state.get('cause_result')
        if scoring is None or emotion_flow is None or cause_result is None:
            return [self._issue(
                'missing_analysis_output',
                'Emotion flow or cause keyword output is missing.',
                'error',
                VALIDATION_ROUTE_EMOTION,
            )]

        expected_flow = analyze_emotion_flow(scoring.emotion_scores)
        if (
            expected_flow.flow_type != emotion_flow.flow_type
            or expected_flow.maintenance_type != emotion_flow.maintenance_type
        ):
            issues.append(self._issue(
                'emotion_pattern_score_mismatch',
                'Emotion pattern does not match the calculated score flow.',
                'error',
                VALIDATION_ROUTE_EMOTION,
            ))

        narrative_result = state.get('narrative_result')
        narrative = narrative_result.narrative if narrative_result else None
        if narrative is not None:
            public_text = self._narrative_text(state)
            if any(pattern.search(public_text) for pattern in _INTERNAL_ANALYSIS_PATTERNS):
                issues.append(self._issue(
                    'internal_score_or_state_disclosed',
                    'Do not mention scores, internal emotion states, or flow classifications; rewrite them as cautious observations grounded in the conversation.',
                    'error',
                    VALIDATION_ROUTE_NARRATIVE,
                ))

            if _QUOTED_PATTERN.search(public_text):
                issues.append(self._issue(
                    'direct_conversation_quote_disclosed',
                    'Do not quote the conversation directly; paraphrase the observed topic and context using cautious, indirect language.',
                    'error',
                    VALIDATION_ROUTE_NARRATIVE,
                ))

            compact_summary = len(re.sub(r'\s+', '', narrative.summary))
            if compact_summary > 80:
                issues.append(self._issue(
                    'summary_too_long',
                    'Shorten the header summary to one natural Korean sentence of 35 to 80 characters and move details into the analysis paragraphs.',
                    'warning',
                    VALIDATION_ROUTE_NARRATIVE,
                ))
            analysis_lengths = [
                len(re.sub(r'\s+', '', paragraph))
                for paragraph in narrative.analysis_sentences
            ]
            action_lengths = [
                len(re.sub(r'\s+', '', paragraph))
                for paragraph in narrative.action_recommendations
            ]
            body_length = sum((*analysis_lengths, *action_lengths))
            if (
                len(narrative.analysis_sentences) < 3
                or len(narrative.action_recommendations) < 2
                or compact_summary < 25
                or any(length < 65 for length in analysis_lengths)
                or any(length < 45 for length in action_lengths)
                or body_length < 300
            ):
                issues.append(self._issue(
                    'narrative_too_shallow',
                    'Expand the report into at least three substantial evidence-grounded analysis paragraphs and two concrete action paragraphs with reasons and small starting methods, without adding unsupported facts.',
                    'warning',
                    VALIDATION_ROUTE_NARRATIVE,
                ))

        narrative_text = self._narrative_text(state).lower()
        for keyword in cause_result.cause_keywords:
            if keyword.confidence < 0.6 and keyword.keyword.lower() in narrative_text:
                if any(phrase in narrative_text for phrase in _ASSERTIVE_PHRASES):
                    issues.append(self._issue(
                        'low_confidence_asserted_as_fact',
                        f'Low-confidence keyword "{keyword.keyword}" was stated as fact.',
                        'warning',
                        VALIDATION_ROUTE_NARRATIVE,
                    ))

        return issues

    def _validate_safety(
        self,
        state: MindReportGraphState,
    ) -> list[MindReportValidationIssue]:
        issues: list[MindReportValidationIssue] = []
        report_text = self._narrative_text(state).lower()
        emotion_flow = state.get('emotion_flow')
        if emotion_flow is not None:
            report_text += ' ' + emotion_flow.interpretation.lower()

        if any(re.search(pattern, report_text, re.IGNORECASE) for pattern in _DIAGNOSIS_PATTERNS):
            issues.append(self._issue(
                'diagnosis_or_treatment_claim',
                'Remove disease, diagnosis, or guaranteed treatment claims.',
                'error',
                VALIDATION_ROUTE_NARRATIVE,
            ))

        if any(phrase in report_text for phrase in _OVERLY_POSITIVE_PHRASES):
            issues.append(self._issue(
                'overly_positive_or_unconditional_agreement',
                'Replace excessive optimism or unconditional agreement with balanced wording.',
                'warning',
                VALIDATION_ROUTE_NARRATIVE,
            ))

        if any(pattern.search(report_text) for pattern in _PII_PATTERNS):
            issues.append(self._issue(
                'excessive_personal_information',
                'Remove personal identifiers from the report narrative.',
                'error',
                VALIDATION_ROUTE_NARRATIVE,
            ))

        source_text = ' '.join(
            message.content
            for message in state.get('collection_result').source_messages
        ).lower()
        has_risk_signal = any(phrase in source_text for phrase in _RISK_PHRASES)
        if has_risk_signal:
            issues.append(self._issue(
                'high_risk_signal_detected',
                'High-risk source language requires the dedicated safety response.',
                'error',
                VALIDATION_ROUTE_SAFETY,
            ))
            if not any(phrase in report_text for phrase in _SAFETY_RESPONSE_PHRASES):
                issues.append(self._issue(
                    'high_risk_signal_omitted',
                    'The generated report omitted an appropriate safety response.',
                    'error',
                    VALIDATION_ROUTE_SAFETY,
                ))

        return issues

    @staticmethod
    def _select_target(issues: Iterable[MindReportValidationIssue]) -> str:
        targets = {issue['target'] for issue in issues}
        if VALIDATION_ROUTE_SAFETY in targets:
            return VALIDATION_ROUTE_SAFETY
        if VALIDATION_ROUTE_FALLBACK in targets:
            return VALIDATION_ROUTE_FALLBACK
        for target in _REVISION_PRIORITY:
            if target in targets:
                return target
        return VALIDATION_ROUTE_FALLBACK

    @staticmethod
    def _keyword_evidence(state: MindReportGraphState):
        keyword_result = state.get('keyword_result')
        cause_result = state.get('cause_result')
        candidates = keyword_result.candidates if keyword_result else ()
        cause_keywords = cause_result.cause_keywords if cause_result else ()
        return (*candidates, *cause_keywords)

    @staticmethod
    def _narrative_text(state: MindReportGraphState) -> str:
        narrative_result = state.get('narrative_result')
        if narrative_result is None or narrative_result.narrative is None:
            return ''
        narrative = narrative_result.narrative
        return ' '.join(
            (
                narrative.title,
                narrative.summary,
                *narrative.analysis_sentences,
                *narrative.action_recommendations,
            )
        )

    @staticmethod
    def _extract_dates(text: str) -> tuple[date, ...]:
        parsed: list[date] = []
        for year, month, day in _DATE_PATTERN.findall(text):
            try:
                parsed.append(date(int(year), int(month), int(day)))
            except ValueError:
                continue
        return tuple(parsed)

    @staticmethod
    def _is_in_period(source_date: date, state: MindReportGraphState) -> bool:
        now = timezone.now().date()
        if state['period_type'] == 'week':
            target = state.get('target_date') or now
            start = target - timedelta(days=target.weekday())
            return start <= source_date <= start + timedelta(days=6)
        year = state.get('year') or now.year
        month = state.get('month') or now.month
        return source_date.year == year and source_date.month == month

    @staticmethod
    def _issue(
        code: str,
        message: str,
        severity: str,
        target: str,
    ) -> MindReportValidationIssue:
        return {
            'code': code,
            'message': message,
            'severity': severity,
            'target': target,
        }

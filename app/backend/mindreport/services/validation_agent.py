from __future__ import annotations

from datetime import date
import re
from typing import Iterable

from mindreport.services.emotion_flow import analyze_emotion_flow
from mindreport.services.graph_state import (
    MindReportGraphState,
    MindReportValidationIssue,
    append_trace,
)
from mindreport.services.scoring import (
    KCELECTRA_SCORING_METHOD,
    SCORING_ROUTE_KCELECTRA,
    emotion_state_from_score,
)
from mindreport.services.periods import resolve_period_window
from mindreport.services.payloads import (
    report_recipient_name,
    select_comfort_message,
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
_DATE_PATTERN = re.compile(
    r'(?<!\d)(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?!\d)'
)
_KOREAN_DATE_PATTERN = re.compile(
    r'(?<!\d)(1[0-2]|0?[1-9])월\s*(3[01]|[12]?\d)일'
)
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
_PRACTICAL_CUE_PATTERN = re.compile(
    r'(오늘|내일|아침|점심|저녁|퇴근|귀가|잠들기|기상|시작\s*전|마친\s*뒤|'
    r'직전|직후|\d+\s*분\s*(?:전|후)|(?:회의|수업|업무|일정|외출|잠|식사)\s*(?:전|후|뒤))'
)
_PRACTICAL_AMOUNT_PATTERN = re.compile(
    r'(?:\d+|한|두|세)\s*(분|초|회|번|개|줄|쪽|걸음|가지)'
)
_PRACTICAL_ACTION_PATTERN = re.compile(
    r'(적|쓰|열|꺼내|놓|맞추|고르|정리|표시|걷|마시|보내|읽|듣|앉|'
    r'나가|챙기|준비|시작|닫|끄|누르|확인|말해|연락)'
)
_VIEW_DATE_DEPENDENT_PATTERN = re.compile(
    r'(오늘|내일|모레|이번\s*(?:주|주말|달)|금주|금월)'
)


class MindReportValidationAgent:
    """Validates graph evidence, analysis consistency, and report safety."""

    def run(self, state: MindReportGraphState) -> MindReportGraphState:
        issues: list[MindReportValidationIssue] = []
        issues.extend(self._validate_data(state))
        issues.extend(self._validate_analysis(state))
        issues.extend(self._validate_cause_output(state))
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
            if not 0.0 <= score.emotion_score <= 100.0:
                issues.append(self._issue(
                    'emotion_score_out_of_range',
                    'Emotion score must stay within the 0..100 contract.',
                    'error',
                    VALIDATION_ROUTE_EMOTION,
                ))
            expected_state = emotion_state_from_score(score.emotion_score)
            if score.emotion_state != expected_state:
                issues.append(self._issue(
                    'emotion_state_score_mismatch',
                    'Emotion state must be derived from the current 0..100 score.',
                    'error',
                    VALIDATION_ROUTE_EMOTION,
                ))
            if not set(score.evidence_message_ids).issubset(collection_ids):
                issues.append(self._issue(
                    'unknown_scoring_evidence',
                    'Emotion scoring cites a message that does not exist.',
                    'error',
                    VALIDATION_ROUTE_EMOTION,
                ))
            evidence_dates = {
                source_by_id[message_id].source_date
                for message_id in score.evidence_message_ids
                if message_id in source_by_id
            }
            if evidence_dates and evidence_dates != {score.source_date}:
                issues.append(self._issue(
                    'scoring_evidence_date_mismatch',
                    'Daily emotion scoring may cite only messages from its source date.',
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

        if scoring.scoring_route == SCORING_ROUTE_KCELECTRA and any(
            score.scoring_method != KCELECTRA_SCORING_METHOD
            for score in scoring.emotion_scores
        ):
            issues.append(self._issue(
                'kcelectra_scoring_method_mismatch',
                'KcELECTRA scoring route must use the KcELECTRA scoring method.',
                'error',
                VALIDATION_ROUTE_EMOTION,
            ))

        available_graph_event_ids = {
            event.event_id
            for event in getattr(collection, 'ltm_events', ())
            if event.event_id
        }
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

            cited_graph_event_ids = set(
                getattr(evidence_owner, 'graph_event_ids', ())
            )
            if not cited_graph_event_ids.issubset(available_graph_event_ids):
                issues.append(self._issue(
                    'unsupported_graph_event_evidence',
                    f'Keyword "{evidence_owner.keyword}" cites an unavailable GraphDB event.',
                    'error',
                    VALIDATION_ROUTE_CAUSE,
                ))
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
        narrative_allowed_dates = {
            message.source_date for message in collection.source_messages
        }
        graph_date_parts = []
        for event in getattr(collection, 'ltm_events', ()):
            graph_date_parts.extend((
                event.episode_date,
                event.occurs_start,
                event.occurs_end,
            ))
        narrative_allowed_dates.update(self._extract_dates(' '.join(
            str(value) for value in graph_date_parts if value
        )))
        for cited_date in self._extract_dates(narrative_text):
            if cited_date not in narrative_allowed_dates:
                issues.append(self._issue(
                    'unknown_narrative_date',
                    f'Narrative cites an unsupported date: {cited_date.isoformat()}.',
                    'error',
                    VALIDATION_ROUTE_NARRATIVE,
                ))
        for cited_month, cited_day in self._extract_month_days(narrative_text):
            if not any(
                source_date.month == cited_month and source_date.day == cited_day
                for source_date in narrative_allowed_dates
            ):
                issues.append(self._issue(
                    'unknown_narrative_date',
                    f'Narrative cites an unsupported date: {cited_month}월 {cited_day}일.',
                    'error',
                    VALIDATION_ROUTE_NARRATIVE,
                ))

        return issues

    def _validate_cause_output(
        self,
        state: MindReportGraphState,
    ) -> list[MindReportValidationIssue]:
        """Validate every cause-agent sentence that can reach the frontend."""
        issues: list[MindReportValidationIssue] = []
        cause_text = self._cause_text(state)
        if not cause_text:
            return issues

        if any(pattern.search(cause_text) for pattern in _INTERNAL_ANALYSIS_PATTERNS):
            issues.append(self._issue(
                'cause_internal_score_or_state_disclosed',
                'Remove scores, internal emotion states, and flow classifications from the public cause report.',
                'error',
                VALIDATION_ROUTE_CAUSE,
            ))

        if _QUOTED_PATTERN.search(cause_text):
            issues.append(self._issue(
                'cause_direct_conversation_quote_disclosed',
                'Paraphrase the cause evidence without directly quoting the conversation.',
                'error',
                VALIDATION_ROUTE_CAUSE,
            ))

        collection = state.get('collection_result')
        allowed_dates = {
            message.source_date
            for message in getattr(collection, 'source_messages', ())
        }
        cause_result = state.get('cause_result')
        cited_graph_event_ids = {
            event_id
            for keyword in getattr(cause_result, 'cause_keywords', ())
            for event_id in keyword.graph_event_ids
        }
        graph_date_parts = []
        for event in getattr(collection, 'ltm_events', ()):
            if event.event_id not in cited_graph_event_ids:
                continue
            graph_date_parts.extend((
                event.episode_date,
                event.occurs_start,
                event.occurs_end,
            ))
        allowed_dates.update(self._extract_dates(' '.join(
            str(value) for value in graph_date_parts if value
        )))
        for cited_date in self._extract_dates(cause_text):
            if cited_date not in allowed_dates:
                issues.append(self._issue(
                    'unknown_cause_date',
                    f'Cause report cites an unsupported date: {cited_date.isoformat()}.',
                    'error',
                    VALIDATION_ROUTE_CAUSE,
                ))
        for cited_month, cited_day in self._extract_month_days(cause_text):
            if not any(
                allowed_date.month == cited_month and allowed_date.day == cited_day
                for allowed_date in allowed_dates
            ):
                issues.append(self._issue(
                    'unknown_cause_date',
                    f'Cause report cites an unsupported date: {cited_month}월 {cited_day}일.',
                    'error',
                    VALIDATION_ROUTE_CAUSE,
                ))

        lowered = cause_text.lower()
        if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in _DIAGNOSIS_PATTERNS):
            issues.append(self._issue(
                'cause_diagnosis_or_treatment_claim',
                'Remove disease, diagnosis, and guaranteed treatment claims from the cause report.',
                'error',
                VALIDATION_ROUTE_CAUSE,
            ))

        if any(phrase in lowered for phrase in _OVERLY_POSITIVE_PHRASES):
            issues.append(self._issue(
                'cause_overly_positive_or_unconditional_agreement',
                'Replace excessive optimism or unconditional agreement in the cause report with balanced wording.',
                'warning',
                VALIDATION_ROUTE_CAUSE,
            ))

        if any(pattern.search(cause_text) for pattern in _PII_PATTERNS):
            issues.append(self._issue(
                'cause_excessive_personal_information',
                'Remove personal identifiers from the public cause report.',
                'error',
                VALIDATION_ROUTE_CAUSE,
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

            recipient_name = report_recipient_name(state['user'])
            comfort_message = select_comfort_message(
                summary=narrative.summary,
                analysis=narrative.analysis_sentences,
                recommendations=narrative.action_recommendations,
                recipient_name=recipient_name,
            )
            compact_comfort = len(re.sub(r'\s+', '', comfort_message))
            has_recipient_name = comfort_message.count(recipient_name) == 1
            if (
                compact_comfort < 20
                or compact_comfort > 60
                or not has_recipient_name
                or '당신' in comfort_message
            ):
                issues.append(self._issue(
                    'support_message_missing_recipient_name',
                    f'Rewrite the second sentence of the final analysis paragraph as a 20-to-60-character, context-grounded Korean message that addresses the user exactly once as "{recipient_name}" and does not use "당신". Match the dominant emotional context with comfort, encouragement, or cheering; avoid analysis, instructions, and generic optimism.',
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

            for card in narrative.suggestion_cards:
                how = card.how.strip()
                if _VIEW_DATE_DEPENDENT_PATTERN.search(how):
                    issues.append(self._issue(
                        'suggestion_timing_depends_on_view_date',
                        f'Rewrite the starting method for "{card.title}" so it remains clear when this saved report is opened later. Replace today, tomorrow, this weekend, or this month with a repeatable cue such as the next commute home, the next meeting, or before sleep, while keeping the action inside report_context.action_window.',
                        'warning',
                        VALIDATION_ROUTE_NARRATIVE,
                    ))
                if (
                    not _PRACTICAL_CUE_PATTERN.search(how)
                    or not _PRACTICAL_AMOUNT_PATTERN.search(how)
                    or not _PRACTICAL_ACTION_PATTERN.search(how)
                ):
                    issues.append(self._issue(
                        'suggestion_start_not_practical',
                        f'Rewrite the starting method for "{card.title}" with a concrete cue, one clear first action, a small measurable amount, and a stopping point. Keep it grounded in the supplied cause scene and do not add unsupported facts.',
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
                *(card.title for card in narrative.suggestion_cards),
            )
        )

    @staticmethod
    def _cause_text(state: MindReportGraphState) -> str:
        cause_result = state.get('cause_result')
        if cause_result is None:
            return ''
        return ' '.join(filter(None, (
            cause_result.stress_report,
            cause_result.relief_report,
            *(
                keyword.moment_description
                for keyword in cause_result.cause_keywords
            ),
        )))

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
    def _extract_month_days(text: str) -> tuple[tuple[int, int], ...]:
        parsed = []
        for month, day in _KOREAN_DATE_PATTERN.findall(text):
            month_number = int(month)
            day_number = int(day)
            try:
                date(2000, month_number, day_number)
            except ValueError:
                continue
            parsed.append((month_number, day_number))
        return tuple(parsed)

    @staticmethod
    def _is_in_period(source_date: date, state: MindReportGraphState) -> bool:
        window = resolve_period_window(
            period_type=state['period_type'],
            target_date=state.get('target_date'),
            year=state.get('year'),
            month=state.get('month'),
        )
        return window.start.date() <= source_date <= window.end_inclusive.date()

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

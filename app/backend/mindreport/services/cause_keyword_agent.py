from __future__ import annotations

from mindreport.services.alternatives import build_alternative_plan
from mindreport.services.cause_keywords import (
    MindReportCauseClassifier,
    apply_label_display_policy,
)
from mindreport.services.graph_state import MindReportGraphState, append_trace
from mindreport.services.keyword_candidates import MindReportKeywordExtractor


class MindReportCauseKeywordAgent:
    """Extracts evidence-based candidates and classifies cause keywords."""

    def __init__(
        self,
        keyword_extractor: MindReportKeywordExtractor | None = None,
        cause_classifier: MindReportCauseClassifier | None = None,
    ):
        self.keyword_extractor = keyword_extractor
        self.cause_classifier = cause_classifier

    def run(self, state: MindReportGraphState) -> MindReportGraphState:
        scoring_result = state.get('scoring_result')
        emotion_flow = state.get('emotion_flow')
        if scoring_result is None or scoring_result.status != 'scored':
            raise ValueError('Cause keyword analysis requires emotion scores.')
        if emotion_flow is None:
            raise ValueError('Cause keyword analysis requires an emotion flow.')

        alternative_plan = build_alternative_plan(emotion_flow)
        collection_result = state.get('collection_result')
        graph_events = (
            getattr(collection_result, 'ltm_events', ())
            if collection_result is not None
            else ()
        )
        keyword_extractor = self.keyword_extractor or MindReportKeywordExtractor(
            keyword_client=state.get('keyword_client')
        )
        keyword_result = keyword_extractor.run(
            source_messages=scoring_result.source_messages,
            emotion_scores=scoring_result.emotion_scores,
            emotion_flow=emotion_flow,
            alternative_plan=alternative_plan,
            graph_events=graph_events,
            revision_instructions=state.get('revision_instructions', ()),
        )

        cause_result = None
        label_result = None
        status = 'blocked'
        error = keyword_result.message

        if keyword_result.status in {'extracted', 'no_supported_candidates'}:
            cause_classifier = self.cause_classifier or MindReportCauseClassifier(
                cause_client=state.get('cause_client')
            )
            cause_result = cause_classifier.run(
                candidates=keyword_result.candidates,
                emotion_scores=scoring_result.emotion_scores,
                emotion_flow=emotion_flow,
                source_messages=scoring_result.source_messages,
                graph_events=graph_events,
                revision_instructions=state.get('revision_instructions', ()),
            )
            if cause_result.status in {
                'classified',
                'partially_classified',
                'no_supported_causes',
            }:
                label_result = apply_label_display_policy(
                    cause_keywords=cause_result.cause_keywords,
                    emotion_flow_type=emotion_flow.flow_type,
                )
                status = 'running'
                error = None
            else:
                error = cause_result.message

        next_state: MindReportGraphState = {
            **state,
            'alternative_plan': alternative_plan,
            'keyword_result': keyword_result,
            'cause_result': cause_result,
            'label_result': label_result,
            'status': status,
            'error': error,
        }
        cause_keywords = cause_result.cause_keywords if cause_result else ()
        return append_trace(
            next_state,
            node='cause_keyword_extraction_and_classification',
            status='completed' if status == 'running' else 'blocked',
            message=error or 'Cause keyword extraction and classification completed.',
            payload={
                'alternative_status': alternative_plan.status,
                'extraction': {
                    'status': keyword_result.status,
                    'candidate_count': len(keyword_result.candidates),
                },
                'classification': {
                    'status': cause_result.status if cause_result else None,
                    'cause_keyword_count': len(cause_keywords),
                    'stress_count': sum(
                        1
                        for keyword in cause_keywords
                        if keyword.cause_type == 'stress'
                    ),
                    'relief_count': sum(
                        1
                        for keyword in cause_keywords
                        if keyword.cause_type == 'relief'
                    ),
                    'unresolved_count': len(cause_result.unresolved_candidates)
                    if cause_result
                    else 0,
                },
                'label_policy_status': label_result.status if label_result else None,
            },
        )

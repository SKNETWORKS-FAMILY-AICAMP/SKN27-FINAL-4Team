from __future__ import annotations

from mindreport.services.emotion_flow import (
    analyze_emotion_flow,
    emotion_flow_result_to_payload,
)
from mindreport.services.graph_state import MindReportGraphState, append_trace
from mindreport.services.scoring import MindReportScoringService


class MindReportEmotionAnalysisAgent:
    """Scores emotions and classifies their time-series pattern."""

    def __init__(
        self,
        scoring_service: MindReportScoringService | None = None,
    ):
        self.scoring_service = scoring_service

    def run(self, state: MindReportGraphState) -> MindReportGraphState:
        collection_result = state.get('collection_result')
        if collection_result is None:
            raise ValueError('Emotion analysis requires a collection result.')
        if not collection_result.eligibility['is_eligible']:
            raise ValueError('Emotion analysis cannot run before criteria pass.')

        scoring_service = self.scoring_service or MindReportScoringService(
            score_client=state.get('score_client')
        )
        scoring_result = scoring_service.run(
            user=state['user'],
            period_type=state['period_type'],
            target_date=state.get('target_date'),
            year=state.get('year'),
            month=state.get('month'),
            collection_result=collection_result,
            revision_instructions=state.get('revision_instructions', ()),
        )
        emotion_flow = (
            analyze_emotion_flow(scoring_result.emotion_scores)
            if scoring_result.status == 'scored'
            else None
        )
        is_completed = emotion_flow is not None

        next_state: MindReportGraphState = {
            **state,
            'scoring_result': scoring_result,
            'emotion_flow': emotion_flow,
            'status': 'running' if is_completed else 'blocked',
            'error': None if is_completed else scoring_result.message,
        }
        flow_payload = (
            emotion_flow_result_to_payload(emotion_flow)
            if emotion_flow is not None
            else {}
        )
        return append_trace(
            next_state,
            node='mind_emotion_analysis',
            status='completed' if is_completed else 'blocked',
            message=scoring_result.message,
            payload={
                'scoring_status': scoring_result.status,
                'scoring_route': scoring_result.scoring_route,
                'daily_score_count': len(scoring_result.emotion_scores),
                'time_series': {
                    'metrics': flow_payload.get('metrics', {}),
                    'daily_summaries': flow_payload.get('daily_summaries', []),
                    'detected_by': flow_payload.get('detected_by'),
                },
                'emotion_pattern': {
                    'flow_type': flow_payload.get('flow_type'),
                    'maintenance_type': flow_payload.get('maintenance_type'),
                    'tone_color': flow_payload.get('tone_color'),
                    'rationale': flow_payload.get('rationale'),
                },
            },
        )

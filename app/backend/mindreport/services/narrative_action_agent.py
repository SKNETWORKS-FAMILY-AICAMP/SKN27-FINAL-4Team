from __future__ import annotations

from mindreport.services.graph_state import MindReportGraphState, append_trace
from mindreport.services.narrative import MindReportNarrativeGenerator


class MindReportNarrativeActionAgent:
    """Generates evidence-grounded analysis and practical actions."""

    def __init__(
        self,
        narrative_generator: MindReportNarrativeGenerator | None = None,
    ):
        self.narrative_generator = narrative_generator

    def run(self, state: MindReportGraphState) -> MindReportGraphState:
        scoring_result = state.get('scoring_result')
        emotion_flow = state.get('emotion_flow')
        alternative_plan = state.get('alternative_plan')
        cause_result = state.get('cause_result')
        label_result = state.get('label_result')

        if scoring_result is None or scoring_result.status != 'scored':
            raise ValueError('Narrative generation requires emotion scores.')
        if emotion_flow is None:
            raise ValueError('Narrative generation requires an emotion flow.')
        if alternative_plan is None or alternative_plan.status != 'prepared':
            raise ValueError('Narrative generation requires an alternative plan.')
        if cause_result is None or cause_result.status not in {
            'classified',
            'partially_classified',
            'no_supported_causes',
        }:
            raise ValueError('Narrative generation requires cause keywords.')
        if label_result is None:
            raise ValueError('Narrative generation requires a label display result.')

        narrative_generator = (
            self.narrative_generator
            or MindReportNarrativeGenerator(
                narrative_client=state.get('narrative_client')
            )
        )
        narrative_result = narrative_generator.run(
            source_messages=scoring_result.source_messages,
            emotion_scores=scoring_result.emotion_scores,
            emotion_flow=emotion_flow,
            alternative_plan=alternative_plan,
            cause_result=cause_result,
            label_result=label_result,
            revision_instructions=state.get('revision_instructions', ()),
        )
        is_generated = (
            narrative_result.status == 'generated'
            and narrative_result.narrative is not None
        )

        next_state: MindReportGraphState = {
            **state,
            'narrative_result': narrative_result,
            'status': 'running' if is_generated else 'blocked',
            'error': None if is_generated else narrative_result.message,
        }
        narrative = narrative_result.narrative
        return append_trace(
            next_state,
            node='analysis_evidence_and_action_generation',
            status='completed' if is_generated else 'blocked',
            message=narrative_result.message,
            payload={
                'narrative_status': narrative_result.status,
                'evidence': {
                    'source_message_count': len(scoring_result.source_messages),
                    'cause_keyword_count': len(cause_result.cause_keywords),
                    'analysis_sentence_count': len(narrative.analysis_sentences)
                    if narrative
                    else 0,
                },
                'actions': {
                    'alternative_candidate_count': len(
                        alternative_plan.candidates
                    ),
                    'recommendation_count': len(
                        narrative.action_recommendations
                    )
                    if narrative
                    else 0,
                },
            },
        )

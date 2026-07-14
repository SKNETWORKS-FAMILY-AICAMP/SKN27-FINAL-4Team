from __future__ import annotations

from typing import Literal

from mindreport.services.collection import (
    MindReportCollectionResult,
    MindReportDataCollector,
)
from mindreport.services.graph_state import MindReportGraphState, append_trace


GENERATION_ROUTE = 'generation'
FALLBACK_ROUTE = 'fallback'
MindReportCriteriaRoute = Literal['generation', 'fallback']


class MindReportGenerationCriteriaAgent:
    """Checks report eligibility and selects the first graph route."""

    def __init__(self, collector: MindReportDataCollector | None = None):
        self.collector = collector or MindReportDataCollector()

    def run(self, state: MindReportGraphState) -> MindReportGraphState:
        collection_result = self.collector.run(
            user=state['user'],
            period_type=state['period_type'],
            target_date=state.get('target_date'),
            year=state.get('year'),
            month=state.get('month'),
        )
        route = self.decide_route(collection_result)
        is_eligible = route == GENERATION_ROUTE

        next_state: MindReportGraphState = {
            **state,
            'collection_result': collection_result,
            'status': 'running' if is_eligible else 'insufficient_data',
            'next_node': route,
            'error': None if is_eligible else collection_result.message,
        }
        return append_trace(
            next_state,
            node='generation_criteria_and_graph_validation',
            status='passed' if is_eligible else 'insufficient_data',
            message=collection_result.message,
            payload={
                'period_type': collection_result.period_type,
                'source_message_count': len(collection_result.source_messages),
                'eligibility': collection_result.eligibility,
                'selected_route': route,
            },
        )

    @staticmethod
    def decide_route(
        collection_result: MindReportCollectionResult,
    ) -> MindReportCriteriaRoute:
        eligibility = collection_result.eligibility
        required_keys = {
            'is_eligible',
            'current_count',
            'required_count',
            'missing_count',
        }
        missing_keys = required_keys.difference(eligibility)
        if missing_keys:
            missing = ', '.join(sorted(missing_keys))
            raise ValueError(f'Invalid generation criteria result: missing {missing}')

        if eligibility['is_eligible']:
            return GENERATION_ROUTE
        return FALLBACK_ROUTE

    @staticmethod
    def route(state: MindReportGraphState) -> MindReportCriteriaRoute:
        route = state.get('next_node')
        if route in {GENERATION_ROUTE, FALLBACK_ROUTE}:
            return route
        raise ValueError('Generation criteria agent did not select a graph route.')

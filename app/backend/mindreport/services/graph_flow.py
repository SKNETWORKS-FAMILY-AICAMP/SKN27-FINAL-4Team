from __future__ import annotations

from datetime import date
from typing import Any

from langgraph.graph import END, StateGraph

from mindreport.services.criteria_agent import (
    FALLBACK_ROUTE,
    GENERATION_ROUTE,
    MindReportGenerationCriteriaAgent,
)
from mindreport.services.graph_nodes import (
    collect_and_check_criteria_node,
    extract_and_classify_causes_node,
    fallback_report_node,
    format_report_node,
    generate_narrative_and_actions_node,
    safety_response_node,
    score_and_analyze_emotion_node,
    validate_report_node,
)
from mindreport.services.validation_agent import (
    VALIDATION_ROUTE_CAUSE,
    VALIDATION_ROUTE_CRITERIA,
    VALIDATION_ROUTE_EMOTION,
    VALIDATION_ROUTE_FALLBACK,
    VALIDATION_ROUTE_FORMAT,
    VALIDATION_ROUTE_NARRATIVE,
    VALIDATION_ROUTE_SAFETY,
    MindReportValidationAgent,
)
from mindreport.services.graph_state import (
    MindReportGraphState,
    MindReportPeriodType,
    build_initial_mindreport_state,
)


NODE_COLLECT_AND_CHECK = 'collect_and_check_criteria'
NODE_SCORE_AND_ANALYZE = 'score_and_analyze_emotion'
NODE_EXTRACT_AND_CLASSIFY = 'extract_and_classify_causes'
NODE_GENERATE_NARRATIVE = 'generate_narrative_and_actions'
NODE_VALIDATE_REPORT = 'validate_report'
NODE_FORMAT_REPORT = 'format_report'
NODE_FALLBACK_REPORT = 'fallback_report'
NODE_SAFETY_RESPONSE = 'safety_response'


class MindReportSupervisorAgent:
    """Coordinates generation, validation, revision, and terminal routes."""

    def __init__(self):
        self.graph = build_mindreport_supervisor_graph()

    def run(
        self,
        *,
        user: Any,
        period_type: MindReportPeriodType,
        target_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
        period_name: str = '',
        score_client=None,
        keyword_client=None,
        cause_client=None,
        narrative_client=None,
        max_retries: int = 1,
    ) -> MindReportGraphState:
        initial_state = build_initial_mindreport_state(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
            period_name=period_name,
            score_client=score_client,
            keyword_client=keyword_client,
            cause_client=cause_client,
            narrative_client=narrative_client,
            max_retries=max_retries,
        )
        return self.graph.invoke(initial_state)


def build_mindreport_supervisor_graph():
    workflow = StateGraph(MindReportGraphState)

    workflow.add_node(NODE_COLLECT_AND_CHECK, collect_and_check_criteria_node)
    workflow.add_node(NODE_SCORE_AND_ANALYZE, score_and_analyze_emotion_node)
    workflow.add_node(NODE_EXTRACT_AND_CLASSIFY, extract_and_classify_causes_node)
    workflow.add_node(NODE_GENERATE_NARRATIVE, generate_narrative_and_actions_node)
    workflow.add_node(NODE_VALIDATE_REPORT, validate_report_node)
    workflow.add_node(NODE_FORMAT_REPORT, format_report_node)
    workflow.add_node(NODE_FALLBACK_REPORT, fallback_report_node)
    workflow.add_node(NODE_SAFETY_RESPONSE, safety_response_node)

    workflow.set_entry_point(NODE_COLLECT_AND_CHECK)
    workflow.add_conditional_edges(
        NODE_COLLECT_AND_CHECK,
        route_after_criteria,
        {
            GENERATION_ROUTE: NODE_SCORE_AND_ANALYZE,
            FALLBACK_ROUTE: NODE_FALLBACK_REPORT,
        },
    )
    workflow.add_conditional_edges(
        NODE_SCORE_AND_ANALYZE,
        route_after_emotion_analysis,
        {
            NODE_EXTRACT_AND_CLASSIFY: NODE_EXTRACT_AND_CLASSIFY,
            NODE_FALLBACK_REPORT: NODE_FALLBACK_REPORT,
        },
    )
    workflow.add_conditional_edges(
        NODE_EXTRACT_AND_CLASSIFY,
        route_after_cause_analysis,
        {
            NODE_GENERATE_NARRATIVE: NODE_GENERATE_NARRATIVE,
            NODE_FALLBACK_REPORT: NODE_FALLBACK_REPORT,
        },
    )
    workflow.add_conditional_edges(
        NODE_GENERATE_NARRATIVE,
        route_after_narrative_generation,
        {
            NODE_VALIDATE_REPORT: NODE_VALIDATE_REPORT,
            NODE_FALLBACK_REPORT: NODE_FALLBACK_REPORT,
        },
    )
    workflow.add_conditional_edges(
        NODE_VALIDATE_REPORT,
        route_after_validation,
        {
            VALIDATION_ROUTE_FORMAT: NODE_FORMAT_REPORT,
            VALIDATION_ROUTE_CRITERIA: NODE_COLLECT_AND_CHECK,
            VALIDATION_ROUTE_EMOTION: NODE_SCORE_AND_ANALYZE,
            VALIDATION_ROUTE_CAUSE: NODE_EXTRACT_AND_CLASSIFY,
            VALIDATION_ROUTE_NARRATIVE: NODE_GENERATE_NARRATIVE,
            VALIDATION_ROUTE_SAFETY: NODE_SAFETY_RESPONSE,
            VALIDATION_ROUTE_FALLBACK: NODE_FALLBACK_REPORT,
        },
    )
    workflow.add_edge(NODE_FORMAT_REPORT, END)
    workflow.add_edge(NODE_FALLBACK_REPORT, END)
    workflow.add_edge(NODE_SAFETY_RESPONSE, END)

    return workflow.compile()


def route_after_criteria(state: MindReportGraphState) -> str:
    return MindReportGenerationCriteriaAgent.route(state)


def route_after_emotion_analysis(state: MindReportGraphState) -> str:
    if state.get('status') == 'running':
        return NODE_EXTRACT_AND_CLASSIFY
    return NODE_FALLBACK_REPORT


def route_after_cause_analysis(state: MindReportGraphState) -> str:
    if state.get('status') == 'running':
        return NODE_GENERATE_NARRATIVE
    return NODE_FALLBACK_REPORT


def route_after_narrative_generation(state: MindReportGraphState) -> str:
    if state.get('status') == 'running':
        return NODE_VALIDATE_REPORT
    return NODE_FALLBACK_REPORT


def route_after_validation(state: MindReportGraphState) -> str:
    return MindReportValidationAgent.route(state)

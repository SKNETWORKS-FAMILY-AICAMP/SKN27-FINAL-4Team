from __future__ import annotations

from datetime import date
from typing import Any, Literal, TypedDict

from mindreport.services.alternatives import AlternativePlanResult
from mindreport.services.collection import MindReportCollectionResult
from mindreport.services.cause_keywords import (
    CauseKeywordClient,
    CauseKeywordResult,
    LabelDisplayResult,
)
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.keyword_candidates import (
    KeywordCandidateClient,
    KeywordCandidateResult,
)
from mindreport.services.narrative import (
    MindReportNarrativeResult,
    NarrativeClient,
)
from mindreport.services.scoring import (
    EmotionScoreClient,
    MindReportScoringResult,
)


MindReportPeriodType = Literal['week', 'month']

MindReportGraphStatus = Literal[
    'running',
    'insufficient_data',
    'fallback_ready',
    'safety_ready',
    'needs_revision',
    'blocked',
    'completed',
]

MindReportValidationStatus = Literal[
    'passed',
    'needs_revision',
    'blocked',
]

MindReportValidationSeverity = Literal[
    'info',
    'warning',
    'error',
]


class MindReportValidationIssue(TypedDict):
    code: str
    message: str
    severity: MindReportValidationSeverity
    target: str


class MindReportValidationResult(TypedDict):
    status: MindReportValidationStatus
    issues: list[MindReportValidationIssue]
    message: str


class MindReportGraphState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes for mind report generation."""

    # Request context
    user: Any
    period_type: MindReportPeriodType
    target_date: date | None
    year: int | None
    month: int | None
    period_name: str

    # Optional dependency-injected clients used by tests and controlled execution.
    score_client: EmotionScoreClient | None
    keyword_client: KeywordCandidateClient | None
    cause_client: CauseKeywordClient | None
    narrative_client: NarrativeClient | None

    # Agent outputs
    collection_result: MindReportCollectionResult
    scoring_result: MindReportScoringResult
    emotion_flow: EmotionFlowResult | None
    alternative_plan: AlternativePlanResult | None
    keyword_result: KeywordCandidateResult | None
    cause_result: CauseKeywordResult | None
    label_result: LabelDisplayResult | None
    narrative_result: MindReportNarrativeResult | None
    validation_result: MindReportValidationResult

    # Final payloads
    report_payload: dict[str, Any]
    fallback_payload: dict[str, Any]

    # Chain control
    status: MindReportGraphStatus
    next_node: str
    revision_target: str
    revision_instructions: list[str]
    retry_count: int
    max_retries: int
    error: str | None
    trace: list[dict[str, Any]]


def build_initial_mindreport_state(
    *,
    user: Any,
    period_type: MindReportPeriodType,
    target_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
    period_name: str = '',
    score_client: EmotionScoreClient | None = None,
    keyword_client: KeywordCandidateClient | None = None,
    cause_client: CauseKeywordClient | None = None,
    narrative_client: NarrativeClient | None = None,
    max_retries: int = 1,
) -> MindReportGraphState:
    return {
        'user': user,
        'period_type': period_type,
        'target_date': target_date,
        'year': year,
        'month': month,
        'period_name': period_name,
        'score_client': score_client,
        'keyword_client': keyword_client,
        'cause_client': cause_client,
        'narrative_client': narrative_client,
        'status': 'running',
        'retry_count': 0,
        'max_retries': max_retries,
        'revision_target': '',
        'revision_instructions': [],
        'error': None,
        'trace': [],
    }


def append_trace(
    state: MindReportGraphState,
    *,
    node: str,
    status: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> MindReportGraphState:
    trace = list(state.get('trace', []))
    trace.append(
        {
            'node': node,
            'status': status,
            'message': message,
            'payload': payload or {},
        }
    )
    return {
        **state,
        'trace': trace,
    }

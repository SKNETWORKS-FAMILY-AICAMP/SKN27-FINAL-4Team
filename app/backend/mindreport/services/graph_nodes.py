from __future__ import annotations

from django.utils import timezone

from mindreport.services.cause_keyword_agent import MindReportCauseKeywordAgent
from mindreport.services.criteria_agent import MindReportGenerationCriteriaAgent
from mindreport.services.emotion_analysis_agent import MindReportEmotionAnalysisAgent
from mindreport.services.fallback_service import FallbackReportService
from mindreport.services.graph_state import MindReportGraphState, append_trace
from mindreport.services.narrative_action_agent import MindReportNarrativeActionAgent
from mindreport.services.payloads import (
    build_report_payload_from_state,
    report_period_name as _period_name,
    report_range_text as _range_text,
)
from mindreport.services.validation_agent import MindReportValidationAgent


def collect_and_check_criteria_node(
    state: MindReportGraphState,
) -> MindReportGraphState:
    return MindReportGenerationCriteriaAgent().run(state)


def score_and_analyze_emotion_node(
    state: MindReportGraphState,
) -> MindReportGraphState:
    return MindReportEmotionAnalysisAgent().run(state)


def extract_and_classify_causes_node(
    state: MindReportGraphState,
) -> MindReportGraphState:
    return MindReportCauseKeywordAgent().run(state)


def generate_narrative_and_actions_node(
    state: MindReportGraphState,
) -> MindReportGraphState:
    return MindReportNarrativeActionAgent().run(state)


def validate_report_node(state: MindReportGraphState) -> MindReportGraphState:
    return MindReportValidationAgent().run(state)


def safety_response_node(state: MindReportGraphState) -> MindReportGraphState:
    report_payload = {
        'id': f"safety-{state['user'].id}-{int(timezone.now().timestamp())}",
        'type': _period_name(state),
        'range': _range_text(state),
        'title': '지금은 안전을 먼저 확인할 시간이에요',
        'summary': (
            '현재 기록에는 즉시 안전을 확인해야 할 수 있는 표현이 포함되어 '
            '일반 마음리포트와 활동 추천을 제공하지 않습니다.'
        ),
        'stressCauses': [],
        'reliefCauses': [],
        'emotions': [],
        'analysis': [
            '혼자 감당하지 말고 지금 신뢰할 수 있는 사람에게 현재 상태를 알려주세요.',
            '즉각적인 위험이 있다면 지역 응급 서비스나 가까운 의료기관에 도움을 요청하세요.',
        ],
        'recommendations': [
            '안전한 장소로 이동하고 혼자 있지 않기',
            '신뢰할 수 있는 사람 또는 전문 지원기관에 즉시 연락하기',
        ],
        'is_fallback': False,
        'is_safety_response': True,
    }
    next_state: MindReportGraphState = {
        **state,
        'report_payload': report_payload,
        'status': 'safety_ready',
    }
    return append_trace(
        next_state,
        node='safety_response',
        status='safety_ready',
        message='고위험 표현을 감지하여 안전 응답으로 전환했습니다.',
        payload={
            'validation_issue_codes': [
                issue['code']
                for issue in state['validation_result']['issues']
            ],
        },
    )


def format_report_node(state: MindReportGraphState) -> MindReportGraphState:
    report_payload = build_report_payload_from_state(state)
    next_state: MindReportGraphState = {
        **state,
        'report_payload': report_payload,
        'status': 'completed',
    }
    return append_trace(
        next_state,
        node='format_report',
        status='completed',
        message='프론트엔드 응답용 마음리포트 payload를 생성했습니다.',
        payload={
            'report_id': report_payload['id'],
            'type': report_payload['type'],
        },
    )


def fallback_report_node(state: MindReportGraphState) -> MindReportGraphState:
    period_name = _period_name(state)
    fallback_payload = FallbackReportService.generate_fallback_report(
        user=state['user'],
        report_type=period_name,
        range_text=_range_text(state),
    )
    next_state: MindReportGraphState = {
        **state,
        'fallback_payload': fallback_payload,
        'status': 'fallback_ready',
    }
    return append_trace(
        next_state,
        node='fallback_report',
        status='fallback_ready',
        message='데이터 부족 또는 검증 중단 사유로 폴백 리포트를 생성했습니다.',
        payload={
            'type': fallback_payload.get('type'),
            'reason': state.get('error'),
        },
    )

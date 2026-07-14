from dataclasses import replace
from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from chat.models import ChatMessage, ChatSession
from mindreport.services.cause_keywords import (
    FLOW_SCORE_UPWARD,
    determine_label_display_policy,
)
from mindreport.services.cause_keyword_agent import MindReportCauseKeywordAgent
from mindreport.services.criteria_agent import (
    FALLBACK_ROUTE,
    GENERATION_ROUTE,
    MindReportGenerationCriteriaAgent,
)
from mindreport.services.flow import (
    STEP_ANALYSIS_ACTION,
    STEP_CAUSE_KEYWORDS,
    STEP_DATA_COLLECTION,
    STEP_DATA_SHORTAGE_SUPPORT,
    STEP_EMOTION_PATTERN,
    STEP_EMOTION_SCORING,
    STEP_FLOW_ALTERNATIVES,
    STEP_GENERATION_CRITERIA,
    STEP_KEYWORD_CANDIDATES,
    STEP_LABEL_EQUAL,
    STEP_LABEL_DISPLAY,
    STEP_LABEL_UPWARD,
    STEP_SCORE_DOWNWARD,
    STEP_SCORE_MAINTENANCE,
    STEP_SCORE_UPWARD,
    STEP_SCORE_VOLATILE,
    STEP_TIME_SERIES_FLOW,
    MindReportFlowService,
)
from mindreport.services.emotion_flow import (
    FLOW_SCORE_DOWNWARD,
    FLOW_SCORE_UPWARD as FLOW_SCORE_UPWARD_FROM_FLOW,
    FLOW_SCORE_VOLATILE,
    analyze_emotion_flow,
)
from mindreport.services.emotion_analysis_agent import MindReportEmotionAnalysisAgent
from mindreport.services.narrative_action_agent import MindReportNarrativeActionAgent
from mindreport.services.validation_agent import (
    VALIDATION_ROUTE_CAUSE,
    VALIDATION_ROUTE_CRITERIA,
    VALIDATION_ROUTE_EMOTION,
    VALIDATION_ROUTE_FALLBACK,
    VALIDATION_ROUTE_NARRATIVE,
    VALIDATION_ROUTE_SAFETY,
    MindReportValidationAgent,
)
from mindreport.services.scoring import (
    AFFECT_SCORING_METHOD,
    EmotionScore,
    MindReportScoringService,
    ReportSourceMessage,
    build_emotion_scoring_payload,
    parse_emotion_scores,
)
from mindreport.services.graph_state import build_initial_mindreport_state
from mindreport.services.graph_flow import MindReportSupervisorAgent
from mindreport.models import MindReport


class FakeEmotionScoreClient:
    def __init__(self, emotion_score=0.0, emotion_state='neutral', emotion_label='normal'):
        self.emotion_score = emotion_score
        self.emotion_state = emotion_state
        self.emotion_label = emotion_label

    def score_messages(self, *, payload):
        score = self.emotion_score
        if score <= -1.0:
            score = 0.0
        elif score == 0.0:
            score = 50.0
        elif score <= 1.0:
            score = 100.0

        return {
            'daily_scores': [
                {
                    'source_date': group['source_date'],
                    'emotion_label': self.emotion_label,
                    'emotion_state': self.emotion_state,
                    'emotion_score': score,
                    'confidence': 0.9,
                    'emotional_evidence_count': len(group['messages']),
                    'evidence_message_ids': [
                        message['message_id'] for message in group['messages']
                    ],
                    'rationale': '테스트용 감정 점수',
                }
                for group in payload['daily_groups']
            ]
        }


class FakeDailyEmotionScoreClient:
    def __init__(self, daily_scores):
        self.daily_scores = tuple(daily_scores)

    def score_messages(self, *, payload):
        return {
            'daily_scores': [
                {
                    'source_date': group['source_date'],
                    'emotion_label': 'normal',
                    'emotion_state': self._state_for(score),
                    'emotion_score': score,
                    'confidence': 0.9,
                    'emotional_evidence_count': len(group['messages']),
                    'evidence_message_ids': [
                        message['message_id'] for message in group['messages']
                    ],
                    'rationale': '일자별 흐름 테스트 점수',
                }
                for group, score in zip(payload['daily_groups'], self.daily_scores)
            ]
        }

    def _state_for(self, score):
        if score >= 60:
            return 'positive'
        if score <= 40:
            return 'negative'
        return 'neutral'


class FakeKeywordCandidateClient:
    def __init__(self, keyword='발표 준비'):
        self.keyword = keyword
        self.last_payload = None

    def extract_candidates(self, *, payload):
        self.last_payload = payload
        message_ids = [message['message_id'] for message in payload['messages'][:2]]
        return {
            'candidates': [
                {
                    'keyword': self.keyword,
                    'confidence': 0.86,
                    'evidence_message_ids': message_ids,
                    'evidence_type': 'repeated_association',
                    'relationship': '여러 메시지에서 감정 맥락과 함께 반복됐습니다.',
                    'counter_evidence': [],
                    'rationale': '반복적으로 언급된 소재입니다.',
                }
            ]
        }


class EmptyKeywordCandidateClient:
    def extract_candidates(self, *, payload):
        return {'candidates': []}


class FakeCauseKeywordClient:
    def __init__(self, cause_type='stress'):
        self.cause_type = cause_type

    def classify_keywords(self, *, payload):
        return {
            'cause_keywords': [
                {
                    'keyword': candidate['keyword'],
                    'cause_type': self.cause_type,
                    'publishable': True,
                    'confidence': 0.72,
                    'rationale': '테스트용 원인 키워드 분류입니다.',
                }
                for candidate in payload['candidates']
            ]
        }


class FakeNarrativeClient:
    def __init__(self):
        self.last_payload = None

    def generate_narrative(self, *, payload):
        self.last_payload = payload
        return {
            'title': '진로를 고민하는 시간에 함께 살펴볼 작은 단서',
            'summary': '진로를 준비하며 할 일을 정리하는 과정에서 부담과 잠깐의 휴식이 함께 언급됐어요.',
            'analysis_sentences': [
                (
                    '최근 기록에서는 진로와 발표 준비처럼 앞으로 해야 할 일을 생각하는 이야기가 여러 번 이어졌어요. '
                    '해야 할 항목이 한꺼번에 떠오르는 순간에는 어디서부터 손대야 할지 막막하게 느껴졌을 가능성이 있어 보여요.'
                ),
                (
                    '부담에 관한 이야기 사이에는 잠깐 쉬거나 계획을 작은 단위로 나누려는 시도도 함께 담겨 있었어요. '
                    '이런 장면은 모든 문제를 바로 해결하기보다 당장 다룰 수 있는 범위를 줄이는 일이 숨을 고르는 데 도움이 될 수 있음을 보여줘요.'
                ),
                (
                    '앞으로는 일이 많았다는 사실만 보기보다 부담이 커진 시간대와 그 직전에 있었던 상황을 함께 살펴보는 편이 좋아요. '
                    '반대로 조금 편해졌던 순간에 무엇을 멈추거나 시작했는지도 짧게 남기면 자신에게 맞는 조절 방법을 찾는 단서가 될 수 있어요.'
                ),
            ],
            'action_recommendations': [
                (
                    '해야 할 일이 머릿속에서 겹칠 때 선택 부담을 줄일 수 있도록 오늘 할 일 하나만 가장 작은 행동으로 나눠보세요. '
                    '오늘 저녁 5분 동안 첫 행동을 적고, 가능하다면 그중 10분 안에 끝낼 수 있는 것부터 시작해보세요.'
                ),
                (
                    '계속 생각을 이어가는 것보다 짧은 멈춤이 다음 행동을 정하는 데 도움이 될 수 있어요. '
                    '일을 시작하기 전이나 마친 뒤 10분을 비워 물을 마시거나 천천히 걷고, 전후에 달라진 점을 한 줄로 남겨보세요.'
                ),
            ],
        }


class UnsafeNarrativeClient:
    def generate_narrative(self, *, payload):
        return {
            'analysis_sentences': ['당신은 우울증입니다.'],
            'action_recommendations': ['이 활동은 반드시 치료 효과가 있습니다.'],
        }


class RevisingNarrativeClient:
    def __init__(self):
        self.call_count = 0
        self.revision_instructions = []

    def generate_narrative(self, *, payload):
        self.call_count += 1
        self.revision_instructions = payload.get('revision_instructions', [])
        if not self.revision_instructions:
            return {
                'analysis_sentences': ['당신은 우울증입니다.'],
                'action_recommendations': ['반드시 치료됩니다.'],
            }
        return {
            'title': '부담을 나누어 바라보는 작은 시간',
            'summary': '해야 할 일을 이어가는 과정에서 부담과 잠시 숨을 고르려는 장면이 함께 나타났어요.',
            'analysis_sentences': [
                '최근 기록에서는 해야 할 일을 정리하려는 이야기와 여러 과제가 한꺼번에 떠오르는 장면이 이어졌어요. 무엇부터 시작할지 정하기 어려운 순간에는 평소보다 더 많은 에너지가 들었을 가능성이 있어 보여요.',
                '그 사이에는 잠깐 멈추거나 할 일을 나누어 보려는 시도도 함께 나타났어요. 문제 전체를 한 번에 해결하기보다 지금 다룰 수 있는 범위를 정하는 일이 부담을 덜어주는 단서가 될 수 있어요.',
                '앞으로는 부담이 커진 순간의 앞뒤 상황과 잠시 편해졌던 때의 행동을 함께 기록해보면 좋아요. 반복해서 도움이 된 조건이 보이면 자신에게 맞는 일상 조절 방법을 조금 더 구체적으로 찾을 수 있어요.',
            ],
            'action_recommendations': [
                '선택해야 할 항목을 줄이면 시작할 때 드는 부담을 낮추는 데 도움이 될 수 있어요. 오늘 저녁 5분 동안 가장 작은 행동 하나만 적고 10분 정도 시도해보세요.',
                '짧은 휴식은 생각을 멈추기 위한 것이 아니라 다음 행동을 고를 여유를 만드는 데 도움이 될 수 있어요. 시작 전 10분을 비워 천천히 걷거나 물을 마셔보세요.',
            ],
        }


class MindReportScoringServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='mindreport@example.com',
            password='password',
            nickname='리포트테스터',
        )
        self.session = ChatSession.objects.create(user=self.user, character='pori')

    def _create_user_messages(self, count):
        for index in range(count):
            ChatMessage.objects.create(
                session=self.session,
                role='user',
                content=f'오늘의 감정 기록 {index}',
                emotion_label='normal',
            )

    def _create_weekly_user_messages(self, count):
        start = date(2026, 7, 6)
        for index in range(count):
            message = ChatMessage.objects.create(
                session=self.session,
                role='user',
                content=f'일자별 감정 기록 {index}',
                emotion_label='normal',
            )
            created_at = timezone.make_aware(
                datetime.combine(
                    start.replace(day=start.day + index),
                    datetime.min.time(),
                )
            )
            ChatMessage.objects.filter(id=message.id).update(created_at=created_at)

    def test_weekly_scoring_does_not_start_when_criteria_is_not_met(self):
        self._create_user_messages(4)

        result = MindReportScoringService(
            score_client=FakeEmotionScoreClient()
        ).run(user=self.user, period_type='week')

        self.assertEqual(result.status, 'insufficient_data')
        self.assertFalse(result.eligibility['is_eligible'])
        self.assertEqual(result.emotion_scores, ())

    def test_generation_criteria_agent_selects_fallback_route(self):
        self._create_user_messages(4)
        state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
        )

        result = MindReportGenerationCriteriaAgent().run(state)

        self.assertEqual(result['status'], 'insufficient_data')
        self.assertEqual(result['next_node'], FALLBACK_ROUTE)
        self.assertEqual(
            MindReportGenerationCriteriaAgent.route(result),
            FALLBACK_ROUTE,
        )
        self.assertFalse(result['collection_result'].eligibility['is_eligible'])

    def test_generation_criteria_agent_selects_generation_route(self):
        self._create_user_messages(5)
        state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
        )

        result = MindReportGenerationCriteriaAgent().run(state)

        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['next_node'], GENERATION_ROUTE)
        self.assertEqual(
            MindReportGenerationCriteriaAgent.route(result),
            GENERATION_ROUTE,
        )
        self.assertTrue(result['collection_result'].eligibility['is_eligible'])

    @patch(
        'mindreport.services.graph_nodes.'
        'FallbackReportService.generate_fallback_report'
    )
    def test_supervisor_graph_enters_fallback_route_when_data_is_insufficient(
        self,
        generate_fallback_report,
    ):
        generate_fallback_report.return_value = {
            'id': 'fallback-test',
            'type': 'weekly',
            'is_fallback': True,
        }
        self._create_user_messages(4)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            period_name='weekly',
        )

        self.assertEqual(result['status'], 'fallback_ready')
        self.assertEqual(result['next_node'], FALLBACK_ROUTE)
        self.assertTrue(result['fallback_payload']['is_fallback'])
        self.assertEqual(
            [entry['node'] for entry in result['trace']],
            [
                'generation_criteria_and_graph_validation',
                'fallback_report',
            ],
        )

    def test_supervisor_graph_enters_generation_route_when_data_is_sufficient(self):
        self._create_user_messages(5)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            period_name='weekly',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['next_node'], GENERATION_ROUTE)
        self.assertFalse(result['report_payload']['is_fallback'])
        self.assertTrue(result['report_payload']['emotions'])
        self.assertEqual(
            {day['icon'] for day in result['report_payload']['emotions']},
            {'😐'},
        )
        self.assertEqual(
            [entry['node'] for entry in result['trace']],
            [
                'generation_criteria_and_graph_validation',
                'mind_emotion_analysis',
                'cause_keyword_extraction_and_classification',
                'analysis_evidence_and_action_generation',
                'report_validation',
                'format_report',
            ],
        )

    def test_emotion_analysis_agent_integrates_scoring_and_pattern_analysis(self):
        self._create_user_messages(5)
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)

        result = MindReportEmotionAnalysisAgent().run(criteria_state)

        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['scoring_result'].status, 'scored')
        self.assertEqual(len(result['scoring_result'].emotion_scores), 1)
        self.assertEqual(result['emotion_flow'].flow_type, 'score_maintenance')
        self.assertEqual(
            result['emotion_flow'].detected_by,
            'insufficient_repeated_observations',
        )
        trace_payload = result['trace'][-1]['payload']
        self.assertEqual(trace_payload['scoring_status'], 'scored')
        self.assertEqual(
            trace_payload['emotion_pattern']['flow_type'],
            'score_maintenance',
        )
        self.assertEqual(
            trace_payload['time_series']['detected_by'],
            'insufficient_repeated_observations',
        )

    def test_cause_keyword_agent_integrates_extraction_and_classification(self):
        self._create_user_messages(5)
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(keyword='meeting prep'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)

        result = MindReportCauseKeywordAgent().run(emotion_state)

        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['keyword_result'].status, 'extracted')
        self.assertEqual(len(result['keyword_result'].candidates), 1)
        self.assertEqual(result['cause_result'].status, 'classified')
        self.assertEqual(len(result['cause_result'].cause_keywords), 1)
        self.assertEqual(
            result['cause_result'].cause_keywords[0].cause_type,
            'stress',
        )
        self.assertEqual(result['label_result'].status, 'applied')
        trace_payload = result['trace'][-1]['payload']
        self.assertEqual(trace_payload['extraction']['candidate_count'], 1)
        self.assertEqual(trace_payload['classification']['stress_count'], 1)

    def test_supervisor_completes_report_when_no_cause_is_supported(self):
        self._create_user_messages(5)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=EmptyKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(
            result['keyword_result'].status,
            'no_supported_candidates',
        )
        self.assertEqual(result['cause_result'].status, 'no_supported_causes')
        self.assertEqual(result['report_payload']['stressCauses'], [])
        self.assertEqual(result['report_payload']['reliefCauses'], [])

    def test_narrative_action_agent_generates_evidence_and_practical_actions(self):
        self._create_user_messages(5)
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(keyword='meeting prep'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=FakeNarrativeClient(),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        cause_state = MindReportCauseKeywordAgent().run(emotion_state)

        result = MindReportNarrativeActionAgent().run(cause_state)

        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['narrative_result'].status, 'generated')
        narrative = result['narrative_result'].narrative
        self.assertEqual(len(narrative.analysis_sentences), 3)
        self.assertEqual(len(narrative.action_recommendations), 2)
        trace_payload = result['trace'][-1]['payload']
        self.assertEqual(
            trace_payload['evidence']['analysis_sentence_count'],
            3,
        )
        self.assertEqual(trace_payload['actions']['recommendation_count'], 2)

    def test_validation_agent_routes_unsafe_narrative_back_for_revision(self):
        self._create_user_messages(5)
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(keyword='meeting prep'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=UnsafeNarrativeClient(),
            max_retries=1,
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        cause_state = MindReportCauseKeywordAgent().run(emotion_state)
        narrative_state = MindReportNarrativeActionAgent().run(cause_state)

        result = MindReportValidationAgent().run(narrative_state)

        self.assertEqual(result['status'], 'needs_revision')
        self.assertEqual(result['revision_target'], VALIDATION_ROUTE_NARRATIVE)
        self.assertEqual(result['retry_count'], 1)
        issue_codes = {
            issue['code'] for issue in result['validation_result']['issues']
        }
        self.assertIn('diagnosis_or_treatment_claim', issue_codes)

        exhausted = MindReportValidationAgent().run(result)
        self.assertEqual(exhausted['status'], 'blocked')
        self.assertEqual(exhausted['revision_target'], VALIDATION_ROUTE_FALLBACK)

    def test_validation_rejects_internal_state_and_direct_quotes(self):
        self._create_user_messages(5)
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        cause_state = MindReportCauseKeywordAgent().run(emotion_state)
        complete_state = MindReportNarrativeActionAgent().run(cause_state)
        narrative_result = complete_state['narrative_result']

        disclosed_narrative = replace(
            narrative_result.narrative,
            title='감정 점수 75점으로 나타난 한 주',
        )
        disclosed = MindReportValidationAgent().run({
            **complete_state,
            'narrative_result': replace(
                narrative_result,
                narrative=disclosed_narrative,
            ),
        })
        disclosed_codes = {
            issue['code'] for issue in disclosed['validation_result']['issues']
        }
        self.assertIn('internal_score_or_state_disclosed', disclosed_codes)
        self.assertEqual(disclosed['revision_target'], VALIDATION_ROUTE_NARRATIVE)

        quoted_narrative = replace(
            narrative_result.narrative,
            title='기록에 담긴 “오늘의 감정 기록 0”이라는 말',
        )
        quoted = MindReportValidationAgent().run({
            **complete_state,
            'narrative_result': replace(
                narrative_result,
                narrative=quoted_narrative,
            ),
        })
        quoted_codes = {
            issue['code'] for issue in quoted['validation_result']['issues']
        }
        self.assertIn('direct_conversation_quote_disclosed', quoted_codes)
        self.assertEqual(quoted['revision_target'], VALIDATION_ROUTE_NARRATIVE)

    def test_supervisor_graph_routes_high_risk_language_to_safety_response(self):
        self._create_user_messages(5)
        first_message = ChatMessage.objects.filter(session=self.session).first()
        first_message.content = '죽고 싶고 사라지고 싶다.'
        first_message.save(update_fields=['content'])

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            period_name='weekly',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'safety_ready')
        self.assertEqual(result['revision_target'], VALIDATION_ROUTE_SAFETY)
        self.assertTrue(result['report_payload']['is_safety_response'])
        self.assertEqual(result['trace'][-1]['node'], 'safety_response')

    def test_supervisor_graph_regenerates_failed_narrative_with_feedback(self):
        self._create_user_messages(5)
        narrative_client = RevisingNarrativeClient()

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            period_name='weekly',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=narrative_client,
            max_retries=1,
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['retry_count'], 1)
        self.assertEqual(narrative_client.call_count, 2)
        self.assertTrue(narrative_client.revision_instructions)
        trace_nodes = [entry['node'] for entry in result['trace']]
        self.assertEqual(
            trace_nodes.count('analysis_evidence_and_action_generation'),
            2,
        )
        self.assertEqual(trace_nodes.count('report_validation'), 2)

    def test_validation_agent_routes_data_and_analysis_failures(self):
        self._create_user_messages(5)
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        cause_state = MindReportCauseKeywordAgent().run(emotion_state)
        complete_state = MindReportNarrativeActionAgent().run(cause_state)

        first_message = complete_state['collection_result'].source_messages[0]
        outside_message = replace(
            first_message,
            source_date=first_message.source_date - timedelta(days=14),
        )
        invalid_collection = replace(
            complete_state['collection_result'],
            source_messages=(
                outside_message,
                *complete_state['collection_result'].source_messages[1:],
            ),
        )
        period_result = MindReportValidationAgent().run({
            **complete_state,
            'collection_result': invalid_collection,
        })
        self.assertEqual(
            period_result['revision_target'],
            VALIDATION_ROUTE_CRITERIA,
        )

        invalid_flow = replace(
            complete_state['emotion_flow'],
            flow_type='score_upward',
            maintenance_type=None,
        )
        flow_result = MindReportValidationAgent().run({
            **complete_state,
            'emotion_flow': invalid_flow,
        })
        self.assertEqual(
            flow_result['revision_target'],
            VALIDATION_ROUTE_EMOTION,
        )

        first_keyword = complete_state['cause_result'].cause_keywords[0]
        invalid_keyword = replace(
            first_keyword,
            evidence_message_ids=(999999,),
            evidence_dates=('2099-01-01',),
        )
        invalid_causes = replace(
            complete_state['cause_result'],
            cause_keywords=(invalid_keyword,),
        )
        cause_result = MindReportValidationAgent().run({
            **complete_state,
            'cause_result': invalid_causes,
        })
        self.assertEqual(
            cause_result['revision_target'],
            VALIDATION_ROUTE_CAUSE,
        )

    def test_weekly_scoring_starts_after_criteria_is_met(self):
        self._create_user_messages(5)

        result = MindReportScoringService(
            score_client=FakeEmotionScoreClient()
        ).run(user=self.user, period_type='week')

        self.assertEqual(result.status, 'scored')
        self.assertTrue(result.eligibility['is_eligible'])
        self.assertEqual(len(result.source_messages), 5)
        self.assertEqual(len(result.emotion_scores), 1)
        self.assertEqual(result.emotion_scores[0].emotion_score, 50.0)
        self.assertEqual(result.emotion_scores[0].total_message_count, 5)

    def test_affect_dimensions_are_converted_to_score_by_server(self):
        source_messages = (
            ReportSourceMessage(1, date(2026, 7, 14), '오늘은 기쁘지만 조금 불안하다.', 'joy'),
        )

        scores = parse_emotion_scores(
            payload={
                'daily_scores': [{
                    'source_date': '2026-07-14',
                    'emotion_label': 'mixed',
                    'positive_affect': 3,
                    'negative_affect': 1,
                    'activation': 2,
                    'confidence': 0.72,
                    'emotional_evidence_count': 1,
                    'evidence_message_ids': [1],
                    'rationale': '긍정과 불안 표현이 함께 있습니다.',
                }],
            },
            source_messages=source_messages,
        )

        self.assertEqual(scores[0].emotion_score, 75.0)
        self.assertEqual(scores[0].emotion_state, 'positive')
        self.assertEqual(scores[0].confidence, 0.75)
        self.assertEqual(scores[0].scoring_method, AFFECT_SCORING_METHOD)

    def test_affect_dimensions_without_evidence_are_neutralized(self):
        source_messages = (
            ReportSourceMessage(1, date(2026, 7, 14), '일정을 확인했다.', 'normal'),
        )

        scores = parse_emotion_scores(
            payload={
                'daily_scores': [{
                    'source_date': '2026-07-14',
                    'positive_affect': 4,
                    'negative_affect': 0,
                    'activation': 4,
                    'confidence': 1,
                    'evidence_message_ids': [],
                }],
            },
            source_messages=source_messages,
        )

        self.assertEqual(scores[0].emotion_score, 50.0)
        self.assertEqual(scores[0].confidence, 0.0)
        self.assertEqual(scores[0].positive_affect, 0.0)

    def test_scoring_prompt_requests_dimensions_not_direct_score(self):
        payload = build_emotion_scoring_payload(
            period_type='week',
            messages=(
                ReportSourceMessage(1, date(2026, 7, 14), '오늘은 기쁘다.', 'joy'),
            ),
        )
        schema = payload['output_schema']['daily_scores'][0]

        self.assertEqual(payload['scoring_method'], AFFECT_SCORING_METHOD)
        self.assertIn('positive_affect', schema)
        self.assertIn('negative_affect', schema)
        self.assertNotIn('emotion_score', schema)

    def test_flow_classifies_pattern_and_enters_score_maintenance_with_rule_analysis(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        steps = {step.step: step for step in result.steps}
        self.assertEqual(steps[STEP_DATA_COLLECTION].status, 'completed')
        self.assertEqual(steps[STEP_DATA_COLLECTION].payload['source_message_count'], 5)
        self.assertEqual(steps[STEP_GENERATION_CRITERIA].status, 'passed')
        self.assertEqual(steps[STEP_DATA_SHORTAGE_SUPPORT].status, 'skipped')
        self.assertEqual(steps[STEP_EMOTION_SCORING].status, 'completed')
        self.assertEqual(steps[STEP_TIME_SERIES_FLOW].status, 'completed')
        self.assertEqual(
            steps[STEP_TIME_SERIES_FLOW].payload['detected_by'],
            'insufficient_repeated_observations',
        )
        self.assertEqual(steps[STEP_EMOTION_PATTERN].status, 'completed')
        self.assertEqual(
            steps[STEP_EMOTION_PATTERN].payload['flow_type'],
            'score_maintenance',
        )
        self.assertEqual(steps[STEP_SCORE_MAINTENANCE].status, 'entered')
        self.assertEqual(
            steps[STEP_SCORE_MAINTENANCE].payload['maintenance_flow']['maintenance_type'],
            'maintenance_insufficient',
        )
        self.assertEqual(steps[STEP_FLOW_ALTERNATIVES].status, 'completed')
        self.assertEqual(
            steps[STEP_FLOW_ALTERNATIVES].payload['candidates'][0]['category'],
            'low_burden_refresh',
        )

    def test_flow_enters_upward_branch_before_keyword_extraction(self):
        self._create_weekly_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeDailyEmotionScoreClient((40.0, 45.0, 52.0, 60.0, 68.0)),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week', target_date=date(2026, 7, 10))

        steps = {step.step: step for step in result.steps}
        self.assertEqual(steps[STEP_SCORE_UPWARD].status, 'entered')
        self.assertEqual(steps[STEP_SCORE_UPWARD].payload['flow']['flow_type'], 'score_upward')
        self.assertEqual(steps[STEP_SCORE_MAINTENANCE].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_VOLATILE].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_DOWNWARD].status, 'skipped')
        self.assertEqual(steps[STEP_FLOW_ALTERNATIVES].status, 'completed')
        self.assertEqual(
            steps[STEP_FLOW_ALTERNATIVES].payload['candidates'][0]['category'],
            'recovery_maintenance',
        )
        self.assertEqual(steps[STEP_KEYWORD_CANDIDATES].status, 'completed')
        self.assertEqual(steps[STEP_LABEL_UPWARD].status, 'entered')
        self.assertEqual(steps[STEP_LABEL_UPWARD].payload['stress_label_size'], 'compact')
        self.assertEqual(steps[STEP_LABEL_EQUAL].status, 'skipped')

    def test_flow_enters_volatile_branch_before_keyword_extraction(self):
        self._create_weekly_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeDailyEmotionScoreClient((70.0, 35.0, 75.0, 30.0, 68.0)),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week', target_date=date(2026, 7, 10))

        steps = {step.step: step for step in result.steps}
        self.assertEqual(steps[STEP_SCORE_UPWARD].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_MAINTENANCE].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_VOLATILE].status, 'entered')
        self.assertEqual(steps[STEP_SCORE_VOLATILE].payload['flow']['flow_type'], 'score_volatile')
        self.assertEqual(steps[STEP_SCORE_DOWNWARD].status, 'skipped')
        self.assertEqual(
            steps[STEP_FLOW_ALTERNATIVES].payload['candidates'][0]['category'],
            'rhythm_stabilization',
        )
        self.assertEqual(steps[STEP_KEYWORD_CANDIDATES].status, 'completed')
        self.assertEqual(steps[STEP_LABEL_UPWARD].status, 'skipped')
        self.assertEqual(steps[STEP_LABEL_EQUAL].status, 'entered')
        self.assertEqual(steps[STEP_LABEL_EQUAL].payload['stress_label_size'], 'default')

    def test_flow_enters_downward_branch_before_keyword_extraction(self):
        self._create_weekly_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeDailyEmotionScoreClient((70.0, 62.0, 54.0, 45.0, 38.0)),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week', target_date=date(2026, 7, 10))

        steps = {step.step: step for step in result.steps}
        self.assertEqual(steps[STEP_SCORE_UPWARD].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_MAINTENANCE].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_VOLATILE].status, 'skipped')
        self.assertEqual(steps[STEP_SCORE_DOWNWARD].status, 'entered')
        self.assertEqual(steps[STEP_SCORE_DOWNWARD].payload['flow']['flow_type'], 'score_downward')
        self.assertEqual(
            steps[STEP_FLOW_ALTERNATIVES].payload['candidates'][0]['category'],
            'burden_reduction',
        )
        self.assertEqual(steps[STEP_KEYWORD_CANDIDATES].status, 'completed')
        self.assertEqual(steps[STEP_LABEL_UPWARD].status, 'skipped')
        self.assertEqual(steps[STEP_LABEL_EQUAL].status, 'entered')
        self.assertEqual(steps[STEP_LABEL_EQUAL].payload['relief_label_size'], 'default')

    def test_flow_stops_after_generation_criteria_when_data_is_insufficient(self):
        self._create_user_messages(4)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        steps = {step.step: step for step in result.steps}
        self.assertEqual(steps[STEP_DATA_COLLECTION].status, 'completed')
        self.assertEqual(steps[STEP_DATA_COLLECTION].payload['source_message_count'], 4)
        self.assertEqual(steps[STEP_GENERATION_CRITERIA].status, 'blocked')
        self.assertEqual(steps[STEP_DATA_SHORTAGE_SUPPORT].status, 'not_implemented')
        self.assertEqual(steps[STEP_DATA_SHORTAGE_SUPPORT].payload, {})
        self.assertEqual(steps[STEP_EMOTION_SCORING].status, 'blocked')
        self.assertEqual(steps[STEP_TIME_SERIES_FLOW].status, 'blocked')
        self.assertEqual(steps[STEP_EMOTION_PATTERN].status, 'blocked')
        self.assertEqual(steps[STEP_FLOW_ALTERNATIVES].status, 'blocked')
        self.assertEqual(steps[STEP_KEYWORD_CANDIDATES].status, 'blocked')

    def test_single_day_positive_score_does_not_create_green_trend(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=1.0,
                emotion_state='positive',
                emotion_label='joy',
            ),
            keyword_client=FakeKeywordCandidateClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        maintenance = {
            step.step: step for step in result.steps
        }[STEP_SCORE_MAINTENANCE].payload['maintenance_flow']
        self.assertEqual(maintenance['maintenance_type'], 'maintenance_insufficient')
        self.assertIsNone(maintenance['tone_color'])
        self.assertFalse(maintenance['suggestions'])

    def test_single_day_negative_score_does_not_create_red_trend(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        maintenance = {
            step.step: step for step in result.steps
        }[STEP_SCORE_MAINTENANCE].payload['maintenance_flow']
        self.assertEqual(maintenance['maintenance_type'], 'maintenance_insufficient')
        self.assertIsNone(maintenance['tone_color'])
        self.assertFalse(maintenance['suggestions'])

    def test_rule_flow_analysis_detects_future_pattern_types(self):
        upward = analyze_emotion_flow(
            (
                self._emotion_score(1, 40.0, 'negative'),
                self._emotion_score(2, 45.0, 'neutral'),
                self._emotion_score(3, 52.0, 'neutral'),
                self._emotion_score(4, 60.0, 'positive'),
                self._emotion_score(5, 68.0, 'positive'),
            )
        )
        downward = analyze_emotion_flow(
            (
                self._emotion_score(1, 70.0, 'positive'),
                self._emotion_score(2, 62.0, 'positive'),
                self._emotion_score(3, 54.0, 'neutral'),
                self._emotion_score(4, 45.0, 'neutral'),
                self._emotion_score(5, 38.0, 'negative'),
            )
        )
        volatile = analyze_emotion_flow(
            (
                self._emotion_score(1, 70.0, 'positive'),
                self._emotion_score(2, 35.0, 'negative'),
                self._emotion_score(3, 75.0, 'positive'),
                self._emotion_score(4, 30.0, 'negative'),
                self._emotion_score(5, 68.0, 'positive'),
            )
        )

        self.assertEqual(upward.flow_type, FLOW_SCORE_UPWARD_FROM_FLOW)
        self.assertEqual(downward.flow_type, FLOW_SCORE_DOWNWARD)
        self.assertEqual(volatile.flow_type, FLOW_SCORE_VOLATILE)
        self.assertEqual(upward.detected_by, 'rule_time_series')

    def test_keyword_candidate_extraction_runs_after_score_maintenance(self):
        self._create_user_messages(5)
        keyword_client = FakeKeywordCandidateClient()

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(),
            keyword_client=keyword_client,
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        keyword_step = {
            step.step: step for step in result.steps
        }[STEP_KEYWORD_CANDIDATES]
        self.assertEqual(keyword_step.status, 'completed')
        self.assertEqual(keyword_step.payload['candidate_count'], 1)
        self.assertEqual(keyword_step.payload['candidates'][0]['keyword'], '발표 준비')
        self.assertNotIn('alternative_plan', keyword_client.last_payload)
        self.assertNotIn('daily_scores', keyword_client.last_payload)
        self.assertNotIn('emotion_flow', keyword_client.last_payload)

    def test_cause_keyword_llm_classifies_supported_stress_evidence(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        cause_step = {
            step.step: step for step in result.steps
        }[STEP_CAUSE_KEYWORDS]
        self.assertEqual(cause_step.status, 'completed')
        self.assertEqual(cause_step.payload['cause_keyword_count'], 1)
        self.assertEqual(cause_step.payload['cause_keywords'][0]['keyword'], '진로 고민')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['cause_type'], 'stress')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['classified_by'], 'llm')

    def test_cause_keyword_llm_classifies_supported_relief_evidence(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=1.0,
                emotion_state='positive',
                emotion_label='joy',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='산책'),
            cause_client=FakeCauseKeywordClient(cause_type='relief'),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        cause_step = {
            step.step: step for step in result.steps
        }[STEP_CAUSE_KEYWORDS]
        self.assertEqual(cause_step.status, 'completed')
        self.assertEqual(cause_step.payload['cause_keyword_count'], 1)
        self.assertEqual(cause_step.payload['cause_keywords'][0]['keyword'], '산책')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['cause_type'], 'relief')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['classified_by'], 'llm')

    def test_cause_keyword_classification_uses_llm_client_for_neutral_evidence(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(keyword='카페 방문'),
            cause_client=FakeCauseKeywordClient(cause_type='relief'),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        cause_step = {
            step.step: step for step in result.steps
        }[STEP_CAUSE_KEYWORDS]
        self.assertEqual(cause_step.status, 'completed')
        self.assertEqual(cause_step.payload['cause_keyword_count'], 1)
        self.assertEqual(cause_step.payload['cause_keywords'][0]['keyword'], '카페 방문')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['cause_type'], 'relief')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['classified_by'], 'llm')

    def test_label_display_uses_equal_size_for_current_maintenance_flow(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        steps = {step.step: step for step in result.steps}
        label_step = steps[STEP_LABEL_DISPLAY]
        self.assertEqual(label_step.status, 'completed')
        self.assertEqual(label_step.payload['emotion_flow_type'], 'score_maintenance')
        self.assertEqual(label_step.payload['stress_label_size'], 'default')
        self.assertEqual(label_step.payload['relief_label_size'], 'default')
        self.assertEqual(label_step.payload['labels'][0]['label_size'], 'default')
        self.assertEqual(steps[STEP_LABEL_UPWARD].status, 'skipped')
        self.assertEqual(steps[STEP_LABEL_EQUAL].status, 'entered')

    def test_label_display_policy_keeps_future_upward_flow_ready(self):
        policy = determine_label_display_policy(emotion_flow_type=FLOW_SCORE_UPWARD)

        self.assertEqual(policy.stress_label_size, 'compact')
        self.assertEqual(policy.relief_label_size, 'default')
        self.assertLess(policy.stress_display_weight, policy.relief_display_weight)

    def test_analysis_and_action_generation_runs_after_label_display(self):
        self._create_user_messages(5)
        narrative_client = FakeNarrativeClient()

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=narrative_client,
        ).run(user=self.user, period_type='week')

        narrative_step = {
            step.step: step for step in result.steps
        }[STEP_ANALYSIS_ACTION]
        self.assertEqual(narrative_step.status, 'completed')
        self.assertEqual(len(narrative_step.payload['analysis_sentences']), 3)
        self.assertEqual(len(narrative_step.payload['action_recommendations']), 2)
        self.assertEqual(
            narrative_client.last_payload['cause_keywords'][0]['keyword'],
            '진로 고민',
        )
        self.assertNotIn('label_display', narrative_client.last_payload)
        self.assertNotIn('emotion_scores', narrative_client.last_payload)
        self.assertNotIn('emotion_flow_type', narrative_client.last_payload)
        self.assertEqual(
            narrative_client.last_payload['alternative_plan']['candidates'][0]['category'],
            'low_burden_refresh',
        )

    def _emotion_score(
        self,
        day: int,
        score: float,
        state: str,
    ) -> EmotionScore:
        return EmotionScore(
            source_date=date(2026, 7, day),
            emotion_label='normal',
            emotion_state=state,
            emotion_score=score,
            confidence=0.9,
            emotional_evidence_count=1,
            total_message_count=1,
            evidence_message_ids=(day,),
            rationale='test',
        )


class MindReportGraphAPIViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='mindreport-api@example.com',
            password='password',
            nickname='리포트 API 테스트',
        )

    @patch(
        'mindreport.views.MindReportGenerateAPIView._is_last_week_of_month',
        return_value=False,
    )
    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_graph_report_payload_reaches_frontend_contract(
        self,
        supervisor_class,
        _is_last_week,
    ):
        supervisor_class.return_value.run.return_value = {
            'status': 'completed',
            'report_payload': self._report_payload(),
        }

        response = self.client.post('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        report = response.json()['reports'][0]
        self.assertEqual(report['title'], '테스트 마음 리포트')
        self.assertEqual(report['stressCauses'], ['회의 준비'])
        self.assertEqual(report['recommendations'], ['10분 쉬기'])
        self.assertFalse(report['is_fallback'])
        self.assertFalse(report['is_safety_response'])
        self.assertTrue(report['id'].startswith('weekly-'))
        self.assertEqual(MindReport.objects.filter(user=self.user).count(), 1)

    @patch(
        'mindreport.views.MindReportGenerateAPIView._is_last_week_of_month',
        return_value=False,
    )
    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_safety_payload_reaches_frontend_contract(
        self,
        supervisor_class,
        _is_last_week,
    ):
        payload = self._report_payload()
        payload.update({
            'title': '지금은 안전을 먼저 확인할 시간이에요',
            'stressCauses': [],
            'reliefCauses': [],
            'is_safety_response': True,
        })
        supervisor_class.return_value.run.return_value = {
            'status': 'safety_ready',
            'report_payload': payload,
        }

        response = self.client.post('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        report = response.json()['reports'][0]
        self.assertTrue(report['is_safety_response'])
        self.assertFalse(report['is_fallback'])
        self.assertTrue(report['id'].startswith('safety-weekly-'))

    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_get_returns_stored_reports_without_running_graph(self, supervisor_class):
        stored_report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text='2026.07.13 ~ 2026.07.19',
            title='저장된 마음 리포트',
            summary='저장된 요약',
            stress_causes=['일정'],
            relief_causes=['산책'],
            emotions=[],
            analysis=['저장된 분석'],
            recommendations=['잠깐 쉬기'],
        )

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reports'][0]['id'], f'weekly-{stored_report.id}')
        self.assertEqual(response.json()['reports'][0]['title'], '저장된 마음 리포트')
        supervisor_class.assert_not_called()

    def test_get_shows_only_latest_report_for_each_period(self):
        MindReport.objects.create(
            user=self.user,
            report_type='주간 (데이터 부족)',
            range_text='2026.07.13 생성',
            title='이전 리포트',
            summary='이전 요약',
        )
        latest_report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text='2026.07.13 ~ 2026.07.19',
            title='최신 리포트',
            summary='최신 요약',
        )

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['reports']), 1)
        self.assertEqual(response.json()['reports'][0]['id'], f'weekly-{latest_report.id}')


    @patch(
        'mindreport.views.MindReportGenerateAPIView._is_last_week_of_month',
        return_value=False,
    )
    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_refresh_updates_current_week_instead_of_creating_duplicate(
        self,
        supervisor_class,
        _is_last_week,
    ):
        supervisor_class.return_value.run.return_value = {
            'status': 'completed',
            'report_payload': self._report_payload(),
        }

        first_response = self.client.post('/api/report/generate/')
        second_response = self.client.post('/api/report/generate/')

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(MindReport.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            first_response.json()['reports'][0]['id'],
            second_response.json()['reports'][0]['id'],
        )

    @staticmethod
    def _report_payload():
        return {
            'id': 'graph-report',
            'type': '주간',
            'range': '2026.07.14 생성',
            'title': '테스트 마음 리포트',
            'summary': '테스트 요약',
            'stressCauses': ['회의 준비'],
            'reliefCauses': ['산책'],
            'emotions': [{'day': '14일', 'icon': '😐'}],
            'analysis': ['근거 문장'],
            'recommendations': ['10분 쉬기'],
            'is_fallback': False,
        }

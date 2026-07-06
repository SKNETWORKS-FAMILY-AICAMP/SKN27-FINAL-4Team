from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from chat.models import ChatMessage, ChatSession
from mindreport.services.cause_keywords import (
    FLOW_SCORE_UPWARD,
    determine_label_display_policy,
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
from mindreport.services.scoring import EmotionScore, MindReportScoringService


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
                    'rationale': '반복적으로 언급된 소재입니다.',
                }
            ]
        }


class FakeCauseKeywordClient:
    def __init__(self, cause_type='stress'):
        self.cause_type = cause_type

    def classify_keywords(self, *, payload):
        return {
            'cause_keywords': [
                {
                    'keyword': candidate['keyword'],
                    'cause_type': self.cause_type,
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
            'analysis_sentences': [
                '최근 기록에서는 진로 고민과 연결된 부담 표현이 반복되었습니다.',
                '부정 감정이 이어진 날짜의 대화가 원인 키워드 근거로 사용되었습니다.',
            ],
            'action_recommendations': [
                '오늘 해야 할 일을 가장 작은 단위로 나눠 적어보세요.',
                '잠깐 쉬는 시간을 먼저 확보해보세요.',
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
            'rule_time_series',
        )
        self.assertEqual(steps[STEP_EMOTION_PATTERN].status, 'completed')
        self.assertEqual(
            steps[STEP_EMOTION_PATTERN].payload['flow_type'],
            'score_maintenance',
        )
        self.assertEqual(steps[STEP_SCORE_MAINTENANCE].status, 'entered')
        self.assertEqual(
            steps[STEP_SCORE_MAINTENANCE].payload['maintenance_flow']['maintenance_type'],
            'gray_maintenance',
        )
        self.assertEqual(steps[STEP_FLOW_ALTERNATIVES].status, 'completed')
        self.assertEqual(
            steps[STEP_FLOW_ALTERNATIVES].payload['candidates'][0]['category'],
            'emotional_refresh',
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

    def test_score_maintenance_green_branch(self):
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
        self.assertEqual(maintenance['maintenance_type'], 'green_maintenance')
        self.assertEqual(maintenance['tone_color'], 'green')
        self.assertTrue(maintenance['suggestions'])

    def test_score_maintenance_red_branch(self):
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
        self.assertEqual(maintenance['maintenance_type'], 'red_maintenance')
        self.assertEqual(maintenance['tone_color'], 'red')
        self.assertTrue(maintenance['suggestions'])

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
        self.assertEqual(
            keyword_client.last_payload['alternative_plan']['candidates'][0]['category'],
            'emotional_refresh',
        )

    def test_cause_keyword_classification_uses_score_rule_for_negative_evidence(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        cause_step = {
            step.step: step for step in result.steps
        }[STEP_CAUSE_KEYWORDS]
        self.assertEqual(cause_step.status, 'completed')
        self.assertEqual(cause_step.payload['cause_keyword_count'], 1)
        self.assertEqual(cause_step.payload['cause_keywords'][0]['keyword'], '진로 고민')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['cause_type'], 'stress')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['classified_by'], 'score_rule')

    def test_cause_keyword_classification_uses_score_rule_for_positive_evidence(self):
        self._create_user_messages(5)

        result = MindReportFlowService(
            score_client=FakeEmotionScoreClient(
                emotion_score=1.0,
                emotion_state='positive',
                emotion_label='joy',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='산책'),
            narrative_client=FakeNarrativeClient(),
        ).run(user=self.user, period_type='week')

        cause_step = {
            step.step: step for step in result.steps
        }[STEP_CAUSE_KEYWORDS]
        self.assertEqual(cause_step.status, 'completed')
        self.assertEqual(cause_step.payload['cause_keyword_count'], 1)
        self.assertEqual(cause_step.payload['cause_keywords'][0]['keyword'], '산책')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['cause_type'], 'relief')
        self.assertEqual(cause_step.payload['cause_keywords'][0]['classified_by'], 'score_rule')

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
            narrative_client=narrative_client,
        ).run(user=self.user, period_type='week')

        narrative_step = {
            step.step: step for step in result.steps
        }[STEP_ANALYSIS_ACTION]
        self.assertEqual(narrative_step.status, 'completed')
        self.assertEqual(len(narrative_step.payload['analysis_sentences']), 2)
        self.assertEqual(len(narrative_step.payload['action_recommendations']), 2)
        self.assertEqual(
            narrative_client.last_payload['cause_keywords'][0]['keyword'],
            '진로 고민',
        )
        self.assertEqual(
            narrative_client.last_payload['label_display']['emotion_flow_type'],
            'score_maintenance',
        )
        self.assertEqual(
            narrative_client.last_payload['alternative_plan']['candidates'][0]['category'],
            'low_burden_recovery',
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

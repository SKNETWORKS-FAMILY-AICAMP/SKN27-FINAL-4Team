from dataclasses import replace
from datetime import date, datetime, timedelta
import importlib
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.apps import apps as django_apps
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from chat.models import ChatMessage, ChatSession
from mindreport.constants import (
    EMOTION_SCORE_NEGATIVE_MAX,
    EMOTION_SCORE_POSITIVE_MIN,
)
from mindreport.services.alternatives import build_alternative_plan
from mindreport.services.cause_keywords import (
    FLOW_SCORE_UPWARD,
    build_cause_keyword_payload,
    determine_label_display_policy,
    parse_cause_keywords,
)
from mindreport.services.cause_keyword_agent import MindReportCauseKeywordAgent
from mindreport.services.collection import (
    LtmEvent,
    collect_ltm_events,
    format_ltm_context,
)
from mindreport.services.criteria_agent import (
    FALLBACK_ROUTE,
    GENERATION_ROUTE,
    MindReportGenerationCriteriaAgent,
)
from mindreport.services.fallback_service import FallbackReportService
from mindreport.services.emotion_flow import (
    FLOW_SCORE_DOWNWARD,
    FLOW_SCORE_UPWARD as FLOW_SCORE_UPWARD_FROM_FLOW,
    FLOW_SCORE_VOLATILE,
    analyze_emotion_flow,
)
from mindreport.services.emotion_analysis_agent import MindReportEmotionAnalysisAgent
from mindreport.services.keyword_candidates import (
    KeywordCandidate,
    build_keyword_candidate_payload,
    parse_keyword_candidates,
)
from mindreport.services.narrative import MindReportNarrativeGenerator
from mindreport.services.narrative_action_agent import MindReportNarrativeActionAgent
from mindreport.services.payloads import (
    normalize_public_payload,
    select_comfort_message,
    serialize_report,
)
from mindreport.services.periods import (
    last_completed_month,
    last_completed_week_target_date,
    period_range_text,
    suggestion_time_context,
)
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
    LABEL_GROUNDED_AFFECT_SCORING_METHOD,
    KCELECTRA_SCORING_METHOD,
    SCORING_ROUTE_LABEL_GROUNDED,
    SCORING_ROUTE_LLM_FALLBACK,
    EmotionScore,
    MindReportScoringService,
    ReportSourceMessage,
    build_emotion_scoring_payload,
    load_source_messages,
    parse_emotion_scores,
)
from mindreport.services.graph_state import build_initial_mindreport_state
from mindreport.services.graph_flow import MindReportSupervisorAgent
from mindreport.models import MindReport
from ai.agents.web_agent import FallbackWebAgent


class MindReportSuggestionTimingTests(SimpleTestCase):
    def test_monthly_suggestions_use_generation_anchored_four_week_window(self):
        context = suggestion_time_context(
            period_type='month',
            year=2026,
            month=7,
            generated_on=date(2026, 8, 1),
        )

        self.assertEqual(context['analysis_period_start'], '2026-07-01')
        self.assertEqual(context['analysis_period_end'], '2026-07-31')
        self.assertEqual(context['action_window_start'], '2026-08-01')
        self.assertEqual(context['action_window_end'], '2026-08-28')
        self.assertEqual(context['action_window_days'], 28)


class MindReportScheduledPeriodTests(SimpleTestCase):
    def test_weekly_schedule_targets_the_completed_monday_to_sunday_week(self):
        target_date = last_completed_week_target_date(date(2026, 7, 27))

        self.assertEqual(target_date, date(2026, 7, 26))
        self.assertEqual(
            period_range_text(period_type='week', target_date=target_date),
            '2026.07.20 ~ 2026.07.26',
        )

    def test_monthly_schedule_targets_previous_month_across_year_boundary(self):
        self.assertEqual(last_completed_month(date(2026, 1, 1)), (2025, 12))


class MindReportFallbackSafetyTests(SimpleTestCase):
    @patch.dict(
        os.environ,
        {'OPENAI_API_KEY': '', 'TAVILY_API_KEY': ''},
    )
    def test_web_fallback_does_not_return_static_dummy_recommendations(self):
        recommendations = FallbackWebAgent.get_trendy_contents(
            age=20,
            gender='여성',
            hobbies=['독서'],
            interests=['전시'],
        )

        self.assertEqual(recommendations, [])

    @patch(
        'mindreport.services.fallback_service.FallbackWebAgent.get_trendy_contents',
        return_value=[],
    )
    def test_waiting_report_keeps_status_but_has_no_fake_analysis_data(
        self,
        _get_trendy_contents,
    ):
        report = FallbackReportService.generate_fallback_report(
            SimpleNamespace(id=7),
            report_type='주간',
            range_text='2026.07.20 ~ 2026.07.26',
        )

        self.assertEqual(report['stressCauses'], [])
        self.assertEqual(report['reliefCauses'], [])
        self.assertEqual(report['emotions'], [])
        self.assertEqual(report['recommendations'], [])
        self.assertEqual(report['title'], '주간 마음 리포트를 준비하고 있어요')
        self.assertTrue(any('계속 수집' in line for line in report['analysis']))
        self.assertIn('다음 정기 갱신', report['summary'])
        self.assertEqual(
            select_comfort_message(
                summary=report['summary'],
                analysis=report['analysis'],
                recommendations=report['recommendations'],
            ),
            '기록이 아직 적어도, 회원님은 마음을 천천히 알아갈 충분한 시간이 있어요.',
        )

    @patch(
        'mindreport.services.fallback_service.FallbackWebAgent.get_trendy_contents',
        return_value=[{
            'activity': '검색 근거 활동',
            'reason': 'Tavily 결과에 소개된 활동입니다.',
            'how_to': '공식 안내를 먼저 확인해보세요.',
        }],
    )
    def test_web_suggestion_is_explicitly_not_conversation_analysis(
        self,
        _get_trendy_contents,
    ):
        report = FallbackReportService.generate_fallback_report(
            SimpleNamespace(id=8),
            report_type='주간',
        )

        self.assertEqual(report['recommendations'], ['검색 근거 활동'])
        self.assertEqual(report['suggestionCards'][0]['title'], '검색 근거 활동')
        self.assertEqual(report['suggestionCards'][0]['sourceCandidate'], 'web_search')
        self.assertTrue(
            any('대화에서 분석한 결과가 아니라' in line for line in report['analysis'])
        )
        self.assertTrue(any(
            '왜 추천하나요?: Tavily 결과에 소개된 활동입니다.' in line
            for line in report['analysis']
        ))
        self.assertTrue(any(
            '어떻게 시작할까요?: 공식 안내를 먼저 확인해보세요.' in line
            for line in report['analysis']
        ))


class LegacyFallbackSanitizationTests(TestCase):
    def test_migration_clears_unverifiable_fallback_data_but_keeps_status(self):
        user = get_user_model().objects.create_user(
            email='legacy-fallback@example.com',
            password='password',
            nickname='기존 폴백 사용자',
        )
        report = MindReport.objects.create(
            user=user,
            report_type='주간 (데이터 부족)',
            range_text='2026.07.13 ~ 2026.07.19',
            title='마음 리포트 분석 대기 중',
            summary='근거가 확인되지 않는 추천 요약',
            stress_causes=['기록 수집 중...'],
            relief_causes=['기록 수집 중...'],
            emotions=[{'day': '14일', 'icon': '😐'}],
            analysis=['근거가 확인되지 않는 활동 추천'],
            recommendations=['근거가 확인되지 않는 활동'],
            is_fallback=True,
        )
        migration = importlib.import_module(
            'mindreport.migrations.0003_sanitize_legacy_fallback_reports'
        )

        migration.sanitize_legacy_fallback_reports(django_apps, None)

        report.refresh_from_db()
        self.assertEqual(report.title, '마음 리포트 분석 대기 중')
        self.assertEqual(report.range_text, '2026.07.13 ~ 2026.07.19')
        self.assertEqual(report.stress_causes, [])
        self.assertEqual(report.relief_causes, [])
        self.assertEqual(report.emotions, [])
        self.assertEqual(report.recommendations, [])
        self.assertTrue(any('과거 폴백 추천' in line for line in report.analysis))


class MindReportV2GraphCollectionTests(SimpleTestCase):
    @patch('chat.graph_memory_v2_base._get_driver')
    def test_collect_ltm_events_and_format_ltm_context_use_v2_schema(
        self,
        get_driver,
    ):
        session = MagicMock()
        session.run.return_value.data.return_value = [
            {
                'name': '가족 여행',
                'date': '2026-07-07',
                'end_date': '2026-07-09',
                'people': [
                    {'name': '민수', 'relation': '친구'},
                    {'name': None, 'relation': None},
                ],
                'emotions': ['joy'],
            }
        ]
        get_driver.return_value.session.return_value.__enter__.return_value = session

        events = collect_ltm_events(
            user=SimpleNamespace(id=17),
            period_type='week',
            target_date=date(2026, 7, 8),
        )
        result = format_ltm_context(events)

        query = session.run.call_args.args[0]
        self.assertIn('(ep:Episode', query)
        self.assertIn('[:RECORDS]', query)
        self.assertIn('[event_rel:HAS_EVENT]', query)
        self.assertIn('[on_rel:ON]', query)
        self.assertIn('[person_rel:RELATES_TO]', query)
        self.assertIn('[evoked:EVOKED]', query)
        self.assertNotIn('[:KNOWS]', query)
        self.assertNotIn('[:FELT]', query)
        self.assertEqual(
            session.run.call_args.kwargs,
            {
                'uid': 17,
                'start_date': '2026-07-06',
                'end_date': '2026-07-12',
            },
        )
        self.assertEqual(
            result,
            "- 사건 1: '가족 여행' (날짜: 2026-07-07 ~ 2026-07-09), "
            '연관 인물: 민수(친구), 관련 정서: 기쁨',
        )

    @patch('chat.graph_memory_v2_base._get_driver')
    def test_collect_ltm_events_returns_episode_centered_structured_facts(
        self,
        get_driver,
    ):
        session = MagicMock()
        session.run.return_value.data.return_value = [{
            'event_id': 'ev-team-meeting',
            'episode_id': 'ep-20',
            'episode_created_at': '2026-07-20T19:30:00+09:00',
            'name': '팀 프로젝트 회의',
            'cause': '일정 조율 갈등',
            'date': '2026-07-21',
            'end_date': None,
            'people': [{'name': '팀원', 'relation': '동료'}],
            'places': ['회의실'],
            'topics': ['학업'],
            'emotions': [{'type': 'anger', 'score': 0.78}],
        }]
        get_driver.return_value.session.return_value.__enter__.return_value = session

        events = collect_ltm_events(
            user=SimpleNamespace(id=17),
            period_type='week',
            target_date=date(2026, 7, 20),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].episode_date, '2026-07-20')
        self.assertEqual(events[0].occurs_start, '2026-07-21')
        self.assertEqual(events[0].people[0]['name'], '팀원')
        self.assertEqual(events[0].emotions[0]['score'], 0.78)

    @patch('chat.graph_memory_v2_base._get_driver', return_value=None)
    def test_format_ltm_context_returns_empty_message_without_v2_driver(
        self,
        _get_driver,
    ):
        events = collect_ltm_events(
            user=SimpleNamespace(id=17),
            period_type='week',
            target_date=date(2026, 7, 8),
        )
        result = format_ltm_context(events)

        self.assertEqual(result, '조회 가능한 장기 기억(LTM)이 없습니다.')


class FakeEmotionScoreClient:
    def __init__(self, emotion_score=0.0, emotion_state='neutral', emotion_label='normal'):
        self.emotion_score = emotion_score
        self.emotion_state = emotion_state
        self.emotion_label = emotion_label
        self.last_payload = None

    def score_messages(self, *, payload):
        self.last_payload = payload
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


class FakeAffectEmotionScoreClient:
    def __init__(self):
        self.last_payload = None

    def score_messages(self, *, payload):
        self.last_payload = payload
        return {
            'daily_scores': [
                {
                    'source_date': group['source_date'],
                    'emotion_label': 'joy',
                    'positive_affect': 3,
                    'negative_affect': 1,
                    'activation': 2,
                    'confidence': 0.75,
                    'emotional_evidence_count': len(group['messages']),
                    'evidence_message_ids': [
                        message['message_id'] for message in group['messages']
                    ],
                    'rationale': '테스트용 감정 차원 분석',
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
        keyword = payload['candidates'][0]['keyword']
        report_text = (
            f'이번 기록에서는 ‘{keyword}’에 관해 이야기할 때 잠시 여유가 생기고 긴장이 누그러졌다는 표현이 나타나, 마음을 쉬게 한 원인으로 보여요.'
            if self.cause_type == 'relief'
            else f'이번 기록에서는 ‘{keyword}’에 관해 이야기할 때 해야 할 일과 압박이 겹치며 부담이 커졌다는 표현이 나타나, 마음을 힘들게 한 원인으로 보여요.'
        )
        return {
            'cause_keywords': [
                {
                    'keyword': candidate['keyword'],
                    'cause_type': self.cause_type,
                    'publishable': True,
                    'confidence': 0.72,
                    'rationale': '테스트용 원인 키워드 분류입니다.',
                    'moment_description': (
                        f"'{candidate['keyword']}'와 함께하며 마음의 긴장이 조금 누그러졌어요."
                        if self.cause_type == 'relief'
                        else f"'{candidate['keyword']}'를 마주하며 마음의 부담이 커졌던 순간이에요."
                    ),
                }
                for candidate in payload['candidates']
            ],
            'cause_reports': {
                'stress': report_text if self.cause_type == 'stress' else '',
                'relief': report_text if self.cause_type == 'relief' else '',
            },
        }


class RevisingCauseKeywordClient(FakeCauseKeywordClient):
    def __init__(self):
        super().__init__(cause_type='stress')
        self.call_count = 0
        self.revision_instructions = []

    def classify_keywords(self, *, payload):
        self.call_count += 1
        self.revision_instructions = payload.get('revision_instructions', [])
        result = super().classify_keywords(payload=payload)
        if not self.revision_instructions:
            result['cause_keywords'][0]['moment_description'] = (
                '2099-01-01에 발표 준비 때문에 마음의 부담이 커졌던 순간이에요.'
            )
        return result


class FakeNarrativeClient:
    def __init__(self):
        self.last_payload = None

    def generate_narrative(self, *, payload):
        self.last_payload = payload
        candidates = payload['alternative_plan']['candidates'][:2]
        causes = payload.get('cause_keywords') or []
        related_cause = causes[0]['keyword'] if causes else ''
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
                    '진로를 준비하며 애쓴 리포트테스터님은, 모든 걸 한 번에 해내지 않아도 괜찮아요.'
                ),
            ],
            'action_recommendations': [
                (
                    '해야 할 일이 머릿속에서 겹칠 때 선택 부담을 줄일 수 있도록 할 일 하나만 가장 작은 행동으로 나눠보세요. '
                    '다음 저녁 식사 후 5분 동안 첫 행동을 적고, 가능하다면 그중 10분 안에 끝낼 수 있는 것부터 시작해보세요.'
                ),
                (
                    '계속 생각을 이어가는 것보다 짧은 멈춤이 다음 행동을 정하는 데 도움이 될 수 있어요. '
                    '일을 시작하기 전이나 마친 뒤 10분을 비워 물을 마시거나 천천히 걷고, 전후에 달라진 점을 한 줄로 남겨보세요.'
                ),
            ],
            'suggestion_cards': [
                {
                    'title': f"{candidate['title']}로 숨 고르기",
                    'reason': f"{related_cause or '이번 기록의 부담'}로 커진 부담을 덜고 시작 범위를 좁히는 데 도움이 돼요.",
                    'how': '다음 저녁 식사 후 5분 동안 가장 작은 첫 행동 하나만 적어 바로 시작해보세요.',
                    'source_candidate': candidate['title'],
                    'related_cause': related_cause,
                    'timing': 'routine',
                }
                for index, candidate in enumerate(candidates)
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
                '앞으로는 부담이 커진 순간의 앞뒤 상황과 잠시 편해졌던 때의 행동을 함께 기록해보면 좋아요. 해야 할 일을 이어온 리포트테스터님은, 잠시 숨을 고르며 자신의 속도로 가도 괜찮아요.',
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

    def _create_labeled_turns(self, count, label='joy'):
        for index in range(count):
            ChatMessage.objects.create(
                session=self.session,
                role='user',
                content=f'오늘의 감정 기록 {index}',
            )
            ChatMessage.objects.create(
                session=self.session,
                role='assistant',
                content=f'감정 기록 응답 {index}',
                emotion_label=label,
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
            result['report_payload']['comfortMessage'],
            '진로를 준비하며 애쓴 리포트테스터님은, 모든 걸 한 번에 해내지 않아도 괜찮아요.',
        )
        self.assertEqual(
            {day['emotion_score'] for day in result['report_payload']['emotions']},
            {50.0},
        )
        self.assertTrue(all(
            set(day) == {'day', 'emotion_score'}
            for day in result['report_payload']['emotions']
        ))
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
        target_date = date(2026, 7, 23)
        target_datetime = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        ChatMessage.objects.filter(session=self.session).update(
            created_at=target_datetime
        )
        narrative_client = FakeNarrativeClient()
        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            target_date=target_date,
            generated_on=target_date,
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(keyword='meeting prep'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=narrative_client,
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        cause_state = MindReportCauseKeywordAgent().run(emotion_state)

        result = MindReportNarrativeActionAgent(
            narrative_generator=MindReportNarrativeGenerator(
                narrative_client=narrative_client
            )
        ).run(cause_state)

        self.assertEqual(result['status'], 'running')
        self.assertEqual(result['narrative_result'].status, 'generated')
        narrative = result['narrative_result'].narrative
        self.assertEqual(len(narrative.analysis_sentences), 3)
        self.assertEqual(len(narrative.action_recommendations), 2)
        self.assertEqual(len(narrative.suggestion_cards), 2)
        self.assertEqual(
            narrative.suggestion_cards[0].source_candidate,
            narrative_client.last_payload['alternative_plan']['candidates'][0]['title'],
        )
        trace_payload = result['trace'][-1]['payload']
        self.assertEqual(
            trace_payload['evidence']['analysis_sentence_count'],
            3,
        )
        self.assertEqual(trace_payload['actions']['recommendation_count'], 2)
        support_guidance = narrative_client.last_payload['editorial_guidance'][
            'support_message'
        ]
        self.assertEqual(
            support_guidance['dominant_emotion_state'],
            'neutral',
        )
        self.assertEqual(
            support_guidance['recipient_name'],
            '리포트테스터님',
        )
        report_context = narrative_client.last_payload['report_context']
        self.assertEqual(report_context['analysis_period_start'], '2026-07-20')
        self.assertEqual(report_context['analysis_period_end'], '2026-07-23')
        self.assertEqual(report_context['generated_on'], '2026-07-23')
        self.assertEqual(report_context['action_window_end'], '2026-07-29')
        self.assertEqual(report_context['action_window_days'], 7)
        self.assertIn('격려', support_guidance['writing_direction'])
        self.assertEqual(
            narrative_client.last_payload['cause_context']['stress_report'],
            cause_state['cause_result'].stress_report,
        )
        self.assertTrue(
            narrative_client.last_payload['cause_keywords'][0]['moment_description']
        )
        self.assertTrue(any(
            '실행 계기를 먼저 정하고' in constraint
            for constraint in narrative_client.last_payload['constraints']
        ))

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

        generic_comfort_narrative = replace(
            narrative_result.narrative,
            analysis_sentences=(
                *narrative_result.narrative.analysis_sentences[:-1],
                '기록의 맥락을 차분히 살펴볼 수 있어요. 앞으로 도움이 되는 조건을 계속 찾아볼 수 있어요.',
            ),
        )
        generic_comfort = MindReportValidationAgent().run({
            **complete_state,
            'narrative_result': replace(
                narrative_result,
                narrative=generic_comfort_narrative,
            ),
        })
        generic_comfort_codes = {
            issue['code']
            for issue in generic_comfort['validation_result']['issues']
        }
        self.assertIn(
            'support_message_missing_recipient_name',
            generic_comfort_codes,
        )
        self.assertEqual(
            generic_comfort['revision_target'],
            VALIDATION_ROUTE_NARRATIVE,
        )

        impractical_card = replace(
            narrative_result.narrative.suggestion_cards[0],
            how='여유가 생기면 시간을 내어 가볍게 시작해보세요.',
        )
        impractical_narrative = replace(
            narrative_result.narrative,
            suggestion_cards=(
                impractical_card,
                *narrative_result.narrative.suggestion_cards[1:],
            ),
        )
        impractical = MindReportValidationAgent().run({
            **complete_state,
            'narrative_result': replace(
                narrative_result,
                narrative=impractical_narrative,
            ),
        })
        impractical_codes = {
            issue['code']
            for issue in impractical['validation_result']['issues']
        }
        self.assertIn('suggestion_start_not_practical', impractical_codes)
        self.assertEqual(
            impractical['revision_target'],
            VALIDATION_ROUTE_NARRATIVE,
        )

        view_relative_card = replace(
            narrative_result.narrative.suggestion_cards[0],
            how='오늘 저녁 식사 후 5분 동안 첫 행동 하나만 적고 멈춰보세요.',
        )
        view_relative = MindReportValidationAgent().run({
            **complete_state,
            'narrative_result': replace(
                narrative_result,
                narrative=replace(
                    narrative_result.narrative,
                    suggestion_cards=(
                        view_relative_card,
                        *narrative_result.narrative.suggestion_cards[1:],
                    ),
                ),
            ),
        })
        self.assertIn(
            'suggestion_timing_depends_on_view_date',
            {
                issue['code']
                for issue in view_relative['validation_result']['issues']
            },
        )

    def test_validation_rejects_public_cause_prose_and_routes_to_cause_agent(self):
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
        cause_result = complete_state['cause_result']
        unsafe_keyword = replace(
            cause_result.cause_keywords[0],
            moment_description=(
                '“오늘의 감정 기록 0”이라는 말로 감정 점수 75점이며 '
                '우울증입니다. 2099-01-01에 확인됐어요.'
            ),
        )
        unsafe_causes = replace(
            cause_result,
            cause_keywords=(unsafe_keyword,),
            stress_report='연락처 010-1234-5678 때문에 부담이 커졌어요.',
        )

        result = MindReportValidationAgent().run({
            **complete_state,
            'cause_result': unsafe_causes,
        })

        issue_codes = {
            issue['code'] for issue in result['validation_result']['issues']
        }
        self.assertIn('cause_internal_score_or_state_disclosed', issue_codes)
        self.assertIn('cause_direct_conversation_quote_disclosed', issue_codes)
        self.assertIn('cause_diagnosis_or_treatment_claim', issue_codes)
        self.assertIn('cause_excessive_personal_information', issue_codes)
        self.assertIn('unknown_cause_date', issue_codes)
        self.assertEqual(result['revision_target'], VALIDATION_ROUTE_CAUSE)

    def test_validation_rejects_unavailable_graph_event_reference(self):
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
        cause_result = complete_state['cause_result']
        unsupported_keyword = replace(
            cause_result.cause_keywords[0],
            graph_event_ids=('invented-event',),
        )

        result = MindReportValidationAgent().run({
            **complete_state,
            'cause_result': replace(
                cause_result,
                cause_keywords=(unsupported_keyword,),
            ),
        })

        issue_codes = {
            issue['code'] for issue in result['validation_result']['issues']
        }
        self.assertIn('unsupported_graph_event_evidence', issue_codes)
        self.assertEqual(result['revision_target'], VALIDATION_ROUTE_CAUSE)

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

    def test_supervisor_graph_regenerates_failed_cause_prose_with_feedback(self):
        self._create_user_messages(5)
        cause_client = RevisingCauseKeywordClient()

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            period_name='weekly',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=cause_client,
            narrative_client=FakeNarrativeClient(),
            max_retries=1,
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['retry_count'], 1)
        self.assertEqual(cause_client.call_count, 2)
        self.assertTrue(cause_client.revision_instructions)
        trace_nodes = [entry['node'] for entry in result['trace']]
        self.assertEqual(
            trace_nodes.count('cause_keyword_extraction_and_classification'),
            2,
        )
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

        first_score = complete_state['scoring_result'].emotion_scores[0]
        invalid_scoring = replace(
            complete_state['scoring_result'],
            emotion_scores=(
                replace(first_score, emotion_score=80.0, emotion_state='neutral'),
                *complete_state['scoring_result'].emotion_scores[1:],
            ),
        )
        score_state_result = MindReportValidationAgent().run({
            **complete_state,
            'scoring_result': invalid_scoring,
        })
        score_state_codes = {
            issue['code']
            for issue in score_state_result['validation_result']['issues']
        }
        self.assertIn('emotion_state_score_mismatch', score_state_codes)
        self.assertEqual(
            score_state_result['revision_target'],
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

    @patch('mindreport.services.electra_scorer.ElectraEmotionScorer')
    def test_default_scoring_blocks_when_kcelectra_model_is_unavailable(
        self,
        scorer_class,
    ):
        self._create_user_messages(5)
        scorer_class.return_value.model = None
        scorer_class.return_value.available = False

        result = MindReportScoringService().run(
            user=self.user,
            period_type='week',
        )

        self.assertEqual(result.status, 'scoring_model_unavailable')
        self.assertEqual(result.emotion_scores, ())

    @patch('ai.emotion.emotion_model.predict_emotion_full')
    def test_electra_scorer_remote_mode_returns_probs_matrix(self, mock_predict):
        mock_predict.return_value = (
            '기쁨', 0.9, {'기쁨': 0.8, '슬픔': 0.1, '분노': 0.05, '일반': 0.05}
        )
        from mindreport.services.electra_scorer import ElectraEmotionScorer
        scorer = ElectraEmotionScorer()
        with patch.object(scorer, 'model', None), patch.object(scorer, 'remote', True):
            self.assertTrue(scorer.available)
            probs = scorer.predict_probs(['오늘 너무 행복했다'])
            self.assertEqual(probs.shape, (1, 4))
            self.assertAlmostEqual(probs[0, 0], 0.8)

    @patch('ai.emotion.emotion_model.predict_emotion_full')
    def test_scoring_service_succeeds_with_remote_electra_scorer(self, mock_predict):
        self._create_user_messages(5)
        mock_predict.return_value = (
            '기쁨', 0.9, {'기쁨': 0.8, '슬픔': 0.1, '분노': 0.05, '일반': 0.05}
        )
        from mindreport.services.electra_scorer import ElectraEmotionScorer
        scorer = ElectraEmotionScorer()
        with patch.object(scorer, 'model', None), patch.object(scorer, 'remote', True):
            result = MindReportScoringService().run(
                user=self.user,
                period_type='week',
            )
            self.assertEqual(result.status, 'scored')
            self.assertEqual(len(result.emotion_scores), 1)

    def test_source_message_uses_only_immediately_following_assistant_label(self):
        first_user = ChatMessage.objects.create(
            session=self.session,
            role='user',
            content='첫 번째 사용자 응답',
        )
        second_user = ChatMessage.objects.create(
            session=self.session,
            role='user',
            content='두 번째 사용자 응답',
        )
        ChatMessage.objects.create(
            session=self.session,
            role='assistant',
            content='두 번째 응답에 대한 답변',
            emotion_label='sadness',
        )

        messages = load_source_messages(user=self.user, period_type='week')
        messages_by_id = {message.message_id: message for message in messages}

        self.assertIsNone(
            messages_by_id[first_user.id].persisted_emotion_label
        )
        self.assertEqual(
            messages_by_id[second_user.id].persisted_emotion_label,
            'sadness',
        )

    def test_scoring_uses_complete_persisted_labels_as_primary_route(self):
        self._create_labeled_turns(5, label='joy')
        client = FakeAffectEmotionScoreClient()

        result = MindReportScoringService(score_client=client).run(
            user=self.user,
            period_type='week',
        )

        self.assertEqual(result.status, 'scored')
        self.assertEqual(result.scoring_route, SCORING_ROUTE_LABEL_GROUNDED)
        self.assertEqual(
            client.last_payload['scoring_route'],
            SCORING_ROUTE_LABEL_GROUNDED,
        )
        payload_messages = client.last_payload['daily_groups'][0]['messages']
        self.assertEqual(
            {message['persisted_emotion_label'] for message in payload_messages},
            {'joy'},
        )
        self.assertEqual(result.emotion_scores[0].emotion_score, 75.0)
        self.assertEqual(
            result.emotion_scores[0].scoring_method,
            LABEL_GROUNDED_AFFECT_SCORING_METHOD,
        )

    def test_scoring_falls_back_to_raw_text_when_one_label_is_missing(self):
        self._create_labeled_turns(4, label='joy')
        ChatMessage.objects.create(
            session=self.session,
            role='user',
            content='라벨이 저장되지 않은 사용자 응답',
        )
        client = FakeAffectEmotionScoreClient()

        result = MindReportScoringService(score_client=client).run(
            user=self.user,
            period_type='week',
        )

        self.assertEqual(result.status, 'scored')
        self.assertEqual(result.scoring_route, SCORING_ROUTE_LLM_FALLBACK)
        self.assertEqual(
            client.last_payload['scoring_route'],
            SCORING_ROUTE_LLM_FALLBACK,
        )
        payload_messages = client.last_payload['daily_groups'][0]['messages']
        self.assertTrue(all(
            'persisted_emotion_label' not in message
            for message in payload_messages
        ))
        self.assertTrue(all(
            'current_emotion_label' in message
            for message in payload_messages
        ))
        self.assertEqual(result.emotion_scores[0].emotion_score, 75.0)
        self.assertEqual(
            result.emotion_scores[0].scoring_method,
            AFFECT_SCORING_METHOD,
        )

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

    def test_supervisor_classifies_maintenance_and_prepares_alternatives(self):
        self._create_user_messages(5)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(result['collection_result'].source_messages), 5)
        self.assertEqual(
            result['emotion_flow'].detected_by,
            'insufficient_repeated_observations',
        )
        self.assertEqual(
            result['emotion_flow'].flow_type,
            'score_maintenance',
        )
        self.assertEqual(
            result['emotion_flow'].maintenance_type,
            'maintenance_insufficient',
        )
        self.assertEqual(
            result['alternative_plan'].candidates[0].category,
            'low_burden_refresh',
        )

    def test_supervisor_enters_upward_flow_before_keyword_extraction(self):
        self._create_weekly_user_messages(5)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            target_date=date(2026, 7, 10),
            score_client=FakeDailyEmotionScoreClient((40.0, 45.0, 52.0, 60.0, 68.0)),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emotion_flow'].flow_type, 'score_upward')
        self.assertEqual(
            result['alternative_plan'].candidates[0].category,
            'recovery_maintenance',
        )
        self.assertEqual(result['keyword_result'].status, 'extracted')
        self.assertEqual(result['label_result'].policy.stress_emphasis, 'secondary')
        cause_label = result['report_payload']['causeLabels'][0]
        self.assertEqual(cause_label['keyword'], '발표 준비')
        self.assertEqual(cause_label['causeType'], 'stress')
        self.assertEqual(cause_label['emphasis'], 'secondary')
        self.assertEqual(cause_label['displayWeight'], 0.7)
        self.assertTrue(cause_label['momentDescription'])
        self.assertEqual(
            result['report_payload']['hardMoments'][0]['text'],
            cause_label['momentDescription'],
        )
        self.assertEqual(
            result['report_payload']['stressReport'],
            '이번 기록에서는 ‘발표 준비’에 관해 이야기할 때 해야 할 일과 압박이 겹치며 부담이 커졌다는 표현이 나타나, 마음을 힘들게 한 원인으로 보여요.',
        )

    def test_supervisor_enters_volatile_flow_before_keyword_extraction(self):
        self._create_weekly_user_messages(5)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            target_date=date(2026, 7, 10),
            score_client=FakeDailyEmotionScoreClient((70.0, 35.0, 75.0, 30.0, 68.0)),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emotion_flow'].flow_type, 'score_volatile')
        self.assertEqual(
            result['alternative_plan'].candidates[0].category,
            'rhythm_stabilization',
        )
        self.assertEqual(result['keyword_result'].status, 'extracted')
        self.assertEqual(result['label_result'].policy.stress_emphasis, 'primary')

    def test_supervisor_enters_downward_flow_before_keyword_extraction(self):
        self._create_weekly_user_messages(5)

        result = MindReportSupervisorAgent().run(
            user=self.user,
            period_type='week',
            target_date=date(2026, 7, 10),
            score_client=FakeDailyEmotionScoreClient((70.0, 62.0, 54.0, 45.0, 38.0)),
            keyword_client=FakeKeywordCandidateClient(),
            cause_client=FakeCauseKeywordClient(),
            narrative_client=FakeNarrativeClient(),
        )

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['emotion_flow'].flow_type, 'score_downward')
        self.assertEqual(
            result['alternative_plan'].candidates[0].category,
            'burden_reduction',
        )
        self.assertEqual(result['keyword_result'].status, 'extracted')
        self.assertEqual(result['label_result'].policy.relief_emphasis, 'primary')

    def test_single_day_positive_score_does_not_create_green_trend(self):
        flow = analyze_emotion_flow((self._emotion_score(1, 100.0, 'positive'),))

        self.assertEqual(flow.maintenance_type, 'maintenance_insufficient')
        self.assertIsNone(flow.tone_color)
        self.assertFalse(flow.suggestions)

    def test_single_day_negative_score_does_not_create_red_trend(self):
        flow = analyze_emotion_flow((self._emotion_score(1, 0.0, 'negative'),))

        self.assertEqual(flow.maintenance_type, 'maintenance_insufficient')
        self.assertIsNone(flow.tone_color)
        self.assertFalse(flow.suggestions)

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

    def test_kcelectra_flow_recomputes_state_from_weighted_score(self):
        flow = analyze_emotion_flow((
            replace(
                self._emotion_score(14, 57.36, 'negative'),
                emotion_label='슬픔',
                scoring_method=KCELECTRA_SCORING_METHOD,
            ),
        ))

        self.assertEqual(flow.daily_summaries[0].emotion_state, 'positive')

    def test_same_direction_kcelectra_jumps_are_upward_not_volatile(self):
        flow = analyze_emotion_flow((
            self._emotion_score(13, 24.64, 'negative'),
            self._emotion_score(14, 22.92, 'negative'),
            self._emotion_score(15, 57.36, 'positive'),
            self._emotion_score(16, 99.94, 'positive'),
            self._emotion_score(17, 99.40, 'positive'),
        ))

        self.assertEqual(flow.metrics['large_positive_jump_count'], 2)
        self.assertEqual(flow.metrics['large_negative_jump_count'], 0)
        self.assertEqual(flow.metrics['direction_change_count'], 0)
        self.assertEqual(flow.flow_type, FLOW_SCORE_UPWARD_FROM_FLOW)

    def test_kcelectra_context_reaches_keyword_and_cause_payloads(self):
        scores = (
            replace(
                self._emotion_score(14, 75.0, 'positive'),
                emotion_label='기쁨',
                scoring_method=KCELECTRA_SCORING_METHOD,
            ),
        )
        messages = (
            ReportSourceMessage(
                message_id=14,
                source_date=date(2026, 7, 14),
                content='합격 소식 덕분에 기뻤어.',
                emotion_label=None,
            ),
        )
        flow = analyze_emotion_flow(scores)
        alternative_plan = build_alternative_plan(flow)
        keyword_payload = build_keyword_candidate_payload(
            source_messages=messages,
            emotion_scores=scores,
            emotion_flow=flow,
            alternative_plan=alternative_plan,
        )

        self.assertEqual(
            keyword_payload['messages'][0]['model_emotion']['label'],
            '기쁨',
        )
        self.assertEqual(
            keyword_payload['scoring_context']['daily_results'][0][
                'scoring_method'
            ],
            KCELECTRA_SCORING_METHOD,
        )

        candidate = KeywordCandidate(
            keyword='합격 소식',
            confidence=0.9,
            evidence_message_ids=(14,),
            evidence_dates=('2026-07-14',),
            rationale='기쁨의 이유로 명시됐습니다.',
            evidence_type='explicit_causal',
            relationship='합격 소식 때문에 기뻤다고 표현했습니다.',
        )
        cause_payload = build_cause_keyword_payload(
            candidates=(candidate,),
            emotion_scores=scores,
            emotion_flow=flow,
            source_messages=messages,
        )
        self.assertEqual(
            cause_payload['scoring_context']['daily_results'][0][
                'emotion_label'
            ],
            '기쁨',
        )

    def test_graph_events_are_grounded_and_carried_into_cause_classification(self):
        graph_event = LtmEvent(
            event_id='ev-presentation',
            episode_id='ep-14',
            episode_date='2026-07-14',
            name='발표 준비',
            occurs_start='2026-07-15',
            occurs_end='',
            cause='준비할 내용이 많음',
            people=(),
            places=(),
            topics=('학업',),
            emotions=({'type': 'sadness', 'score': 0.7},),
        )
        message = ReportSourceMessage(
            message_id=14,
            source_date=date(2026, 7, 14),
            content='발표 준비할 게 너무 많아서 부담스러워.',
            emotion_label='sadness',
        )
        parsed = parse_keyword_candidates(
            payload={'candidates': [{
                'keyword': '발표 준비',
                'confidence': 0.91,
                'evidence_message_ids': [14],
                'evidence_type': 'explicit_causal',
                'relationship': '준비할 일이 많아 부담스럽다고 표현했습니다.',
                'graph_event_ids': ['ev-presentation', 'ev-invented'],
            }]},
            source_messages=(message,),
            graph_events=(graph_event,),
        )

        self.assertEqual(parsed[0].graph_event_ids, ('ev-presentation',))
        cause_payload = build_cause_keyword_payload(
            candidates=parsed,
            emotion_scores=(),
            emotion_flow=analyze_emotion_flow(()),
            source_messages=(message,),
            graph_events=(graph_event,),
        )
        self.assertEqual(
            cause_payload['candidates'][0]['graph_events'][0]['name'],
            '발표 준비',
        )
        self.assertTrue(any(
            '사건명, cause, 인물, 장소, 주제 관계' in constraint
            for constraint in cause_payload['constraints']
        ))
        self.assertIn('cause_reports', cause_payload['output_schema'])
        self.assertTrue(any(
            '대표 날짜' in constraint
            for constraint in cause_payload['constraints']
        ))

    def test_duplicate_moment_descriptions_receive_distinct_safe_fallbacks(self):
        candidates = tuple(
            KeywordCandidate(
                keyword=keyword,
                confidence=0.9,
                evidence_message_ids=(index,),
                evidence_dates=('2026-07-14',),
                rationale='명시적 부담 표현',
                evidence_type='explicit_causal',
                relationship='부담스럽다고 직접 표현했습니다.',
            )
            for index, keyword in enumerate(('발표 준비', '면접 준비'), start=1)
        )
        duplicate = '준비 과정에서 해야 할 일이 겹치며 마음이 무거워졌던 순간이에요.'
        parsed = parse_cause_keywords(
            payload={'cause_keywords': [
                {
                    'keyword': candidate.keyword,
                    'cause_type': 'stress',
                    'publishable': True,
                    'confidence': 0.8,
                    'rationale': '테스트 근거',
                    'moment_description': duplicate,
                }
                for candidate in candidates
            ]},
            candidates=candidates,
        )

        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0].moment_description, duplicate)
        self.assertNotEqual(
            parsed[0].moment_description,
            parsed[1].moment_description,
        )

    def test_low_confidence_cause_is_not_published_as_a_hard_moment(self):
        candidate = KeywordCandidate(
            keyword='발표 준비',
            confidence=0.9,
            evidence_message_ids=(1,),
            evidence_dates=('2026-07-14',),
            rationale='명시적인 부담 표현',
            evidence_type='explicit_causal',
            relationship='부담스럽다고 직접 표현했습니다.',
        )

        parsed = parse_cause_keywords(
            payload={'cause_keywords': [{
                'keyword': candidate.keyword,
                'cause_type': 'stress',
                'publishable': True,
                'confidence': 0.59,
                'rationale': '근거가 약함',
                'moment_description': '발표를 준비하며 해야 할 일이 겹쳐 마음이 무거워졌던 순간이에요.',
            }]},
            candidates=(candidate,),
        )

        self.assertEqual(parsed, ())

    def test_json_string_true_still_runs_full_cause_validation(self):
        candidate = KeywordCandidate(
            keyword='발표 준비',
            confidence=0.9,
            evidence_message_ids=(1,),
            evidence_dates=('2026-07-14',),
            rationale='명시적인 부담 표현',
            evidence_type='explicit_causal',
            relationship='부담스럽다고 직접 표현했습니다.',
        )

        parsed = parse_cause_keywords(
            payload={'cause_keywords': [{
                'keyword': candidate.keyword,
                'cause_type': 'stress',
                'publishable': 'true',
                'confidence': 0.8,
                'rationale': '직접 근거',
                'moment_description': '발표를 준비하며 해야 할 일이 겹쳐 마음이 무거워졌던 순간이에요.',
            }]},
            candidates=(candidate,),
        )

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].cause_type, 'stress')
        self.assertGreaterEqual(parsed[0].confidence, 0.6)

    def test_non_polite_stress_description_is_replaced_with_polite_copy(self):
        candidate = KeywordCandidate(
            keyword='발표 준비',
            confidence=0.9,
            evidence_message_ids=(1,),
            evidence_dates=('2026-07-14',),
            rationale='명시적인 부담 표현',
            evidence_type='explicit_causal',
            relationship='부담스럽다고 직접 표현했습니다.',
        )
        non_polite = '발표를 준비하며 해야 할 일이 겹쳐 마음이 무거워진 순간이었다.'

        parsed = parse_cause_keywords(
            payload={'cause_keywords': [{
                'keyword': candidate.keyword,
                'cause_type': 'stress',
                'publishable': True,
                'confidence': 0.8,
                'rationale': '직접 근거',
                'moment_description': non_polite,
            }]},
            candidates=(candidate,),
        )

        self.assertEqual(len(parsed), 1)
        self.assertNotEqual(parsed[0].moment_description, non_polite)
        self.assertTrue(parsed[0].moment_description.endswith('요.'))

    def test_keyword_candidate_extraction_runs_after_score_maintenance(self):
        self._create_user_messages(5)
        keyword_client = FakeKeywordCandidateClient()

        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=keyword_client,
            cause_client=FakeCauseKeywordClient(),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        result = MindReportCauseKeywordAgent().run(emotion_state)

        self.assertEqual(result['keyword_result'].status, 'extracted')
        self.assertEqual(len(result['keyword_result'].candidates), 1)
        self.assertEqual(result['keyword_result'].candidates[0].keyword, '발표 준비')
        self.assertNotIn('alternative_plan', keyword_client.last_payload)
        self.assertNotIn('daily_scores', keyword_client.last_payload)
        self.assertNotIn('emotion_flow', keyword_client.last_payload)

    def test_cause_keyword_llm_classifies_supported_stress_evidence(self):
        self._create_user_messages(5)

        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        result = MindReportCauseKeywordAgent().run(emotion_state)

        cause_keywords = result['cause_result'].cause_keywords
        self.assertEqual(result['cause_result'].status, 'classified')
        self.assertEqual(len(cause_keywords), 1)
        self.assertEqual(cause_keywords[0].keyword, '진로 고민')
        self.assertEqual(cause_keywords[0].cause_type, 'stress')
        self.assertEqual(cause_keywords[0].classified_by, 'llm')

    def test_cause_keyword_llm_classifies_supported_relief_evidence(self):
        self._create_user_messages(5)

        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(
                emotion_score=1.0,
                emotion_state='positive',
                emotion_label='joy',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='산책'),
            cause_client=FakeCauseKeywordClient(cause_type='relief'),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        result = MindReportCauseKeywordAgent().run(emotion_state)

        cause_keywords = result['cause_result'].cause_keywords
        self.assertEqual(result['cause_result'].status, 'classified')
        self.assertEqual(len(cause_keywords), 1)
        self.assertEqual(cause_keywords[0].keyword, '산책')
        self.assertEqual(cause_keywords[0].cause_type, 'relief')
        self.assertEqual(cause_keywords[0].classified_by, 'llm')
        self.assertTrue(cause_keywords[0].moment_description.endswith('요.'))
        self.assertEqual(
            result['cause_result'].relief_report,
            '이번 기록에서는 ‘산책’에 관해 이야기할 때 잠시 여유가 생기고 긴장이 누그러졌다는 표현이 나타나, 마음을 쉬게 한 원인으로 보여요.',
        )

    def test_cause_keyword_classification_uses_llm_client_for_neutral_evidence(self):
        self._create_user_messages(5)

        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(),
            keyword_client=FakeKeywordCandidateClient(keyword='카페 방문'),
            cause_client=FakeCauseKeywordClient(cause_type='relief'),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        result = MindReportCauseKeywordAgent().run(emotion_state)

        cause_keywords = result['cause_result'].cause_keywords
        self.assertEqual(result['cause_result'].status, 'classified')
        self.assertEqual(len(cause_keywords), 1)
        self.assertEqual(cause_keywords[0].keyword, '카페 방문')
        self.assertEqual(cause_keywords[0].cause_type, 'relief')
        self.assertEqual(cause_keywords[0].classified_by, 'llm')

    def test_label_display_uses_equal_size_for_current_maintenance_flow(self):
        self._create_user_messages(5)

        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        result = MindReportCauseKeywordAgent().run(emotion_state)

        label_result = result['label_result']
        self.assertEqual(label_result.status, 'applied')
        self.assertEqual(label_result.policy.emotion_flow_type, 'score_maintenance')
        self.assertEqual(label_result.policy.stress_emphasis, 'primary')
        self.assertEqual(label_result.policy.relief_emphasis, 'primary')
        self.assertEqual(label_result.labels[0]['emphasis'], 'primary')

    def test_label_display_policy_keeps_future_upward_flow_ready(self):
        policy = determine_label_display_policy(emotion_flow_type=FLOW_SCORE_UPWARD)

        self.assertEqual(policy.stress_emphasis, 'secondary')
        self.assertEqual(policy.relief_emphasis, 'primary')
        self.assertLess(policy.stress_display_weight, policy.relief_display_weight)

    def test_analysis_and_action_generation_runs_after_label_display(self):
        self._create_user_messages(5)
        narrative_client = FakeNarrativeClient()

        initial_state = build_initial_mindreport_state(
            user=self.user,
            period_type='week',
            score_client=FakeEmotionScoreClient(
                emotion_score=-1.0,
                emotion_state='negative',
                emotion_label='sadness',
            ),
            keyword_client=FakeKeywordCandidateClient(keyword='진로 고민'),
            cause_client=FakeCauseKeywordClient(cause_type='stress'),
            narrative_client=narrative_client,
        )
        criteria_state = MindReportGenerationCriteriaAgent().run(initial_state)
        emotion_state = MindReportEmotionAnalysisAgent().run(criteria_state)
        cause_state = MindReportCauseKeywordAgent().run(emotion_state)
        result = MindReportNarrativeActionAgent().run(cause_state)

        narrative = result['narrative_result'].narrative
        self.assertEqual(result['narrative_result'].status, 'generated')
        self.assertEqual(len(narrative.analysis_sentences), 3)
        self.assertEqual(len(narrative.action_recommendations), 2)
        self.assertEqual(len(narrative.suggestion_cards), 2)
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
        self.client.force_login(self.user)

    def test_authentication_is_required(self):
        self.client.logout()

        response = self.client.get('/api/report/generate/')

        self.assertIn(response.status_code, (401, 403))

    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_get_automatically_creates_fallback_when_criteria_is_not_met(
        self,
        supervisor_class,
    ):
        payload = self._report_payload()
        payload.update({
            'type': '주간 (데이터 부족)',
            'title': '주간 마음 리포트를 준비하고 있어요',
            'stressCauses': [],
            'reliefCauses': [],
            'causeLabels': [],
            'emotions': [],
            'is_fallback': True,
        })
        supervisor_class.return_value.run.return_value = {
            'status': 'fallback_ready',
            'fallback_payload': payload,
        }

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        report = next(
            item for item in response.json()['reports']
            if item['type'].startswith('주간')
        )
        self.assertEqual(report['title'], '주간 마음 리포트를 준비하고 있어요')
        self.assertTrue(report['is_fallback'])
        self.assertTrue(report['id'].startswith('fallback-weekly-'))
        self.assertEqual(MindReport.objects.filter(user=self.user).count(), 2)

    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_get_automatically_creates_missing_full_weekly_report(
        self,
        supervisor_class,
    ):
        supervisor_class.return_value.run.return_value = {
            'status': 'completed',
            'report_payload': self._report_payload(),
        }

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        weekly_report = next(
            item for item in response.json()['reports']
            if item['type'] == '주간'
        )
        self.assertFalse(weekly_report['is_fallback'])
        self.assertEqual(supervisor_class.return_value.run.call_count, 2)

    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_get_automatically_catches_up_weekly_and_monthly_reports(
        self,
        supervisor_class,
    ):
        def graph_result(**kwargs):
            payload = self._report_payload()
            if kwargs['period_type'] == 'month':
                payload.update({
                    'type': '월간',
                    'range': '2026.07 월간 결산',
                    'title': '테스트 월간 마음 리포트',
                })
            return {'status': 'completed', 'report_payload': payload}

        supervisor_class.return_value.run.side_effect = graph_result

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {report['type'] for report in response.json()['reports']},
            {'주간', '월간'},
        )
        self.assertEqual(supervisor_class.return_value.run.call_count, 2)
        calls_by_period = {
            call.kwargs['period_type']: call.kwargs
            for call in supervisor_class.return_value.run.call_args_list
        }
        today = timezone.localdate()
        self.assertEqual(
            calls_by_period['week']['target_date'],
            last_completed_week_target_date(today),
        )
        self.assertEqual(
            (
                calls_by_period['month']['year'],
                calls_by_period['month']['month'],
            ),
            last_completed_month(today),
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
        self.assertEqual(report['causeLabels'][0]['emphasis'], 'secondary')
        self.assertEqual(
            report['hardMoments'][0]['text'],
            '회의를 준비하며 해야 할 일이 겹쳐 마음이 무거워졌던 순간이에요.',
        )
        self.assertEqual(
            report['reliefMoments'][0]['text'],
            '산책을 하며 굳어 있던 마음이 조금씩 편안해졌어요.',
        )
        self.assertEqual(
            report['stressReport'],
            '회의 준비 과정에서 해야 할 일이 겹치고 압박감이 커졌다는 표현이 함께 나타나, 마음을 힘들게 한 원인으로 보여요.',
        )
        self.assertEqual(
            report['reliefReport'],
            '산책하며 생긴 여유가 복잡한 생각을 가라앉히고 긴장을 누그러뜨렸다는 표현이 나타나, 마음을 쉬게 한 원인으로 보여요.',
        )
        self.assertEqual(report['recommendations'], ['10분 쉬기'])
        self.assertEqual(report['emotionScale'], {
            'heavyMax': float(EMOTION_SCORE_NEGATIVE_MAX),
            'lightMin': float(EMOTION_SCORE_POSITIVE_MIN),
        })
        self.assertEqual(report['suggestionCards'][0]['title'], '회의 전 5분 정리')
        self.assertEqual(report['suggestionCards'][0]['relatedCause'], '회의 준비')
        self.assertEqual(
            report['comfortMessage'],
            '테스트 요약',
        )
        self.assertFalse(report['is_fallback'])
        self.assertFalse(report['is_safety_response'])
        self.assertTrue(report['generatedAt'])
        self.assertTrue(report['id'].startswith('weekly-'))
        self.assertEqual(MindReport.objects.filter(user=self.user).count(), 1)

    def test_payload_formatter_does_not_invent_missing_cause_prose(self):
        payload = self._report_payload()
        cause_labels = [{
            'keyword': '회의 준비',
            'causeType': 'stress',
            'emphasis': 'secondary',
            'displayWeight': 0.7,
            'momentDescription': '',
            'harmonySummary': '',
            'graphEventIds': [],
            'evidenceDates': ['2026-07-14'],
        }]
        payload['causeLabels'] = cause_labels
        payload['hardMoments'] = []
        payload['reliefMoments'] = []

        normalized = normalize_public_payload(payload)
        stored_report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text='이번 주',
            title='검증된 문구만 사용하는 리포트',
            summary='검증된 요약 문장입니다.',
            stress_causes=['회의 준비'],
            relief_causes=[],
            cause_labels=cause_labels,
            emotions=[],
            analysis=[],
            recommendations=[],
        )
        serialized = serialize_report(stored_report)

        self.assertEqual(normalized['stressReport'], '')
        self.assertEqual(normalized['reliefReport'], '')
        self.assertEqual(serialized['stressReport'], '')
        self.assertEqual(serialized['reliefReport'], '')
        self.assertEqual(serialized['hardMoments'], [])
        self.assertEqual(serialized['reliefMoments'], [])

    def test_payload_uses_verified_moment_when_aggregate_report_is_invalid(self):
        payload = self._report_payload()
        payload['stressReport'] = '회의 준비였어요.'
        payload['reliefReport'] = '산책이었어요.'
        payload['causeLabels'][0]['harmonySummary'] = ''
        payload['causeLabels'][1]['harmonySummary'] = ''

        normalized = normalize_public_payload(payload)
        self.assertEqual(
            normalized['stressReport'],
            payload['causeLabels'][0]['momentDescription'],
        )
        self.assertEqual(
            normalized['reliefReport'],
            payload['causeLabels'][1]['momentDescription'],
        )

        stored_report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text='이번 주',
            title='대표 장면 안전망 리포트',
            summary='검증된 대표 장면을 표시하는 리포트예요.',
            stress_causes=['회의 준비'],
            relief_causes=['산책'],
            cause_labels=payload['causeLabels'],
            emotions=[],
            analysis=[],
            recommendations=[],
        )
        serialized = serialize_report(stored_report)
        self.assertEqual(
            serialized['stressReport'],
            payload['causeLabels'][0]['momentDescription'],
        )
        self.assertEqual(
            serialized['reliefReport'],
            payload['causeLabels'][1]['momentDescription'],
        )

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
            'causeLabels': [],
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

    @patch(
        'mindreport.views.MindReportGenerateAPIView._is_last_week_of_month',
        return_value=False,
    )
    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_invalid_graph_payload_is_not_persisted(
        self,
        supervisor_class,
        _is_last_week,
    ):
        supervisor_class.return_value.run.return_value = {
            'status': 'completed',
            'report_payload': {'type': '주간'},
        }

        response = self.client.post('/api/report/generate/')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()['code'], 'MINDREPORT_INVALID_PAYLOAD')
        self.assertFalse(MindReport.objects.filter(user=self.user).exists())

    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_get_returns_stored_reports_without_running_graph(self, supervisor_class):
        today = timezone.localdate()
        weekly_target = last_completed_week_target_date(today)
        monthly_year, monthly_month = last_completed_month(today)
        stored_report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text=period_range_text(
                period_type='week',
                target_date=weekly_target,
            ),
            title='저장된 마음 리포트',
            summary='저장된 요약',
            stress_causes=['일정'],
            relief_causes=['산책'],
            emotions=[],
            analysis=['저장된 분석'],
            recommendations=['잠깐 쉬기'],
        )
        MindReport.objects.create(
            user=self.user,
            report_type='월간',
            range_text=period_range_text(
                period_type='month',
                year=monthly_year,
                month=monthly_month,
            ),
            title='저장된 월간 마음 리포트',
            summary='저장된 월간 요약',
        )

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        weekly_report = next(
            item for item in response.json()['reports']
            if item['type'].startswith('주간')
        )
        self.assertEqual(weekly_report['id'], f'weekly-{stored_report.id}')
        self.assertEqual(weekly_report['title'], '저장된 마음 리포트')
        self.assertEqual(weekly_report['causeLabels'], [])
        supervisor_class.assert_not_called()

    @patch('mindreport.views.MindReportSupervisorAgent')
    def test_get_shows_only_latest_report_for_each_period(self, supervisor_class):
        today = timezone.localdate()
        weekly_target = last_completed_week_target_date(today)
        weekly_range = period_range_text(
            period_type='week',
            target_date=weekly_target,
        )
        monthly_year, monthly_month = last_completed_month(today)
        MindReport.objects.create(
            user=self.user,
            report_type='주간 (데이터 부족)',
            range_text=weekly_range,
            title='이전 리포트',
            summary='이전 요약',
            is_fallback=True,
        )
        latest_report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text=weekly_range,
            title='최신 리포트',
            summary='최신 요약',
        )
        MindReport.objects.create(
            user=self.user,
            report_type='월간',
            range_text=period_range_text(
                period_type='month',
                year=monthly_year,
                month=monthly_month,
            ),
            title='월간 리포트',
            summary='월간 요약',
        )

        response = self.client.get('/api/report/generate/')

        self.assertEqual(response.status_code, 200)
        weekly_reports = [
            item for item in response.json()['reports']
            if item['type'].startswith('주간')
        ]
        self.assertEqual(len(weekly_reports), 1)
        self.assertEqual(weekly_reports[0]['id'], f'weekly-{latest_report.id}')
        supervisor_class.assert_not_called()


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
        stale_generated_at = timezone.now() - timedelta(hours=2)
        MindReport.objects.filter(user=self.user).update(
            created_at=stale_generated_at
        )
        second_response = self.client.post('/api/report/generate/')

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(MindReport.objects.filter(user=self.user).count(), 1)
        self.assertEqual(
            first_response.json()['reports'][0]['id'],
            second_response.json()['reports'][0]['id'],
        )
        self.assertGreater(
            datetime.fromisoformat(
                second_response.json()['reports'][0]['generatedAt']
            ),
            stale_generated_at,
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
            'causeLabels': [
                {
                    'keyword': '회의 준비',
                    'causeType': 'stress',
                    'emphasis': 'secondary',
                    'displayWeight': 0.7,
                    'momentDescription': '회의를 준비하며 해야 할 일이 겹쳐 마음이 무거워졌던 순간이에요.',
                    'harmonySummary': '회의 준비 과정에서 해야 할 일이 겹치고 압박감이 커졌다는 표현이 함께 나타나, 마음을 힘들게 한 원인으로 보여요.',
                    'graphEventIds': ['ev-meeting'],
                    'evidenceDates': ['2026-07-14'],
                },
                {
                    'keyword': '산책',
                    'causeType': 'relief',
                    'emphasis': 'primary',
                    'displayWeight': 1.0,
                    'momentDescription': '산책을 하며 굳어 있던 마음이 조금씩 편안해졌어요.',
                    'harmonySummary': '산책하며 생긴 여유가 복잡한 생각을 가라앉히고 긴장을 누그러뜨렸다는 표현이 나타나, 마음을 쉬게 한 원인으로 보여요.',
                    'graphEventIds': ['ev-walk'],
                    'evidenceDates': ['2026-07-15'],
                },
            ],
            'hardMoments': [{
                'text': '회의를 준비하며 해야 할 일이 겹쳐 마음이 무거워졌던 순간이에요.',
                'keyword': '회의 준비',
                'evidenceDates': ['2026-07-14'],
            }],
            'reliefMoments': [{
                'text': '산책을 하며 굳어 있던 마음이 조금씩 편안해졌어요.',
                'keyword': '산책',
                'evidenceDates': ['2026-07-15'],
            }],
            'emotions': [{
                'day': '14일',
                'emotion_score': 50.0,
            }],
            'analysis': ['근거 문장'],
            'recommendations': ['10분 쉬기'],
            'suggestionCards': [{
                'title': '회의 전 5분 정리',
                'reason': '회의 준비로 커진 부담을 작은 순서로 나누는 데 도움이 될 수 있어요.',
                'how': '회의 전에 5분 동안 첫 순서 하나만 적어보세요.',
                'sourceCandidate': '해야 할 일 나누기',
                'relatedCause': '회의 준비',
                'timing': 'today',
            }],
            'is_fallback': False,
        }


class MindReportSafetyResponse24hExpirationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='safetytestuser@example.com',
            password='password',
            nickname='안전테스터',
        )

    def test_validate_safety_ignores_risk_signals_older_than_24_hours(self):
        agent = MindReportValidationAgent()
        now = timezone.now()

        old_risk_msg = ReportSourceMessage(
            message_id=1,
            source_date=(now - timedelta(hours=25)).date(),
            content='죽고 싶다 힘들다',
            emotion_label='슬픔',
            created_at=now - timedelta(hours=25),
        )
        state_old = {
            'collection_result': SimpleNamespace(source_messages=(old_risk_msg,)),
            'emotion_flow': SimpleNamespace(interpretation='해석'),
            'narrative_result': SimpleNamespace(narrative=None),
        }
        issues_old = agent._validate_safety(state_old)
        safety_issues_old = [i for i in issues_old if i['code'] == 'high_risk_signal_detected']
        self.assertEqual(len(safety_issues_old), 0)

        recent_risk_msg = ReportSourceMessage(
            message_id=2,
            source_date=(now - timedelta(hours=2)).date(),
            content='죽고 싶다 힘들다',
            emotion_label='슬픔',
            created_at=now - timedelta(hours=2),
        )
        state_recent = {
            'collection_result': SimpleNamespace(source_messages=(recent_risk_msg,)),
            'emotion_flow': SimpleNamespace(interpretation='해석'),
            'narrative_result': SimpleNamespace(narrative=None),
        }
        issues_recent = agent._validate_safety(state_recent)
        safety_issues_recent = [i for i in issues_recent if i['code'] == 'high_risk_signal_detected']
        self.assertEqual(len(safety_issues_recent), 1)

    def test_period_report_exists_expires_safety_response_after_24_hours(self):
        from mindreport.services.persistence import period_report_exists

        now = timezone.now()
        target_date = timezone.localdate(now)
        report = MindReport.objects.create(
            user=self.user,
            report_type='주간',
            range_text=period_range_text(
                period_type='week',
                target_date=target_date,
            ),
            title='안전 안내',
            summary='요약',
            is_safety_response=True,
        )
        MindReport.objects.filter(pk=report.pk).update(created_at=now - timedelta(hours=25))

        exists = period_report_exists(
            user=self.user,
            period_type='week',
            period_name='주간',
            target_date=target_date,
        )
        self.assertFalse(exists)

        MindReport.objects.filter(pk=report.pk).update(created_at=now - timedelta(hours=2))
        exists_recent = period_report_exists(
            user=self.user,
            period_type='week',
            period_name='주간',
            target_date=target_date,
        )
        self.assertTrue(exists_recent)


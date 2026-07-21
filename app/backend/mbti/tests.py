from dataclasses import dataclass
from datetime import datetime
from unittest import TestCase

from mbti.services.opening_rules import (
    evaluate_primary_opening,
    evaluate_secondary_opening,
)
from mbti.services.baseline_sources import (
    UserBaselineSnapshot,
    build_user_baseline_snapshot,
    extract_axis_letters_from_mbti_type,
)
from mbti.services.dashboard_payload import build_frontend_preparing_payload
from mbti.services.graph_scores import (
    calculate_axis_graph_score,
    calculate_monthly_graph_scores,
)
from mbti.services.llm_config import (
    DEFAULT_OPENAI_SCORING_MODEL,
    build_scoring_llm_config,
)
from mbti.services.monthly_results import (
    build_previous_monthly_baselines,
    combine_monthly_mbti,
    finalize_monthly_axis_preferences,
)
from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline
from mbti.services.monthly_questions import (
    MBTI_AXES,
    build_monthly_question_batch,
    resolve_month_period,
)
from mbti.services.reports import (
    ReportSection,
    _build_report_context,
    build_mypage_payload,
    generate_monthly_report,
    select_report_evidence,
)
from mbti.services.response_scoring import (
    MbtiResponseScore,
    build_axis_scoring_input,
    build_axis_scoring_system_prompt,
    _build_failed_scoring_payload,
    parse_axis_scoring_payload,
    score_primary_open_axes,
)


@dataclass(frozen=True)
class FakeQuestionResponse:
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


@dataclass(frozen=True)
class FakeResponseScore:
    axis: str
    score: float | None
    coding_status: str


@dataclass(frozen=True)
class FakeScoredResponse:
    response_id: int
    axis: str
    score: float | None
    coding_status: str
    reason: str


@dataclass(frozen=True)
class FakeMonthlyResultRecord:
    user_id: int
    period_key: str
    estimated_mbti_type: str | None


@dataclass(frozen=True)
class FakeOnboardingProfile:
    user_id: int
    mbti_type: str | None


@dataclass(frozen=True)
class FakeAxisResultRecord:
    user_id: int
    period_key: str
    axis: str
    selected_letter: str | None
    axis_avg: float | None = None
    axis_ratios_json: dict[str, float] | None = None


class FakeScoringClient:
    def __init__(self) -> None:
        self.requested_axes: list[str] = []

    def score_axis_responses(self, *, axis, responses, config):
        self.requested_axes.append(axis)
        if axis == 'IE':
            return {
                'scores': [
                    {
                        'response_id': responses[0].id,
                        'score': -0.7,
                        'coding_status': 'coded',
                        'reason': 'alone time preference',
                    },
                    {
                        'response_id': responses[1].id,
                        'score': None,
                        'coding_status': 'insufficient_context',
                        'reason': 'too short',
                    },
                ],
            }
        return {
            'scores': [
                {
                    'response_id': responses[0].id,
                    'score': 0.4,
                    'coding_status': 'coded',
                    'reason': 'structured decision evidence',
                },
            ],
        }


class FakeReportClient:
    def generate_sections(self, *, monthly_result, axis_results, evidence_items):
        evidence_axes = ','.join(item.axis for item in evidence_items) or 'none'
        return (
            ReportSection(
                title='result',
                content=f'{monthly_result.estimated_mbti_type} from {evidence_axes}',
            ),
            ReportSection(
                title='evidence',
                content=f'evidence_count={len(evidence_items)}',
            ),
            ReportSection(
                title='type',
                content=f'{monthly_result.estimated_mbti_type} description',
            ),
        )


class MonthlyQuestionBatchTests(TestCase):
    def test_resolve_month_period_from_explicit_period_key(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )

        self.assertEqual(period_key, '2026-06')
        self.assertEqual(period_start.isoformat(), '2026-06-01T00:00:00+09:00')
        self.assertEqual(period_end.isoformat(), '2026-07-01T00:00:00+09:00')

    def test_resolve_month_period_rejects_invalid_period_key(self):
        with self.assertRaises(ValueError):
            resolve_month_period(period_key='2026-13')

    def test_build_monthly_question_batch_groups_responses_by_axis(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        responses = [
            FakeQuestionResponse(2, 'q2', 'a2', 'TF', datetime(2026, 6, 3, 9, 0)),
            FakeQuestionResponse(1, 'q1', 'a1', 'IE', datetime(2026, 6, 2, 9, 0)),
            FakeQuestionResponse(3, 'q3', 'a3', 'XX', datetime(2026, 6, 4, 9, 0)),
        ]

        batch = build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=responses,
        )

        self.assertEqual(batch.user_id, 7)
        self.assertEqual(batch.period_key, '2026-06')
        self.assertEqual(batch.axis_counts, {'IE': 1, 'SN': 0, 'TF': 1, 'JP': 0})
        self.assertEqual(batch.total_count, 2)
        self.assertEqual(tuple(batch.axis_responses.keys()), MBTI_AXES)
        self.assertEqual(batch.axis_responses['IE'][0].id, 1)
        self.assertEqual(batch.axis_responses['TF'][0].id, 2)


class PrimaryOpeningTests(TestCase):
    def test_evaluate_primary_opening_splits_scoring_and_baseline_axes(self):
        result = evaluate_primary_opening(
            {'IE': 5, 'SN': 4, 'TF': 6, 'JP': 0},
        )

        self.assertEqual(result.scoring_axes, ('IE', 'TF'))
        self.assertEqual(result.baseline_axes, ('SN', 'JP'))
        self.assertTrue(result.axis_results['IE'].primary_open)
        self.assertEqual(result.axis_results['IE'].next_step, 'score_responses')
        self.assertFalse(result.axis_results['SN'].primary_open)
        self.assertEqual(result.axis_results['SN'].data_status, 'primary_closed')


class SecondaryOpeningTests(TestCase):
    def test_evaluate_secondary_opening_uses_only_coded_non_null_scores(self):
        primary = evaluate_primary_opening(
            {'IE': 5, 'SN': 4, 'TF': 6, 'JP': 0},
        )
        scores = [
            FakeResponseScore(axis='IE', score=-0.5, coding_status='coded'),
            FakeResponseScore(axis='IE', score=None, coding_status='insufficient_context'),
            FakeResponseScore(axis='TF', score=None, coding_status='insufficient_context'),
            FakeResponseScore(axis='SN', score=1.0, coding_status='coded'),
        ]

        result = evaluate_secondary_opening(primary, scores)

        self.assertEqual(result.graph_score_axes, ('IE',))
        self.assertEqual(result.baseline_axes, ('SN', 'TF', 'JP'))
        self.assertTrue(result.axis_results['IE'].secondary_open)
        self.assertEqual(result.axis_results['IE'].next_step, 'calculate_graph_score')
        self.assertFalse(result.axis_results['TF'].secondary_open)
        self.assertEqual(result.axis_results['TF'].data_status, 'secondary_closed')
        self.assertEqual(result.axis_results['SN'].data_status, 'primary_closed')


class DashboardPayloadTests(TestCase):
    def test_preparing_payload_does_not_fabricate_monthly_results(self):
        payload = build_frontend_preparing_payload(user_id=7, period_key='2026-06')

        self.assertEqual(payload['status'], 'preparing')
        self.assertFalse(payload['has_monthly_analysis'])
        self.assertEqual(payload['mbti_view_mode'], 'onboardingNext')
        self.assertEqual(payload['mbti_data']['current']['type'], '----')
        self.assertEqual(payload['mbti_data']['current']['axes'], [])
        self.assertEqual(payload['mbti_data']['report'], [])


class ResponseScoringTests(TestCase):
    def test_score_primary_open_axes_scores_only_axes_that_passed_primary_opening(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        rows = []
        response_id = 1
        for axis, count in {'IE': 5, 'SN': 4, 'TF': 5, 'JP': 0}.items():
            for index in range(count):
                rows.append(
                    FakeQuestionResponse(
                        response_id,
                        f'{axis} q{index}',
                        f'{axis} a{index}',
                        axis,
                        datetime(2026, 6, index + 1, 9, 0),
                    )
                )
                response_id += 1
        batch = build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=rows,
        )
        primary = evaluate_primary_opening(batch.axis_counts)
        client = FakeScoringClient()

        scores = score_primary_open_axes(
            batch=batch,
            primary_opening=primary,
            client=client,
        )

        self.assertEqual(client.requested_axes, ['IE', 'TF'])
        self.assertEqual(tuple(score.axis for score in scores), ('IE', 'IE', 'TF'))
        self.assertIsInstance(scores[0], MbtiResponseScore)
        self.assertEqual(scores[0].score, -0.7)
        self.assertIsNone(scores[1].score)
        self.assertEqual(scores[1].coding_status, 'insufficient_context')

    def test_parse_axis_scoring_payload_clamps_coded_scores_and_ignores_unknown_ids(self):
        response = FakeQuestionResponse(
            1,
            'q',
            'a',
            'IE',
            datetime(2026, 6, 1, 9, 0),
        )

        scores = parse_axis_scoring_payload(
            axis='IE',
            payload={
                'scores': [
                    {
                        'response_id': 1,
                        'score': 1.5,
                        'coding_status': 'coded',
                        'reason': 'strong evidence',
                    },
                    {
                        'response_id': 999,
                        'score': -0.2,
                        'coding_status': 'coded',
                        'reason': 'not from source batch',
                    },
                ],
            },
            source_responses=(response,),
            model='gpt-5.4-mini',
        )

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].score, 1.0)

    def test_build_axis_scoring_input_contains_axis_and_response_payload(self):
        response = FakeQuestionResponse(
            1,
            'When do you feel energized?',
            'When discussing ideas with friends.',
            'IE',
            datetime(2026, 6, 1, 9, 0),
        )

        payload_text = build_axis_scoring_input(axis='IE', responses=(response,))

        self.assertIn('"axis": "IE"', payload_text)
        self.assertIn('"response_id": 1', payload_text)
        self.assertIn('When discussing ideas with friends.', payload_text)

    def test_build_axis_scoring_system_prompt_controls_json_scoring_rules(self):
        prompt = build_axis_scoring_system_prompt()

        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())
        self.assertIn('trailing comma', prompt)
        self.assertIn('"scores"', prompt)

    def test_failed_scoring_payload_marks_every_source_response_failed(self):
        responses = (
            FakeQuestionResponse(
                1,
                'q1',
                'a1',
                'IE',
                datetime(2026, 6, 1, 9, 0),
            ),
            FakeQuestionResponse(
                2,
                'q2',
                'a2',
                'IE',
                datetime(2026, 6, 2, 9, 0),
            ),
        )

        payload = _build_failed_scoring_payload(
            responses=responses,
            reason='invalid JSON',
        )
        scores = parse_axis_scoring_payload(
            axis='IE',
            payload=payload,
            source_responses=responses,
            model='gpt-5.4-mini',
        )

        self.assertEqual(len(scores), 2)
        self.assertEqual(tuple(score.coding_status for score in scores), ('failed', 'failed'))
        self.assertEqual(tuple(score.score for score in scores), (None, None))


class LlmConfigTests(TestCase):
    def test_build_scoring_llm_config_uses_requested_default_model(self):
        config = build_scoring_llm_config()

        self.assertEqual(config.provider, 'openai')
        self.assertEqual(config.model, DEFAULT_OPENAI_SCORING_MODEL)
        self.assertEqual(config.model, 'gpt-5.4-mini')
        self.assertEqual(config.temperature, 0.0)


class BaselineSourceTests(TestCase):
    def test_extract_axis_letters_from_mbti_type_validates_axis_letters(self):
        self.assertEqual(
            extract_axis_letters_from_mbti_type('intp'),
            {'IE': 'I', 'SN': 'N', 'TF': 'T', 'JP': 'P'},
        )
        self.assertEqual(extract_axis_letters_from_mbti_type('XXXX'), {})
        self.assertEqual(extract_axis_letters_from_mbti_type(None), {})

    def test_build_user_baseline_snapshot_prefers_previous_month_result(self):
        snapshot = build_user_baseline_snapshot(
            user_id=7,
            previous_monthly_result=FakeMonthlyResultRecord(
                user_id=7,
                period_key='2026-05',
                estimated_mbti_type='ENTJ',
            ),
            onboarding_profile=FakeOnboardingProfile(
                user_id=7,
                mbti_type='INFP',
            ),
        )

        self.assertEqual(snapshot.user_id, 7)
        self.assertEqual(
            snapshot.previous_axis_letters,
            {'IE': 'E', 'SN': 'N', 'TF': 'T', 'JP': 'J'},
        )
        self.assertEqual(
            snapshot.previous_axis_period_keys,
            {'IE': '2026-05', 'SN': '2026-05', 'TF': '2026-05', 'JP': '2026-05'},
        )
        self.assertEqual(snapshot.previous_axis_avgs, {})
        self.assertEqual(snapshot.previous_axis_ratios, {})
        self.assertEqual(snapshot.previous_period_key, '2026-05')
        self.assertEqual(snapshot.previous_estimated_mbti_type, 'ENTJ')
        self.assertEqual(snapshot.onboarding_mbti_type, 'INFP')

    def test_build_user_baseline_snapshot_can_fill_from_axis_results(self):
        snapshot = build_user_baseline_snapshot(
            user_id=7,
            previous_axis_results=(
                FakeAxisResultRecord(7, '2026-04', 'SN', 'S', 0.4, {'N': 0.3, 'S': 0.7}),
                FakeAxisResultRecord(7, '2026-03', 'JP', 'P', -0.2, {'P': 0.6, 'J': 0.4}),
            ),
            onboarding_profile=FakeOnboardingProfile(
                user_id=7,
                mbti_type='INFP',
            ),
        )

        self.assertEqual(snapshot.previous_axis_letters, {'SN': 'S', 'JP': 'P'})
        self.assertEqual(
            snapshot.previous_axis_period_keys,
            {'SN': '2026-04', 'JP': '2026-03'},
        )
        self.assertEqual(snapshot.previous_axis_avgs, {'SN': 0.4, 'JP': -0.2})
        self.assertEqual(
            snapshot.previous_axis_ratios,
            {'SN': {'N': 0.3, 'S': 0.7}, 'JP': {'P': 0.6, 'J': 0.4}},
        )
        self.assertEqual(snapshot.previous_estimated_mbti_type, 'INFP')

    def test_build_user_baseline_snapshot_uses_onboarding_when_no_previous_month_exists(self):
        snapshot = build_user_baseline_snapshot(
            user_id=7,
            onboarding_profile=FakeOnboardingProfile(
                user_id=7,
                mbti_type='INFP',
            ),
        )

        self.assertEqual(snapshot.previous_axis_letters, {})
        self.assertIsNone(snapshot.previous_period_key)
        self.assertEqual(snapshot.previous_estimated_mbti_type, 'INFP')
        self.assertEqual(snapshot.onboarding_mbti_type, 'INFP')

    def test_build_user_baseline_snapshot_rejects_other_user_rows(self):
        with self.assertRaises(ValueError):
            build_user_baseline_snapshot(
                user_id=7,
                previous_monthly_result=FakeMonthlyResultRecord(
                    user_id=99,
                    period_key='2026-05',
                    estimated_mbti_type='ENTJ',
                ),
            )
        with self.assertRaises(ValueError):
            build_user_baseline_snapshot(
                user_id=7,
                previous_axis_results=(
                    FakeAxisResultRecord(99, '2026-04', 'SN', 'S'),
                ),
            )


class GraphScoreTests(TestCase):
    def test_calculate_axis_graph_score_selects_higher_display_direction(self):
        result = calculate_axis_graph_score(
            axis='TF',
            scores=(1.0, 0.5, -0.5),
        )

        self.assertAlmostEqual(result.axis_avg, 1.0 / 3.0)
        self.assertAlmostEqual(result.axis_ratios['T'], 2.0 / 3.0)
        self.assertAlmostEqual(result.axis_ratios['F'], 1.0 / 3.0)
        self.assertEqual(result.selected_direction, 'positive')
        self.assertEqual(result.selected_letter, 'T')
        self.assertEqual(result.next_step, 'decide_current_month_preference')
        self.assertEqual(result.data_status, 'current_month')

    def test_calculate_axis_graph_score_sends_tie_to_baseline(self):
        result = calculate_axis_graph_score(
            axis='IE',
            scores=(-1.0, 1.0),
        )

        self.assertEqual(result.axis_avg, 0.0)
        self.assertEqual(result.axis_ratios, {'I': 0.5, 'E': 0.5})
        self.assertIsNone(result.selected_letter)
        self.assertEqual(result.next_step, 'apply_baseline_letter')
        self.assertEqual(result.data_status, 'tie_carried')

    def test_calculate_monthly_graph_scores_uses_only_secondary_open_axes(self):
        primary = evaluate_primary_opening(
            {'IE': 5, 'SN': 5, 'TF': 5, 'JP': 4},
        )
        scores = [
            FakeResponseScore(axis='IE', score=-1.0, coding_status='coded'),
            FakeResponseScore(axis='IE', score=1.0, coding_status='coded'),
            FakeResponseScore(axis='SN', score=-0.5, coding_status='coded'),
            FakeResponseScore(axis='TF', score=1.0, coding_status='coded'),
            FakeResponseScore(axis='TF', score=0.5, coding_status='coded'),
            FakeResponseScore(axis='TF', score=None, coding_status='insufficient_context'),
            FakeResponseScore(axis='JP', score=1.0, coding_status='coded'),
        ]
        secondary = evaluate_secondary_opening(primary, scores)

        result = calculate_monthly_graph_scores(
            secondary_opening=secondary,
            response_scores=scores,
        )

        self.assertEqual(result.selected_axes, ('SN', 'TF'))
        self.assertEqual(result.tie_axes, ('IE',))
        self.assertEqual(result.baseline_axes, ('JP', 'IE'))
        self.assertEqual(result.axis_results['IE'].data_status, 'tie_carried')
        self.assertEqual(result.axis_results['SN'].selected_letter, 'N')
        self.assertEqual(result.axis_results['TF'].selected_letter, 'T')
        self.assertEqual(result.axis_results['JP'].data_status, 'primary_closed')


class MonthlyResultAndReportTests(TestCase):
    def _build_batch(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        rows = [
            FakeQuestionResponse(1, 'IE q1', '혼자 쉬는 편입니다.', 'IE', datetime(2026, 6, 1, 9, 0)),
            FakeQuestionResponse(2, 'IE q2', '큰 모임도 좋습니다.', 'IE', datetime(2026, 6, 2, 9, 0)),
            FakeQuestionResponse(3, 'SN q1', '구체적인 사례를 봅니다.', 'SN', datetime(2026, 6, 3, 9, 0)),
            FakeQuestionResponse(4, 'TF q1', '근거를 먼저 봅니다.', 'TF', datetime(2026, 6, 4, 9, 0)),
            FakeQuestionResponse(5, 'JP q1', '계획을 세웁니다.', 'JP', datetime(2026, 6, 5, 9, 0)),
            FakeQuestionResponse(6, 'TF q2', '객관적인 기준이 필요합니다.', 'TF', datetime(2026, 6, 6, 9, 0)),
            FakeQuestionResponse(7, 'TF q3', '먼저 따져보는 편입니다.', 'TF', datetime(2026, 6, 7, 9, 0)),
            FakeQuestionResponse(8, 'TF q4', '근거가 있으면 납득됩니다.', 'TF', datetime(2026, 6, 8, 9, 0)),
            FakeQuestionResponse(9, 'TF q5', '논리적으로 정리합니다.', 'TF', datetime(2026, 6, 9, 9, 0)),
        ]
        return build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=rows,
        )

    def test_finalize_combine_report_and_payload_use_pipeline_results(self):
        batch = self._build_batch()
        primary = evaluate_primary_opening(
            {'IE': 5, 'SN': 5, 'TF': 5, 'JP': 4},
        )
        response_scores = [
            FakeScoredResponse(1, 'IE', -1.0, 'coded', 'I evidence'),
            FakeScoredResponse(2, 'IE', 1.0, 'coded', 'E evidence'),
            FakeScoredResponse(3, 'SN', -0.5, 'coded', 'N evidence'),
            FakeScoredResponse(4, 'TF', 1.0, 'coded', 'T evidence'),
            FakeScoredResponse(5, 'JP', 1.0, 'coded', 'ignored JP evidence'),
        ]
        secondary = evaluate_secondary_opening(primary, response_scores)
        graph = calculate_monthly_graph_scores(
            secondary_opening=secondary,
            response_scores=response_scores,
        )
        previous = build_previous_monthly_baselines(
            previous_axis_letters={'IE': 'I', 'SN': 'N', 'TF': 'F'},
            previous_period_key='2026-05',
            previous_axis_avgs={'IE': -0.5, 'SN': -0.2, 'TF': -0.6},
            previous_axis_ratios={
                'IE': {'I': 0.75, 'E': 0.25},
                'SN': {'N': 0.6, 'S': 0.4},
                'TF': {'F': 0.8, 'T': 0.2},
            },
        )

        final_axes = finalize_monthly_axis_preferences(
            batch=batch,
            graph_result=graph,
            previous_baselines=previous,
            onboarding_mbti_type='INFP',
        )
        monthly = combine_monthly_mbti(
            user_id=batch.user_id,
            period_key=batch.period_key,
            axis_results=final_axes,
            previous_estimated_mbti_type='INFP',
        )
        evidence = select_report_evidence(
            batch=batch,
            monthly_result=monthly,
            response_scores=response_scores,
        )
        report = generate_monthly_report(
            monthly_result=monthly,
            axis_results=final_axes,
            evidence_items=evidence,
            report_client=FakeReportClient(),
        )
        payload = build_mypage_payload(
            monthly_result=monthly,
            report=report,
        )

        self.assertEqual(final_axes['IE'].data_status, 'carried_from_previous')
        self.assertEqual(final_axes['SN'].selected_letter, 'N')
        self.assertEqual(final_axes['SN'].data_status, 'current_month')
        self.assertEqual(final_axes['TF'].selected_letter, 'T')
        self.assertEqual(final_axes['JP'].selected_letter, 'P')
        self.assertEqual(final_axes['JP'].data_status, 'carried_from_onboarding')
        self.assertEqual(monthly.estimated_mbti_type, 'INTP')
        self.assertEqual(monthly.changed_axes, ('TF',))
        self.assertEqual(tuple(item.axis for item in evidence), ('TF', 'SN'))
        self.assertEqual(tuple(item.role for item in evidence), ('score_change_driver', 'current_direction_evidence'))
        self.assertEqual(evidence[0].score_delta_contribution, 1.6)
        self.assertEqual(evidence[0].impact_score, 1.6)
        self.assertEqual(evidence[0].answer_text, '근거를 먼저 봅니다.')
        self.assertEqual(evidence[0].evidence_span, '근거를 먼저 봅니다.')
        self.assertEqual(payload['estimated_mbti_type'], 'INTP')
        self.assertEqual(len(payload['axis_results']), 4)
        self.assertEqual(payload['axis_results'][2]['previous_axis_avg'], -0.6)
        self.assertEqual(payload['report_sections'][2]['content'], 'INTP description')

        context = _build_report_context(
            monthly_result=monthly,
            axis_results=final_axes,
            evidence_items=evidence,
        )
        self.assertEqual(context['previous_or_baseline_mbti_type'], 'INFP')
        self.assertEqual(context['estimated_mbti_type'], 'INTP')
        self.assertEqual(context['changed_axes'], ['TF'])
        self.assertEqual(context['current_month_preference_changed_axes'], ['TF'])
        self.assertEqual(
            context['changed_axis_display_changes'],
            [
                {
                    'axis': 'TF',
                    'previous_letter': 'F',
                    'selected_letter': 'T',
                    'previous_display_score': 80,
                    'current_display_score': 100,
                    'display_score_delta': 20,
                }
            ],
        )
        self.assertIn('SN', context['unchanged_axes'])
        self.assertIn('IE', context['carried_axes'])
        self.assertIn('JP', context['carried_axes'])
        self.assertIn('SN', context['current_month_updated_axes'])
        self.assertIn('TF', context['current_month_updated_axes'])
        self.assertEqual(context['evidence_items'][0]['role'], 'score_change_driver')
        self.assertEqual(context['evidence_items'][0]['answer_text'], '근거를 먼저 봅니다.')
        self.assertIn('impact_score', context['evidence_items'][0])
        self.assertIn('score_delta_contribution', context['evidence_items'][0])
        tf_context = [
            row for row in context['axis_results']
            if row['axis'] == 'TF'
        ][0]
        self.assertEqual(tf_context['score_delta_from_previous_axis_avg'], 1.6)
        self.assertEqual(tf_context['absolute_score_delta'], 1.6)

    def test_onboarding_only_does_not_open_monthly_analysis(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        batch = build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=[],
        )

        result = run_monthly_mbti_pipeline(
            batch=batch,
            onboarding_mbti_type='INFP',
            scoring_client=FakeScoringClient(),
            report_client=FakeReportClient(),
        )

        self.assertEqual(result.primary_opening.scoring_axes, ())
        self.assertEqual(result.monthly_result.status, 'insufficient_data')
        self.assertIsNone(result.monthly_result.estimated_mbti_type)

    def test_under_primary_threshold_axes_stay_in_preparing_state(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        rows = [
            FakeQuestionResponse(1, 'IE q1', 'a', 'IE', datetime(2026, 6, 1, 9, 0)),
            FakeQuestionResponse(2, 'SN q1', 'a', 'SN', datetime(2026, 6, 2, 9, 0)),
            FakeQuestionResponse(3, 'TF q1', 'a', 'TF', datetime(2026, 6, 3, 9, 0)),
            FakeQuestionResponse(4, 'JP q1', 'a', 'JP', datetime(2026, 6, 4, 9, 0)),
        ]
        batch = build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=rows,
        )

        result = run_monthly_mbti_pipeline(
            batch=batch,
            onboarding_mbti_type='INFP',
            scoring_client=FakeScoringClient(),
            report_client=FakeReportClient(),
        )

        self.assertEqual(result.primary_opening.scoring_axes, ())
        self.assertEqual(result.monthly_result.status, 'insufficient_data')
        self.assertIsNone(result.monthly_result.estimated_mbti_type)

    def test_one_primary_open_axis_opens_monthly_analysis_with_baseline_axes(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        rows = [
            FakeQuestionResponse(
                index,
                f'IE q{index}',
                '혼자 쉬는 편입니다.',
                'IE',
                datetime(2026, 6, index, 9, 0),
            )
            for index in range(1, 6)
        ]
        batch = build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=rows,
        )

        result = run_monthly_mbti_pipeline(
            batch=batch,
            onboarding_mbti_type='ENFP',
            scoring_client=FakeScoringClient(),
            report_client=FakeReportClient(),
        )

        self.assertEqual(result.primary_opening.scoring_axes, ('IE',))
        self.assertEqual(result.monthly_result.status, 'complete')
        self.assertEqual(result.monthly_result.estimated_mbti_type, 'INFP')
        self.assertEqual(result.final_axis_results['IE'].data_status, 'current_month')
        self.assertEqual(result.final_axis_results['SN'].data_status, 'carried_from_onboarding')
        self.assertEqual(result.final_axis_results['TF'].data_status, 'carried_from_onboarding')
        self.assertEqual(result.final_axis_results['JP'].data_status, 'carried_from_onboarding')

    def test_run_monthly_mbti_pipeline_connects_scoring_to_report_payload(self):
        period_key, period_start, period_end = resolve_month_period(
            period_key='2026-06',
        )
        rows = []
        response_id = 1
        for axis, count in {'IE': 5, 'SN': 5, 'TF': 5, 'JP': 4}.items():
            for index in range(count):
                rows.append(
                    FakeQuestionResponse(
                        response_id,
                        f'{axis} q{index}',
                        f'{axis} a{index}',
                        axis,
                        datetime(2026, 6, index + 1, 9, 0),
                    )
                )
                response_id += 1
        batch = build_monthly_question_batch(
            user_id=7,
            period_key=period_key,
            period_start=period_start,
            period_end=period_end,
            responses=rows,
        )
        scoring_client = FakeScoringClient()

        result = run_monthly_mbti_pipeline(
            batch=batch,
            previous_axis_letters={'IE': 'I', 'SN': 'N', 'TF': 'F'},
            previous_period_key='2026-05',
            previous_estimated_mbti_type='INFP',
            onboarding_mbti_type='INFP',
            scoring_client=scoring_client,
            report_client=FakeReportClient(),
        )

        self.assertEqual(scoring_client.requested_axes, ['IE', 'SN', 'TF'])
        self.assertEqual(result.primary_opening.scoring_axes, ('IE', 'SN', 'TF'))
        self.assertEqual(result.secondary_opening.graph_score_axes, ('IE', 'SN', 'TF'))
        self.assertEqual(result.graph_result.baseline_axes, ('JP',))
        self.assertEqual(result.monthly_result.estimated_mbti_type, 'ISTP')
        self.assertEqual(tuple(item.axis for item in result.evidence_items), ('SN', 'TF', 'IE'))
        self.assertEqual(result.mypage_payload['estimated_mbti_type'], 'ISTP')
        self.assertEqual(len(result.mypage_payload['report_sections']), 3)

    def test_run_monthly_mbti_pipeline_uses_same_user_baseline_snapshot(self):
        batch = self._build_batch()
        snapshot = UserBaselineSnapshot(
            user_id=7,
            previous_axis_letters={'IE': 'E', 'SN': 'S', 'TF': 'T'},
            previous_axis_period_keys={'IE': '2026-05', 'SN': '2026-04', 'TF': '2026-05'},
            previous_axis_avgs={'IE': 0.2, 'SN': 0.4, 'TF': 0.6},
            previous_axis_ratios={
                'IE': {'I': 0.4, 'E': 0.6},
                'SN': {'N': 0.3, 'S': 0.7},
                'TF': {'F': 0.2, 'T': 0.8},
            },
            previous_period_key='2026-05',
            previous_estimated_mbti_type='ESTJ',
            onboarding_mbti_type='INFP',
        )

        result = run_monthly_mbti_pipeline(
            batch=batch,
            baseline_snapshot=snapshot,
            scoring_client=FakeScoringClient(),
            report_client=FakeReportClient(),
        )

        self.assertEqual(result.monthly_result.user_id, 7)
        self.assertEqual(result.monthly_result.estimated_mbti_type, 'ESTP')
        self.assertEqual(result.final_axis_results['IE'].baseline_source, 'latest_monthly_result')
        self.assertEqual(result.final_axis_results['IE'].axis_avg, 0.2)
        self.assertEqual(result.final_axis_results['IE'].axis_ratios, {'I': 0.4, 'E': 0.6})
        self.assertEqual(result.final_axis_results['SN'].baseline_period_key, '2026-04')
        self.assertEqual(result.final_axis_results['SN'].axis_avg, 0.4)
        self.assertEqual(result.final_axis_results['SN'].axis_ratios, {'N': 0.3, 'S': 0.7})
        self.assertEqual(result.final_axis_results['JP'].baseline_source, 'onboarding')
        self.assertIsNone(result.final_axis_results['JP'].axis_avg)
        self.assertEqual(result.final_axis_results['JP'].axis_ratios, {})

    def test_run_monthly_mbti_pipeline_rejects_other_user_baseline_snapshot(self):
        batch = self._build_batch()
        snapshot = UserBaselineSnapshot(
            user_id=99,
            previous_axis_letters={'IE': 'E'},
            previous_axis_period_keys={'IE': '2026-05'},
            previous_axis_avgs={'IE': 0.4},
            previous_axis_ratios={'IE': {'I': 0.3, 'E': 0.7}},
            previous_period_key='2026-05',
            previous_estimated_mbti_type='ENTJ',
            onboarding_mbti_type='ENTJ',
        )

        with self.assertRaises(ValueError):
            run_monthly_mbti_pipeline(
                batch=batch,
                baseline_snapshot=snapshot,
                scoring_client=FakeScoringClient(),
                report_client=FakeReportClient(),
            )

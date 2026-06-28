from dataclasses import dataclass
from datetime import datetime
from unittest import TestCase

from mbti.services.opening_rules import (
    evaluate_primary_opening,
    evaluate_secondary_opening,
)
from mbti.services.llm_config import (
    DEFAULT_OPENAI_SCORING_MODEL,
    build_scoring_llm_config,
)
from mbti.services.monthly_questions import (
    MBTI_AXES,
    build_monthly_question_batch,
    resolve_month_period,
)
from mbti.services.response_scoring import (
    MbtiResponseScore,
    build_axis_scoring_input,
    build_axis_scoring_system_prompt,
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

        self.assertIn('Return JSON only', prompt)
        self.assertIn('coding_status', prompt)
        self.assertIn('insufficient_context', prompt)
        self.assertIn('Do not infer traits from stereotypes', prompt)


class LlmConfigTests(TestCase):
    def test_build_scoring_llm_config_uses_requested_default_model(self):
        config = build_scoring_llm_config()

        self.assertEqual(config.provider, 'openai')
        self.assertEqual(config.model, DEFAULT_OPENAI_SCORING_MODEL)
        self.assertEqual(config.model, 'gpt-5.4-mini')
        self.assertEqual(config.temperature, 0.0)

from types import SimpleNamespace

from django.test import TestCase

from mbti.models import MbtiMonthlyResultRecord
from mbti.services.monthly_results import FinalAxisPreference, MonthlyMbtiResult
from mbti.services.persistence import save_monthly_pipeline_result
from mbti.services.reports import MonthlyReport, ReportSection


class MonthlyResultPersistenceTests(TestCase):
    def test_previous_period_key_is_persisted_for_dashboard_comparison(self):
        axes = {
            axis: FinalAxisPreference(
                axis=axis,
                qna_count=5,
                scored_count=1,
                axis_avg=-0.5,
                axis_ratios={letters[0]: 0.75, letters[1]: 0.25},
                previous_axis_avg=-0.25,
                previous_axis_ratios={letters[0]: 0.625, letters[1]: 0.375},
                selected_letter=letters[0],
                data_status='current_month',
                calculation_status='calculated',
                baseline_letter=letters[0],
                baseline_source='latest_monthly_result',
                baseline_period_key='2026-05',
            )
            for axis, letters in {
                'IE': ('I', 'E'),
                'SN': ('N', 'S'),
                'TF': ('F', 'T'),
                'JP': ('P', 'J'),
            }.items()
        }
        monthly = MonthlyMbtiResult(
            user_id=777,
            period_key='2026-06',
            previous_estimated_mbti_type='INFP',
            estimated_mbti_type='INFP',
            changed_axes=(),
            status='complete',
            axis_results=axes,
            previous_period_key='2026-05',
        )
        result = SimpleNamespace(
            response_scores=(),
            monthly_result=monthly,
            final_axis_results=axes,
            primary_opening=SimpleNamespace(scoring_axes=tuple(axes)),
            secondary_opening=SimpleNamespace(graph_score_axes=tuple(axes)),
            report=MonthlyReport(
                report_sections=(ReportSection(title='요약', content='유지됨'),),
                evidence_items=(),
            ),
        )

        save_monthly_pipeline_result(result)

        record = MbtiMonthlyResultRecord.objects.get(user_id=777, period_key='2026-06')
        self.assertEqual(record.previous_estimated_mbti_type, 'INFP')
        self.assertEqual(record.previous_period_key, '2026-05')


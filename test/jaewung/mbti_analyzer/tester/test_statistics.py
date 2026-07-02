from datetime import datetime

from test.jaewung.mbti_analyzer.analyzer.schemas import MbtiEvidenceRecord
from test.jaewung.mbti_analyzer.analyzer.statistics import MbtiStatisticsEngine


def test_dedupe_same_message_axis_pole_keyword_counts_once():
    engine = MbtiStatisticsEngine()

    records = [
        MbtiEvidenceRecord(
            message_id="u1",
            user_id=1,
            period_key="2026-06",
            source_created_at=datetime(2026, 6, 1, 10, 0, 0),
            axis="IE",
            pole="I",
            normalized_keyword="혼자 회복",
            evidence_span="혼자 조용히 있어야 회복돼요",
            context_summary="사회적 교류 이후 혼자 회복하려는 맥락",
            coding_reason="에너지 회복 방식이 I 방향",
            coding_status="coded",
        ),
        MbtiEvidenceRecord(
            message_id="u1",
            user_id=1,
            period_key="2026-06",
            source_created_at=datetime(2026, 6, 1, 10, 0, 0),
            axis="IE",
            pole="I",
            normalized_keyword="혼자 회복",
            evidence_span="혼자 조용히 있어야 회복돼요",
            context_summary="사회적 교류 이후 혼자 회복하려는 맥락",
            coding_reason="에너지 회복 방식이 I 방향",
            coding_status="coded",
        ),
    ]

    result = engine.aggregate(
        user_id=1,
        period_type="monthly",
        period_key="2026-06",
        source_message_count=1,
        evidence_records=records,
    )

    assert result.axis_scores["IE"].counts["I"] == 1
    assert result.axis_scores["IE"].counts["E"] == 0
    assert result.axis_scores["IE"].ratios["I"] == 100
    assert result.axis_scores["IE"].selected == "I"


def test_estimated_type_is_built_from_selected_axis_letters():
    engine = MbtiStatisticsEngine()

    records = [
        MbtiEvidenceRecord(
            message_id="u1",
            user_id=1,
            period_key="2026-06",
            source_created_at=datetime(2026, 6, 1),
            axis="IE",
            pole="I",
            normalized_keyword="혼자 회복",
            evidence_span="혼자 회복",
            context_summary="",
            coding_reason="",
            coding_status="coded",
        ),
        MbtiEvidenceRecord(
            message_id="u2",
            user_id=1,
            period_key="2026-06",
            source_created_at=datetime(2026, 6, 2),
            axis="SN",
            pole="N",
            normalized_keyword="가능성 탐색",
            evidence_span="가능성을 열어두고 싶다",
            context_summary="",
            coding_reason="",
            coding_status="coded",
        ),
        MbtiEvidenceRecord(
            message_id="u3",
            user_id=1,
            period_key="2026-06",
            source_created_at=datetime(2026, 6, 3),
            axis="TF",
            pole="T",
            normalized_keyword="원인 분석",
            evidence_span="원인을 먼저 정리하자",
            context_summary="",
            coding_reason="",
            coding_status="coded",
        ),
        MbtiEvidenceRecord(
            message_id="u4",
            user_id=1,
            period_key="2026-06",
            source_created_at=datetime(2026, 6, 4),
            axis="JP",
            pole="P",
            normalized_keyword="선택지 유지",
            evidence_span="선택지를 열어두자",
            context_summary="",
            coding_reason="",
            coding_status="coded",
        ),
    ]

    result = engine.aggregate(
        user_id=1,
        period_type="monthly",
        period_key="2026-06",
        source_message_count=4,
        evidence_records=records,
    )

    assert result.estimated_type == "INTP"
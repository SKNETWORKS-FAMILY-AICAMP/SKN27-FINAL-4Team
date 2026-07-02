from datetime import datetime

from test.jaewung.mbti_analyzer.analyzer.schemas import (
    AxisEvidence,
    ConversationMessage,
    LocalContextWindow,
    MessageCodingResult,
)
from test.jaewung.mbti_analyzer.analyzer.service import MbtiAnalysisService


class FakeMbtiCoder:
    def code(self, window: LocalContextWindow) -> MessageCodingResult:
        if "혼자 조용히" in window.target_user_text:
            return MessageCodingResult(
                message_id=window.target_message_id,
                context_summary="사회적 교류 이후 혼자 조용히 회복하려는 맥락",
                coding_status="coded",
                axis_evidence=[
                    AxisEvidence(
                        axis="IE",
                        pole="I",
                        normalized_keyword="혼자 회복",
                        evidence_span="혼자 조용히 있어야 회복돼요",
                        coding_reason="사회적 상호작용 이후 에너지 회복 방식이 I 방향",
                    )
                ],
            )

        if "가능성" in window.target_user_text:
            return MessageCodingResult(
                message_id=window.target_message_id,
                context_summary="미래 가능성과 선택지를 탐색하는 맥락",
                coding_status="coded",
                axis_evidence=[
                    AxisEvidence(
                        axis="SN",
                        pole="N",
                        normalized_keyword="가능성 탐색",
                        evidence_span="가능성을 더 보고 싶어요",
                        coding_reason="구체 사실보다 가능성 탐색에 가깝다",
                    )
                ],
            )

        return MessageCodingResult(
            message_id=window.target_message_id,
            context_summary="성향 판단에 필요한 맥락이 부족하다.",
            coding_status="insufficient_context",
            axis_evidence=[],
        )


def test_service_outputs_evidence_period_result_and_dashboard_without_rag():
    messages = [
        ConversationMessage(
            message_id="a1",
            user_id=1,
            conversation_id="c1",
            role="assistant",
            raw_text="이번 주말에 사람들과 약속을 잡아보는 건 어때요?",
            turn_index=1,
            created_at=datetime(2026, 6, 10, 20, 10),
        ),
        ConversationMessage(
            message_id="u1",
            user_id=1,
            conversation_id="c1",
            role="user",
            raw_text="좋긴 한데 약속 끝나면 혼자 조용히 있어야 회복돼요.",
            turn_index=2,
            created_at=datetime(2026, 6, 10, 20, 11),
        ),
        ConversationMessage(
            message_id="u2",
            user_id=1,
            conversation_id="c1",
            role="user",
            raw_text="그리고 가능성을 더 보고 싶어요.",
            turn_index=3,
            created_at=datetime(2026, 6, 10, 20, 12),
        ),
    ]

    service = MbtiAnalysisService(coder=FakeMbtiCoder())

    output = service.analyze(
        user_id=1,
        period_type="monthly",
        period_key="2026-06",
        messages=messages,
    )

    assert len(output.message_mbti_evidence) == 2

    assert output.mbti_period_result.axis_scores["IE"].selected == "I"
    assert output.mbti_period_result.axis_scores["SN"].selected == "N"

    # TF, JP는 근거가 없으므로 ? 처리
    assert output.mbti_period_result.estimated_type == "IN??"

    assert output.dashboard.estimated_type == "IN??"
    assert output.dashboard.evidence_report == []
    assert output.dashboard.report_status == "skipped_rag_not_implemented"
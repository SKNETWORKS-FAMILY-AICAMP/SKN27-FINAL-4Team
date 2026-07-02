from __future__ import annotations

from test.jaewung.mbti_analyzer.analyzer.context_builder import LocalContextBuilder
from test.jaewung.mbti_analyzer.analyzer.llm_coder import MbtiCoder
from test.jaewung.mbti_analyzer.analyzer.schemas import (
    ConversationMessage,
    DashboardMbtiResponse,
    MbtiEvidenceRecord,
    MbtiPipelineOutput,
)
from test.jaewung.mbti_analyzer.analyzer.statistics import MbtiStatisticsEngine


class MbtiAnalysisService:
    def __init__(
        self,
        *,
        coder: MbtiCoder,
        context_builder: LocalContextBuilder | None = None,
        statistics_engine: MbtiStatisticsEngine | None = None,
    ) -> None:
        self.coder = coder
        self.context_builder = context_builder or LocalContextBuilder()
        self.statistics_engine = statistics_engine or MbtiStatisticsEngine()

    def analyze(
        self,
        *,
        user_id: int,
        period_type: str,
        period_key: str,
        messages: list[ConversationMessage],
    ) -> MbtiPipelineOutput:
        user_messages = [
            message for message in messages
            if message.user_id == user_id and message.role == "user"
        ]

        windows = self.context_builder.build_windows(messages)

        target_windows = [
            window for window in windows
            if window.user_id == user_id
        ]

        evidence_records: list[MbtiEvidenceRecord] = []

        for window in target_windows:
            coding_result = self.coder.code(window)

            if coding_result.coding_status == "insufficient_context":
                continue

            for evidence in coding_result.axis_evidence:
                evidence_records.append(
                    MbtiEvidenceRecord(
                        message_id=window.target_message_id,
                        user_id=window.user_id,
                        period_key=period_key,
                        source_created_at=window.source_created_at,
                        axis=evidence.axis,
                        pole=evidence.pole,
                        normalized_keyword=evidence.normalized_keyword,
                        evidence_span=evidence.evidence_span,
                        context_summary=coding_result.context_summary,
                        coding_reason=evidence.coding_reason,
                        coding_status=coding_result.coding_status,
                    )
                )

        period_result = self.statistics_engine.aggregate(
            user_id=user_id,
            period_type=period_type,
            period_key=period_key,
            source_message_count=len(user_messages),
            evidence_records=evidence_records,
        )

        dashboard = DashboardMbtiResponse(
            estimated_type=period_result.estimated_type,
            axis_scores={
                axis: {
                    **score.ratios,
                    "selected": score.selected,
                    "counts": score.counts,
                }
                for axis, score in period_result.axis_scores.items()
            },
            evidence_report=[],
            report_status="skipped_rag_not_implemented",
        )

        return MbtiPipelineOutput(
            message_mbti_evidence=evidence_records,
            mbti_period_result=period_result,
            dashboard=dashboard,
        )
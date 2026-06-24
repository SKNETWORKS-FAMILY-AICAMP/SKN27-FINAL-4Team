from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Axis = Literal["IE", "SN", "TF", "JP"]
Pole = Literal["I", "E", "S", "N", "T", "F", "J", "P"]
CodingStatus = Literal["coded", "insufficient_context"]


class ConversationMessage(BaseModel):
    message_id: str
    user_id: int
    conversation_id: str
    role: Literal["user", "assistant", "system"]
    raw_text: str
    turn_index: int
    created_at: datetime


class LocalContextWindow(BaseModel):
    target_message_id: str
    user_id: int
    conversation_id: str
    source_created_at: datetime
    target_user_text: str
    context_text: str
    context_message_ids: list[str]
    window_policy: str = "local_context_window"


class AxisEvidence(BaseModel):
    axis: Axis
    pole: Pole
    normalized_keyword: str = Field(
        description="원문 단어가 아니라 맥락 기반 정규화 키워드"
    )
    evidence_span: str = Field(
        description="성향 근거가 되는 원문 일부. 반드시 입력 context 안에 있어야 함"
    )
    coding_reason: str

    @model_validator(mode="after")
    def validate_pole_matches_axis(self) -> "AxisEvidence":
        allowed = {
            "IE": {"I", "E"},
            "SN": {"S", "N"},
            "TF": {"T", "F"},
            "JP": {"J", "P"},
        }

        if self.pole not in allowed[self.axis]:
            raise ValueError(f"{self.axis} 축에는 {self.pole} 방향을 사용할 수 없습니다.")

        return self


class MessageCodingResult(BaseModel):
    message_id: str
    context_summary: str
    coding_status: CodingStatus
    axis_evidence: list[AxisEvidence]


class MbtiEvidenceRecord(BaseModel):
    message_id: str
    user_id: int
    period_key: str
    source_created_at: datetime
    axis: Axis
    pole: Pole
    normalized_keyword: str
    evidence_span: str
    context_summary: str
    coding_reason: str
    coding_status: CodingStatus
    prompt_version: str = "mbti-coding-v1"
    taxonomy_version: str = "mbti-taxonomy-v1"


class AxisScore(BaseModel):
    selected: str | None
    ratios: dict[str, float]
    counts: dict[str, int]


class MbtiPeriodResult(BaseModel):
    user_id: int
    period_type: Literal["weekly", "monthly"]
    period_key: str
    source_message_count: int
    coded_message_count: int
    axis_scores: dict[str, AxisScore]
    estimated_type: str


class DashboardMbtiResponse(BaseModel):
    estimated_type: str
    axis_scores: dict[str, dict]
    evidence_report: list[str] = Field(
        default_factory=list,
        description="RAG 미구현 단계에서는 빈 배열"
    )
    report_status: Literal["skipped_rag_not_implemented"] = (
        "skipped_rag_not_implemented"
    )


class MbtiPipelineOutput(BaseModel):
    message_mbti_evidence: list[MbtiEvidenceRecord]
    mbti_period_result: MbtiPeriodResult
    dashboard: DashboardMbtiResponse
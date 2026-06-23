# mbti_estimator/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


AxisName = Literal["E_I", "S_N", "T_F", "J_P"]
MbtiLetter = Literal["E", "I", "S", "N", "T", "F", "J", "P", "X"]
Confidence = Literal["none", "low", "medium", "high"]


class EvidenceSource(str, Enum):
    SELF_LABEL = "self_label"
    BEHAVIOR = "behavior"
    PREFERENCE = "preference"
    REPEATED_PATTERN = "repeated_pattern"
    WEAK_CONTEXT = "weak_context"


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant", "system"]
    content: str


@dataclass(frozen=True)
class MbtiEvidence:
    """
    대화에서 추출된 MBTI 성향 단서.

    axis:
        E_I, S_N, T_F, J_P 중 하나.

    direction:
        해당 축에서 어느 쪽 성향인지.
        예: axis="E_I", direction="I"

    weight:
        0.0 ~ 1.0.
        단서의 강도.

    quote:
        근거가 된 원문 일부.

    reason:
        왜 해당 방향의 단서인지에 대한 설명.

    source:
        단서 유형.
        자기 라벨인지, 실제 행동 패턴인지 등을 구분하기 위함.
    """

    axis: AxisName
    direction: MbtiLetter
    weight: float
    quote: str
    reason: str
    source: EvidenceSource = EvidenceSource.PREFERENCE


@dataclass(frozen=True)
class AxisResult:
    axis: AxisName
    direction: MbtiLetter
    score: float
    confidence: Confidence
    total_weight: float
    positive_weight: float
    negative_weight: float
    evidence_count: int


@dataclass(frozen=True)
class MbtiAnalysisResult:
    axes: dict[AxisName, AxisResult]
    mbti: str
    confidence: Confidence
    evidence: list[MbtiEvidence] = field(default_factory=list)
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from mindreport.services.emotion_flow import (
    EmotionFlowResult,
    FLOW_SCORE_DOWNWARD,
    FLOW_SCORE_MAINTENANCE,
    FLOW_SCORE_UPWARD,
    FLOW_SCORE_VOLATILE,
    MAINTENANCE_GRAY,
    MAINTENANCE_GREEN,
    MAINTENANCE_RED,
)


@dataclass(frozen=True)
class AlternativeCandidate:
    title: str
    category: str
    priority: int
    rationale: str


@dataclass(frozen=True)
class AlternativePlanResult:
    status: str
    flow_type: str
    maintenance_type: str | None
    action_direction: str
    candidates: tuple[AlternativeCandidate, ...]
    message: str


def build_alternative_plan(
    emotion_flow: EmotionFlowResult,
) -> AlternativePlanResult:
    candidates = _candidates_for_flow(emotion_flow)
    return AlternativePlanResult(
        status='prepared' if candidates else 'empty',
        flow_type=emotion_flow.flow_type,
        maintenance_type=emotion_flow.maintenance_type,
        action_direction=emotion_flow.action_direction,
        candidates=candidates,
        message='감정 흐름 유형에 맞는 실천 대안 후보를 구성했습니다.'
        if candidates
        else '감정 흐름에 맞는 실천 대안 후보를 구성하지 못했습니다.',
    )


def _candidates_for_flow(
    emotion_flow: EmotionFlowResult,
) -> tuple[AlternativeCandidate, ...]:
    if emotion_flow.flow_type == FLOW_SCORE_UPWARD:
        return _build_candidates(
            category='recovery_maintenance',
            rationale='점수 상향 흐름은 회복 구간이 있으므로 실제 회복에 도움 된 행동을 유지하는 방향을 우선합니다.',
            titles=('회복에 도움 된 행동 유지', '편한 사람과 짧게 연결하기', '가벼운 취미 시간 이어가기'),
        )

    if emotion_flow.flow_type == FLOW_SCORE_VOLATILE:
        return _build_candidates(
            category='rhythm_stabilization',
            rationale='감정 변동성 흐름은 기복을 줄이고 하루 리듬을 안정화하는 대안을 우선합니다.',
            titles=('수면/식사 시간 고정', '짧은 감정 기록', '자극이 큰 일정 줄이기'),
        )

    if emotion_flow.flow_type == FLOW_SCORE_DOWNWARD:
        return _build_candidates(
            category='burden_reduction',
            rationale='점수 하향 흐름은 최근 부담 요인을 줄이고 회복 여지를 확보하는 대안을 우선합니다.',
            titles=('해야 할 일 나누기', '일정 조정하기', '휴식 시간 먼저 확보하기'),
        )

    if emotion_flow.flow_type == FLOW_SCORE_MAINTENANCE:
        return _maintenance_candidates(emotion_flow.maintenance_type)

    return _build_candidates(
        category='low_burden_refresh',
        rationale='명확한 흐름 세부 유형이 없으므로 부담이 낮은 환기 활동을 우선합니다.',
        titles=('짧은 산책', '가벼운 휴식', '오늘 기록 한 줄 남기기'),
    )


def _maintenance_candidates(
    maintenance_type: str | None,
) -> tuple[AlternativeCandidate, ...]:
    if maintenance_type == MAINTENANCE_GREEN:
        return _build_candidates(
            category='positive_routine_maintenance',
            rationale='초록 유지 흐름은 현재 회복 루틴이 작동하는 상태로 보고 무리한 변화보다 지속을 우선합니다.',
            titles=('현재 루틴 유지', '가벼운 운동 이어가기', '충분한 수면 유지'),
        )

    if maintenance_type == MAINTENANCE_RED:
        return _build_candidates(
            category='low_burden_recovery',
            rationale='빨강 유지 흐름은 부담이 누적된 상태 가능성이 있어 낮은 강도의 회복 행동을 우선합니다.',
            titles=('짧은 휴식', '수면 정리', '편한 사람에게 짧게 연락'),
        )

    if maintenance_type == MAINTENANCE_GRAY:
        return _build_candidates(
            category='emotional_refresh',
            rationale='회색 유지 흐름은 감정 변화가 적거나 표현이 줄어든 상태 가능성이 있어 작은 환기 활동을 우선합니다.',
            titles=('짧은 산책', '카페 방문', '가까운 곳 다녀오기', '관심 있는 게임'),
        )

    return _build_candidates(
        category='low_burden_refresh',
        rationale='유지 흐름의 세부 색상이 불명확하므로 부담이 낮은 환기 활동을 우선합니다.',
        titles=('짧은 산책', '가벼운 휴식', '오늘 기록 한 줄 남기기'),
    )


def _build_candidates(
    *,
    category: str,
    rationale: str,
    titles: Sequence[str],
) -> tuple[AlternativeCandidate, ...]:
    return tuple(
        AlternativeCandidate(
            title=title,
            category=category,
            priority=index + 1,
            rationale=rationale,
        )
        for index, title in enumerate(titles)
    )

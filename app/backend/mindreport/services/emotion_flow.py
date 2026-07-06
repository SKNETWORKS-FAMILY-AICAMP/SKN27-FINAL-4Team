from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from statistics import pstdev
from typing import Any, Sequence

from mindreport.services.scoring import EmotionScore


FLOW_SCORE_UPWARD = 'score_upward'
FLOW_SCORE_MAINTENANCE = 'score_maintenance'
FLOW_SCORE_VOLATILE = 'score_volatile'
FLOW_SCORE_DOWNWARD = 'score_downward'

MAINTENANCE_GREEN = 'green_maintenance'
MAINTENANCE_GRAY = 'gray_maintenance'
MAINTENANCE_RED = 'red_maintenance'
MAINTENANCE_INSUFFICIENT = 'maintenance_insufficient'

UPWARD_DELTA_THRESHOLD = 8.0
DOWNWARD_DELTA_THRESHOLD = -8.0
NET_CHANGE_THRESHOLD = 12.0
VOLATILITY_STDDEV_THRESHOLD = 16.0
LARGE_JUMP_THRESHOLD = 18.0
SIGNIFICANT_DIFF_THRESHOLD = 5.0


@dataclass(frozen=True)
class DailyScoreSummary:
    source_date: date
    average_score: float
    emotion_state: str
    score_count: int


@dataclass(frozen=True)
class EmotionFlowResult:
    flow_type: str
    maintenance_type: str | None
    tone_color: str | None
    title: str
    interpretation: str
    action_direction: str
    suggestions: tuple[str, ...]
    daily_summaries: tuple[DailyScoreSummary, ...]
    state_counts: dict[str, int]
    metrics: dict[str, Any]
    rationale: str
    detected_by: str


def analyze_emotion_flow(scores: Sequence[EmotionScore]) -> EmotionFlowResult:
    daily_summaries = _build_daily_summaries(scores)
    state_counts = dict(Counter(summary.emotion_state for summary in daily_summaries))
    metrics = _build_metrics(daily_summaries)

    if not daily_summaries:
        return _insufficient_result(daily_summaries, state_counts, metrics)

    flow_type = _classify_time_series_flow(metrics, len(daily_summaries))
    if flow_type == FLOW_SCORE_UPWARD:
        return _upward_result(daily_summaries, state_counts, metrics)
    if flow_type == FLOW_SCORE_VOLATILE:
        return _volatile_result(daily_summaries, state_counts, metrics)
    if flow_type == FLOW_SCORE_DOWNWARD:
        return _downward_result(daily_summaries, state_counts, metrics)

    return _maintenance_result(daily_summaries, state_counts, metrics)


def emotion_flow_result_to_payload(result: EmotionFlowResult) -> dict[str, Any]:
    return {
        'flow_type': result.flow_type,
        'maintenance_type': result.maintenance_type,
        'tone_color': result.tone_color,
        'title': result.title,
        'interpretation': result.interpretation,
        'action_direction': result.action_direction,
        'suggestions': list(result.suggestions),
        'state_counts': result.state_counts,
        'metrics': result.metrics,
        'rationale': result.rationale,
        'detected_by': result.detected_by,
        'daily_summaries': [
            {
                'source_date': summary.source_date.isoformat(),
                'average_score': summary.average_score,
                'emotion_state': summary.emotion_state,
                'score_count': summary.score_count,
            }
            for summary in result.daily_summaries
        ],
    }


def _build_daily_summaries(
    scores: Sequence[EmotionScore],
) -> tuple[DailyScoreSummary, ...]:
    return tuple(
        DailyScoreSummary(
            source_date=score.source_date,
            average_score=score.emotion_score,
            emotion_state=score.emotion_state,
            score_count=score.total_message_count,
        )
        for score in sorted(scores, key=lambda item: item.source_date)
    )


def _build_metrics(summaries: Sequence[DailyScoreSummary]) -> dict[str, Any]:
    values = [summary.average_score for summary in summaries]
    if not values:
        return {
            'score_count': 0,
            'first_score': None,
            'last_score': None,
            'first_half_average': None,
            'second_half_average': None,
            'half_delta': 0.0,
            'net_delta': 0.0,
            'stddev': 0.0,
            'large_jump_count': 0,
            'direction_change_count': 0,
            'diffs': [],
        }

    midpoint = max(1, len(values) // 2)
    first_half = values[:midpoint]
    second_half = values[midpoint:] or values[-1:]
    diffs = [
        round(values[index] - values[index - 1], 3)
        for index in range(1, len(values))
    ]

    return {
        'score_count': len(values),
        'first_score': values[0],
        'last_score': values[-1],
        'first_half_average': round(sum(first_half) / len(first_half), 3),
        'second_half_average': round(sum(second_half) / len(second_half), 3),
        'half_delta': round(
            (sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half)),
            3,
        ),
        'net_delta': round(values[-1] - values[0], 3),
        'stddev': round(pstdev(values), 3) if len(values) > 1 else 0.0,
        'large_jump_count': sum(
            1 for diff in diffs if abs(diff) >= LARGE_JUMP_THRESHOLD
        ),
        'direction_change_count': _count_direction_changes(diffs),
        'diffs': diffs,
    }


def _count_direction_changes(diffs: Sequence[float]) -> int:
    significant_signs = [
        1 if diff > 0 else -1
        for diff in diffs
        if abs(diff) >= SIGNIFICANT_DIFF_THRESHOLD
    ]
    return sum(
        1
        for index in range(1, len(significant_signs))
        if significant_signs[index] != significant_signs[index - 1]
    )


def _classify_time_series_flow(metrics: dict[str, Any], score_count: int) -> str:
    if score_count < 2:
        return FLOW_SCORE_MAINTENANCE

    if (
        score_count >= 3
        and metrics['stddev'] >= VOLATILITY_STDDEV_THRESHOLD
        and (
            metrics['direction_change_count'] >= 1
            or metrics['large_jump_count'] >= 2
        )
    ):
        return FLOW_SCORE_VOLATILE

    if (
        metrics['half_delta'] >= UPWARD_DELTA_THRESHOLD
        or metrics['net_delta'] >= NET_CHANGE_THRESHOLD
    ):
        return FLOW_SCORE_UPWARD

    if (
        metrics['half_delta'] <= DOWNWARD_DELTA_THRESHOLD
        or metrics['net_delta'] <= -NET_CHANGE_THRESHOLD
    ):
        return FLOW_SCORE_DOWNWARD

    return FLOW_SCORE_MAINTENANCE


def _dominant_state(summaries: Sequence[DailyScoreSummary]) -> str | None:
    if not summaries:
        return None

    counts = Counter(summary.emotion_state for summary in summaries)
    top_count = max(counts.values())
    tied_states = sorted(state for state, count in counts.items() if count == top_count)
    if len(tied_states) == 1:
        return tied_states[0]

    average_score = sum(summary.average_score for summary in summaries) / len(summaries)
    if average_score > 55:
        return 'positive'
    if average_score < 45:
        return 'negative'
    return 'neutral'


def _upward_result(
    daily_summaries: tuple[DailyScoreSummary, ...],
    state_counts: dict[str, int],
    metrics: dict[str, Any],
) -> EmotionFlowResult:
    return EmotionFlowResult(
        flow_type=FLOW_SCORE_UPWARD,
        maintenance_type=None,
        tone_color='green',
        title='점수 상향',
        interpretation='기간 후반의 감정 점수가 초반보다 높아진 회복 흐름으로 봅니다.',
        action_direction='회복에 도움 된 행동을 무리 없이 유지합니다.',
        suggestions=('도움 된 행동 유지', '짧은 산책', '편한 사람과 대화', '가벼운 취미 유지'),
        daily_summaries=daily_summaries,
        state_counts=state_counts,
        metrics=metrics,
        rationale='초반 대비 후반 평균 또는 첫날 대비 마지막 점수가 상승 기준을 넘었습니다.',
        detected_by='rule_time_series',
    )


def _volatile_result(
    daily_summaries: tuple[DailyScoreSummary, ...],
    state_counts: dict[str, int],
    metrics: dict[str, Any],
) -> EmotionFlowResult:
    return EmotionFlowResult(
        flow_type=FLOW_SCORE_VOLATILE,
        maintenance_type=None,
        tone_color='gray',
        title='감정 변동성',
        interpretation='긍정과 부정 흐름이 짧은 기간 안에서 크게 오르내린 상태로 봅니다.',
        action_direction='감정 기복을 줄이고 하루 리듬을 안정화하는 대안을 우선합니다.',
        suggestions=('수면/식사 시간 고정', '짧은 감정 기록', '자극이 큰 일정 줄이기', '가벼운 산책'),
        daily_summaries=daily_summaries,
        state_counts=state_counts,
        metrics=metrics,
        rationale='점수 표준편차와 상승/하락 전환 또는 큰 변화폭이 변동성 기준을 넘었습니다.',
        detected_by='rule_time_series',
    )


def _downward_result(
    daily_summaries: tuple[DailyScoreSummary, ...],
    state_counts: dict[str, int],
    metrics: dict[str, Any],
) -> EmotionFlowResult:
    return EmotionFlowResult(
        flow_type=FLOW_SCORE_DOWNWARD,
        maintenance_type=None,
        tone_color='red',
        title='점수 하향',
        interpretation='기간 후반의 감정 점수가 초반보다 낮아진 부담 증가 흐름으로 봅니다.',
        action_direction='최근 부담 요인을 줄이는 방향의 행동을 우선합니다.',
        suggestions=('일정 조정', '해야 할 일 나누기', '대화로 감정 꺼내기', '휴식 시간 확보'),
        daily_summaries=daily_summaries,
        state_counts=state_counts,
        metrics=metrics,
        rationale='초반 대비 후반 평균 또는 첫날 대비 마지막 점수가 하락 기준을 넘었습니다.',
        detected_by='rule_time_series',
    )


def _maintenance_result(
    daily_summaries: tuple[DailyScoreSummary, ...],
    state_counts: dict[str, int],
    metrics: dict[str, Any],
) -> EmotionFlowResult:
    dominant_state = _dominant_state(daily_summaries)
    if dominant_state == 'positive':
        return EmotionFlowResult(
            flow_type=FLOW_SCORE_MAINTENANCE,
            maintenance_type=MAINTENANCE_GREEN,
            tone_color='green',
            title='초록 유지',
            interpretation='긍정 감정이 여러 날 유지되어 현재 회복 루틴이 작동하는 상태로 봅니다.',
            action_direction='현재 도움 되는 행동을 무리 없이 유지합니다.',
            suggestions=('현재 루틴 유지', '가벼운 운동', '충분한 수면'),
            daily_summaries=daily_summaries,
            state_counts=state_counts,
            metrics=metrics,
            rationale='뚜렷한 상향/하향/변동성보다 긍정 상태 유지가 우세했습니다.',
            detected_by='rule_time_series',
        )

    if dominant_state == 'negative':
        return EmotionFlowResult(
            flow_type=FLOW_SCORE_MAINTENANCE,
            maintenance_type=MAINTENANCE_RED,
            tone_color='red',
            title='빨강 유지',
            interpretation='부정 감정이 여러 날 유지되어 스트레스가 지속되는 상태 가능성으로 봅니다.',
            action_direction='부담이 낮은 회복 행동부터 우선합니다.',
            suggestions=('수면 정리', '짧은 휴식', '편한 사람에게 연락', '일정 쪼개기'),
            daily_summaries=daily_summaries,
            state_counts=state_counts,
            metrics=metrics,
            rationale='뚜렷한 상향/하향/변동성보다 부정 상태 유지가 우세했습니다.',
            detected_by='rule_time_series',
        )

    return EmotionFlowResult(
        flow_type=FLOW_SCORE_MAINTENANCE,
        maintenance_type=MAINTENANCE_GRAY,
        tone_color='gray',
        title='회색 유지',
        interpretation='중립 감정이 여러 날 유지되어 감정 변화가 적거나 표현이 줄어든 상태 가능성으로 봅니다.',
        action_direction='감정 환기를 위한 작은 변화를 추가합니다.',
        suggestions=('짧은 산책', '카페 방문', '가까운 곳 여행', '관심 있는 게임'),
        daily_summaries=daily_summaries,
        state_counts=state_counts,
        metrics=metrics,
        rationale='뚜렷한 상향/하향/변동성보다 중립 또는 낮은 변화폭 유지가 우세했습니다.',
        detected_by='rule_time_series',
    )


def _insufficient_result(
    daily_summaries: tuple[DailyScoreSummary, ...],
    state_counts: dict[str, int],
    metrics: dict[str, Any],
) -> EmotionFlowResult:
    return EmotionFlowResult(
        flow_type=FLOW_SCORE_MAINTENANCE,
        maintenance_type=MAINTENANCE_INSUFFICIENT,
        tone_color=None,
        title='흐름 판단 보류',
        interpretation='감정 점수 흐름을 판단할 일 단위 점수 데이터가 아직 없습니다.',
        action_direction='감정 점수화 결과가 들어오면 흐름을 다시 판단합니다.',
        suggestions=(),
        daily_summaries=daily_summaries,
        state_counts=state_counts,
        metrics=metrics,
        rationale='일 단위 감정 점수 데이터가 없어 패턴 분류를 적용하지 않았습니다.',
        detected_by='rule_time_series',
    )

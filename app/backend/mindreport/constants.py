"""Stable domain constants and bounded runtime configuration for mind reports."""

from __future__ import annotations

import os


def _bounded_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _bounded_float(
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


# Periods and generation criteria
PERIOD_WEEK = 'week'
PERIOD_MONTH = 'month'
SUPPORTED_PERIODS = frozenset((PERIOD_WEEK, PERIOD_MONTH))
PERIOD_LABELS = {
    PERIOD_WEEK: '주간',
    PERIOD_MONTH: '월간',
}
REPORT_REQUIRED_MESSAGE_COUNTS = {
    PERIOD_WEEK: _bounded_int(
        'MINDREPORT_WEEKLY_REQUIRED_MESSAGES', 5, minimum=3, maximum=100
    ),
    PERIOD_MONTH: _bounded_int(
        'MINDREPORT_MONTHLY_REQUIRED_MESSAGES', 20, minimum=5, maximum=500
    ),
}

# Scoring contract
AFFECT_SCORING_METHOD = 'independent-affect-balance-v2'
LABEL_GROUNDED_AFFECT_SCORING_METHOD = (
    'persisted-label-grounded-affect-balance-v1'
)
SCORING_ROUTE_LABEL_GROUNDED = 'persisted_emotion_labels_primary'
SCORING_ROUTE_LLM_FALLBACK = 'raw_text_llm_fallback'
SCORING_ROUTE_KCELECTRA = 'kcelectra_scoring'
KCELECTRA_SCORING_METHOD = 'kcelectra-finetuned-v1'
KCELECTRA_EMOTION_CLASSES = ('기쁨', '슬픔', '분노', '일반')
KCELECTRA_SCORE_WEIGHTS = (70.0, 40.0, 30.0, 50.0)
KCELECTRA_REQUIRED_FILES = ('config.json', 'model.safetensors', 'tokenizer.json')
MINDREPORT_KCELECTRA_MODEL_PATH = os.environ.get(
    'MINDREPORT_KCELECTRA_MODEL_PATH', ''
).strip()
MINDREPORT_KCELECTRA_BATCH_SIZE = _bounded_int(
    'MINDREPORT_KCELECTRA_BATCH_SIZE', 16, minimum=1, maximum=256
)
MINDREPORT_KCELECTRA_MAX_LENGTH = _bounded_int(
    'MINDREPORT_KCELECTRA_MAX_LENGTH', 128, minimum=32, maximum=512
)
AFFECT_DIMENSION_MIN = 0
AFFECT_DIMENSION_MAX = 4
AFFECT_BALANCE_POINT_VALUE = 12.5
CONFIDENCE_LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
EMOTION_SCORE_NEGATIVE_MAX = _bounded_float(
    'MINDREPORT_NEGATIVE_SCORE_MAX', 45.0, minimum=0.0, maximum=49.0
)
EMOTION_SCORE_POSITIVE_MIN = _bounded_float(
    'MINDREPORT_POSITIVE_SCORE_MIN', 55.0, minimum=51.0, maximum=100.0
)

# Time-series flow contract
FLOW_SCORE_UPWARD = 'score_upward'
FLOW_SCORE_MAINTENANCE = 'score_maintenance'
FLOW_SCORE_VOLATILE = 'score_volatile'
FLOW_SCORE_DOWNWARD = 'score_downward'
MAINTENANCE_GREEN = 'green_maintenance'
MAINTENANCE_GRAY = 'gray_maintenance'
MAINTENANCE_RED = 'red_maintenance'
MAINTENANCE_INSUFFICIENT = 'maintenance_insufficient'
UPWARD_DELTA_THRESHOLD = _bounded_float(
    'MINDREPORT_UPWARD_DELTA_THRESHOLD', 8.0, minimum=1.0, maximum=50.0
)
DOWNWARD_DELTA_THRESHOLD = -UPWARD_DELTA_THRESHOLD
NET_CHANGE_THRESHOLD = _bounded_float(
    'MINDREPORT_NET_CHANGE_THRESHOLD', 12.0, minimum=1.0, maximum=100.0
)
VOLATILITY_STDDEV_THRESHOLD = _bounded_float(
    'MINDREPORT_VOLATILITY_STDDEV_THRESHOLD', 16.0, minimum=1.0, maximum=50.0
)
LARGE_JUMP_THRESHOLD = _bounded_float(
    'MINDREPORT_LARGE_JUMP_THRESHOLD', 18.0, minimum=1.0, maximum=100.0
)
SIGNIFICANT_DIFF_THRESHOLD = _bounded_float(
    'MINDREPORT_SIGNIFICANT_DIFF_THRESHOLD', 5.0, minimum=0.1, maximum=50.0
)
MIN_TREND_DAYS = _bounded_int(
    'MINDREPORT_MIN_TREND_DAYS', 3, minimum=3, maximum=31
)

# Public payload contract
FRONTEND_LIST_FIELDS = (
    'stressCauses',
    'reliefCauses',
    'causeLabels',
    'hardMoments',
    'reliefMoments',
    'emotions',
    'analysis',
    'recommendations',
    'suggestionCards',
)
FRONTEND_REQUIRED_TEXT_FIELDS = ('type', 'range', 'title', 'summary')
GRAPH_REPORT_PAYLOAD_STATUSES = frozenset(('completed', 'safety_ready'))
GRAPH_FALLBACK_PAYLOAD_STATUS = 'fallback_ready'

# Model defaults
MINDREPORT_SCORING_MODEL = os.environ.get(
    'MINDREPORT_SCORING_MODEL', 'gpt-5.4-mini'
)
MINDREPORT_KEYWORD_MODEL = os.environ.get(
    'MINDREPORT_KEYWORD_MODEL', 'gpt-5.4-mini'
)
MINDREPORT_CAUSE_KEYWORD_MODEL = os.environ.get(
    'MINDREPORT_CAUSE_KEYWORD_MODEL', 'gpt-5.4-mini'
)
MINDREPORT_NARRATIVE_MODEL = os.environ.get(
    'MINDREPORT_NARRATIVE_MODEL', 'gpt-5.4-mini'
)
MINDREPORT_LLM_TEMPERATURE = 0
MINDREPORT_SCORING_MAX_TOKENS = _bounded_int(
    'MINDREPORT_SCORING_MAX_TOKENS', 1400, minimum=200, maximum=8000
)
MINDREPORT_KEYWORD_MAX_TOKENS = _bounded_int(
    'MINDREPORT_KEYWORD_MAX_TOKENS', 1200, minimum=200, maximum=8000
)
MINDREPORT_CAUSE_MAX_TOKENS = _bounded_int(
    'MINDREPORT_CAUSE_MAX_TOKENS', 1000, minimum=200, maximum=8000
)
MINDREPORT_NARRATIVE_MAX_TOKENS = _bounded_int(
    'MINDREPORT_NARRATIVE_MAX_TOKENS', 1200, minimum=200, maximum=8000
)

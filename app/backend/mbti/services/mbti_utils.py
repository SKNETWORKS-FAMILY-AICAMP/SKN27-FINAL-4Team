from __future__ import annotations

from datetime import timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MBTI_AXES = ('IE', 'SN', 'TF', 'JP')

AXIS_TYPE_INDEX = {
    'IE': 0,
    'SN': 1,
    'TF': 2,
    'JP': 3,
}

AXIS_ALLOWED_LETTERS = {
    'IE': {'I', 'E'},
    'SN': {'S', 'N'},
    'TF': {'T', 'F'},
    'JP': {'J', 'P'},
}

VALID_MBTI_TYPES = {
    'ISTJ', 'ISFJ', 'INFJ', 'INTJ',
    'ISTP', 'ISFP', 'INFP', 'INTP',
    'ESTP', 'ESFP', 'ENFP', 'ENTP',
    'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ',
}

try:
    SEOUL_TZ = ZoneInfo('Asia/Seoul')
except ZoneInfoNotFoundError:
    SEOUL_TZ = timezone(timedelta(hours=9), name='Asia/Seoul')

PERIOD_KEY_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')

# Direction mappings for MBTI axes
AXIS_LETTER_DIRECTIONS = {
    'IE': {'positive': 'E', 'negative': 'I'},
    'SN': {'positive': 'S', 'negative': 'N'},
    'TF': {'positive': 'T', 'negative': 'F'},
    'JP': {'positive': 'J', 'negative': 'P'},
}

AXIS_DIRECTION_LABELS = {
    'IE': ('I', 'E'),
    'SN': ('N', 'S'),
    'TF': ('F', 'T'),
    'JP': ('P', 'J'),
}

VALID_CODING_STATUSES = {'coded', 'insufficient_context', 'failed'}

DEFAULT_OPENAI_SCORING_MODEL = 'gpt-5.4-mini'

AXIS_CHOICES = [
    ('IE', 'IE'),
    ('SN', 'SN'),
    ('TF', 'TF'),
    ('JP', 'JP'),
]

CODING_STATUS_CHOICES = [
    ('coded', 'coded'),
    ('insufficient_context', 'insufficient_context'),
    ('failed', 'failed'),
]

BASELINE_SOURCE_CHOICES = [
    ('latest_monthly_result', 'latest_monthly_result'),
    ('onboarding', 'onboarding'),
    ('none', 'none'),
]

AXIS_DATA_STATUS_CHOICES = [
    ('current_month', 'current_month'),
    ('primary_closed', 'primary_closed'),
    ('secondary_closed', 'secondary_closed'),
    ('tie_carried', 'tie_carried'),
    ('carried_from_previous', 'carried_from_previous'),
    ('carried_from_onboarding', 'carried_from_onboarding'),
    ('insufficient_axis_data', 'insufficient_axis_data'),
]


def is_valid_mbti_type(mbti_type: str | None) -> str | None:
    """Validate if the given string is a valid 4-letter MBTI type."""
    if not mbti_type:
        return None
    normalized = mbti_type.strip().upper()
    return normalized if normalized in VALID_MBTI_TYPES else None

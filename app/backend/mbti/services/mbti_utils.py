from __future__ import annotations

from datetime import timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mbti.constants import VALID_MBTI_TYPES


try:
    SEOUL_TZ = ZoneInfo("Asia/Seoul")
except ZoneInfoNotFoundError:
    SEOUL_TZ = timezone(timedelta(hours=9), name="Asia/Seoul")

PERIOD_KEY_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def is_valid_mbti_type(mbti_type: str | None) -> str | None:
    """Return a normalized MBTI type when it is valid."""
    if not mbti_type:
        return None
    normalized = mbti_type.strip().upper()
    return normalized if normalized in VALID_MBTI_TYPES else None

from __future__ import annotations

from collections.abc import Iterable


MIN_PROFILE_PREFERENCE_COUNT = 3
PROFILE_PREFERENCE_MINIMUM_ERROR = (
    f'관심사와 취미를 합쳐 {MIN_PROFILE_PREFERENCE_COUNT}개 이상 선택해 주세요.'
)


def normalize_preference_labels(values: Iterable[object] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        label = str(value).strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        normalized.append(label)
    return normalized


def preference_count(*, hobbies: Iterable[object] | None, interests: Iterable[object] | None) -> int:
    labels = normalize_preference_labels([*(hobbies or ()), *(interests or ())])
    return len(labels)


def has_minimum_preferences(
    *,
    hobbies: Iterable[object] | None,
    interests: Iterable[object] | None,
) -> bool:
    return preference_count(hobbies=hobbies, interests=interests) >= MIN_PROFILE_PREFERENCE_COUNT

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from mbti.services.monthly_results import AXIS_ALLOWED_LETTERS, AXIS_TYPE_INDEX
from mbti.services.monthly_questions import MBTI_AXES


class MonthlyResultLike(Protocol):
    user_id: int
    period_key: str
    estimated_mbti_type: str | None


class OnboardingProfileLike(Protocol):
    user_id: int
    mbti_type: str | None


class AxisResultLike(Protocol):
    user_id: int
    period_key: str
    axis: str
    selected_letter: str | None
    axis_avg: float | None
    axis_ratios_json: Mapping[str, float] | None


@dataclass(frozen=True)
class OnboardingSnapshot:
    user_id: int
    mbti_type: str | None


ONBOARDING_MBTI_KEYS = (
    'mbti_type',
    'onboarding_mbti_type',
    'onboarding_mbti',
    'mbti',
)


@dataclass(frozen=True)
class UserBaselineSnapshot:
    user_id: int
    previous_axis_letters: dict[str, str]
    previous_axis_period_keys: dict[str, str]
    previous_axis_avgs: dict[str, float | None]
    previous_axis_ratios: dict[str, dict[str, float]]
    previous_period_key: str | None
    previous_estimated_mbti_type: str | None
    onboarding_mbti_type: str | None


def extract_axis_letters_from_mbti_type(
    mbti_type: str | None,
) -> dict[str, str]:
    if mbti_type is None:
        return {}

    normalized = mbti_type.strip().upper()
    if len(normalized) != 4:
        return {}

    axis_letters: dict[str, str] = {}
    for axis in MBTI_AXES:
        letter = normalized[AXIS_TYPE_INDEX[axis]]
        if letter in AXIS_ALLOWED_LETTERS[axis]:
            axis_letters[axis] = letter

    return axis_letters


def build_user_baseline_snapshot(
    *,
    user_id: int,
    previous_monthly_result: MonthlyResultLike | None = None,
    previous_axis_results: list[AxisResultLike] | tuple[AxisResultLike, ...] = (),
    onboarding_profile: OnboardingProfileLike | None = None,
) -> UserBaselineSnapshot:
    if previous_monthly_result is not None and previous_monthly_result.user_id != user_id:
        raise ValueError('previous_monthly_result.user_id must match user_id.')
    for axis_result in previous_axis_results:
        if axis_result.user_id != user_id:
            raise ValueError('previous_axis_results.user_id must match user_id.')
    if onboarding_profile is not None and onboarding_profile.user_id != user_id:
        raise ValueError('onboarding_profile.user_id must match user_id.')

    previous_type = (
        previous_monthly_result.estimated_mbti_type
        if previous_monthly_result is not None
        else None
    )
    onboarding_type = (
        onboarding_profile.mbti_type
        if onboarding_profile is not None
        else None
    )
    previous_axis_letters = extract_axis_letters_from_mbti_type(previous_type)
    previous_axis_period_keys = {
        axis: previous_monthly_result.period_key
        for axis in previous_axis_letters
        if previous_monthly_result is not None
    }
    previous_axis_avgs: dict[str, float | None] = {}
    previous_axis_ratios: dict[str, dict[str, float]] = {}

    for axis_result in previous_axis_results:
        axis = axis_result.axis
        letter = axis_result.selected_letter
        if axis not in MBTI_AXES:
            continue
        if letter not in AXIS_ALLOWED_LETTERS[axis]:
            continue
        if axis not in previous_axis_letters:
            previous_axis_letters[axis] = letter
        previous_axis_period_keys[axis] = axis_result.period_key
        previous_axis_avgs[axis] = axis_result.axis_avg
        previous_axis_ratios[axis] = dict(axis_result.axis_ratios_json or {})

    return UserBaselineSnapshot(
        user_id=user_id,
        previous_axis_letters=previous_axis_letters,
        previous_axis_period_keys=previous_axis_period_keys,
        previous_axis_avgs=previous_axis_avgs,
        previous_axis_ratios=previous_axis_ratios,
        previous_period_key=(
            previous_monthly_result.period_key
            if previous_monthly_result is not None
            else None
        ),
        previous_estimated_mbti_type=previous_type or onboarding_type,
        onboarding_mbti_type=onboarding_type,
    )


def _extract_mbti_from_mapping(data: Mapping[str, Any] | None) -> str | None:
    if not data:
        return None

    for key in ONBOARDING_MBTI_KEYS:
        value = data.get(key)
        if isinstance(value, str) and extract_axis_letters_from_mbti_type(value):
            return value.strip().upper()

    for nested_key in ('onboarding', 'profile', 'mbti_data'):
        nested = data.get(nested_key)
        if isinstance(nested, Mapping):
            nested_value = _extract_mbti_from_mapping(nested)
            if nested_value:
                return nested_value

    return None


def _extract_mbti_from_object(obj: object | None) -> str | None:
    if obj is None:
        return None

    for key in ONBOARDING_MBTI_KEYS:
        value = getattr(obj, key, None)
        if isinstance(value, str) and extract_axis_letters_from_mbti_type(value):
            return value.strip().upper()

    for key in ('profile_data', 'onboarding_data', 'extra_data'):
        value = getattr(obj, key, None)
        if isinstance(value, Mapping):
            mapped_value = _extract_mbti_from_mapping(value)
            if mapped_value:
                return mapped_value

    return None


def load_onboarding_snapshot(
    *,
    user_id: int,
) -> OnboardingSnapshot | None:
    """Read onboarding MBTI from the onboarding/user-side DB first.

    The current project does not expose one fixed onboarding MBTI column yet, so
    this adapter checks likely user/profile JSON fields without changing other
    apps. The mbti-owned fallback table remains available for local tests and
    future migration bridges.
    """
    try:
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.filter(id=user_id).first()
    except Exception:
        user = None

    mbti_type = _extract_mbti_from_object(user)
    if not mbti_type and user is not None:
        for related_name in ('mypage_profile', 'onboarding_profile', 'profile'):
            try:
                related = getattr(user, related_name)
            except Exception:
                continue
            mbti_type = _extract_mbti_from_object(related)
            if mbti_type:
                break

    if mbti_type:
        return OnboardingSnapshot(user_id=user_id, mbti_type=mbti_type)

    from mbti.models import MbtiOnboardingProfile

    fallback = (
        MbtiOnboardingProfile.objects
        .filter(
            user_id=user_id,
            mbti_type__isnull=False,
        )
        .order_by('-updated_at', '-id')
        .first()
    )
    if fallback is None:
        return None
    return OnboardingSnapshot(user_id=user_id, mbti_type=fallback.mbti_type)


def load_user_baseline_snapshot(
    *,
    user_id: int,
    current_period_key: str,
) -> UserBaselineSnapshot:
    """Load one user's baseline values for G/M.

    Previous monthly result is preferred. If it does not exist, onboarding is
    still returned so unresolved axes can fall back to onboarding.
    """
    from mbti.models import (
        MbtiMonthlyAxisResult,
        MbtiMonthlyResultRecord,
    )

    previous = (
        MbtiMonthlyResultRecord.objects
        .filter(
            user_id=user_id,
            period_key__lt=current_period_key,
            status='complete',
            estimated_mbti_type__isnull=False,
        )
        .order_by('-period_key', '-id')
        .first()
    )
    axis_candidates = (
        MbtiMonthlyAxisResult.objects
        .filter(
            user_id=user_id,
            period_key__lt=current_period_key,
            selected_letter__isnull=False,
        )
        .order_by('-period_key', '-id')
    )
    previous_axis_results = []
    seen_axes = set()
    for axis_result in axis_candidates:
        if axis_result.axis in seen_axes:
            continue
        previous_axis_results.append(axis_result)
        seen_axes.add(axis_result.axis)
        if len(seen_axes) == len(MBTI_AXES):
            break

    onboarding = load_onboarding_snapshot(user_id=user_id)

    return build_user_baseline_snapshot(
        user_id=user_id,
        previous_monthly_result=previous,
        previous_axis_results=tuple(previous_axis_results),
        onboarding_profile=onboarding,
    )

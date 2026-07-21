from __future__ import annotations

from django.utils.timezone import now

from mbti.models import MbtiOnboardingProfile


def save_onboarding_mbti(*, user_id: int, mbti_type: str) -> MbtiOnboardingProfile:
    timestamp = now()
    profile, created = MbtiOnboardingProfile.objects.update_or_create(
        user_id=user_id,
        defaults={"mbti_type": mbti_type, "updated_at": timestamp},
    )
    if created:
        profile.created_at = timestamp
        profile.save(update_fields=["created_at"])
    return profile

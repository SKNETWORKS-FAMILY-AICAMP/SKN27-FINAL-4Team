from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='myprofile',
    )
    name = models.CharField(max_length=30)
    mbti = models.CharField(max_length=4)
    gender = models.CharField(max_length=20)
    age = models.PositiveSmallIntegerField()
    birthday = models.CharField(max_length=20)
    job = models.CharField(max_length=80)
    status = models.CharField(max_length=80)
    keywords = models.CharField(max_length=255)
    interests = models.JSONField(default=list)
    hobbies = models.CharField(max_length=80)
    selected_character = models.CharField(max_length=20, default='sol')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # ⚠️ user 앱 UserProfile(user_profiles)과 테이블명 충돌 → 임시로 분리 (2026-07-02)
        #    두 프로필 모델 통합 여부는 팀 결정 필요 (온보딩 담당 ↔ 마이페이지 담당)
        db_table = 'myprofile_profiles'

    def __str__(self):
        return f'{self.user_id}: {self.name}'

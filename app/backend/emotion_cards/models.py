import uuid

from django.conf import settings
from django.db import models


class FeatureCode(models.Model):
    group = models.CharField(max_length=40)
    code = models.CharField(max_length=80)
    label = models.CharField(max_length=120)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['group', 'code'], name='emotion_feature_code_unique')]
        indexes = [models.Index(fields=['group', 'code'])]


class CatalogEntry(models.Model):
    catalog = models.CharField(max_length=48)
    code = models.CharField(max_length=100)
    display_name = models.CharField(max_length=160)
    visual_prompt = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['catalog', 'code'], name='emotion_catalog_entry_unique')]
        indexes = [models.Index(fields=['catalog', 'code', 'enabled'])]


class RuleEntry(models.Model):
    rule_type = models.CharField(max_length=48)
    rule_id = models.CharField(max_length=80)
    data = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['rule_type', 'rule_id'], name='emotion_rule_entry_unique')]
        indexes = [models.Index(fields=['rule_type', 'enabled'])]


class SocialCompanionRule(models.Model):
    rule_id = models.CharField(max_length=24, unique=True)
    social_context = models.CharField(max_length=40, db_index=True)
    companion_type = models.CharField(max_length=64)
    companion_count_max = models.PositiveSmallIntegerField(default=0)
    visual_prompt = models.TextField()
    privacy_note = models.CharField(max_length=240, blank=True)
    weight = models.IntegerField(default=35)
    enabled = models.BooleanField(default=True)


class EmotionCardAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emotion_card_analyses')
    raw_input = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    analysis_status = models.CharField(max_length=32, default='CLEAR')
    safety_status = models.CharField(max_length=16, default='SAFE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'created_at'])]


class EmotionCardScene(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emotion_card_scenes')
    analysis = models.ForeignKey(EmotionCardAnalysis, on_delete=models.CASCADE, related_name='scenes')
    scene_hash = models.CharField(max_length=64, db_index=True)
    scene_spec = models.JSONField(default=dict)
    available_styles = models.JSONField(default=list)
    safety_status = models.CharField(max_length=16, default='SAFE')
    invalidated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'scene_hash'])]


class EmotionCardJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emotion_card_jobs')
    scene = models.ForeignKey(EmotionCardScene, on_delete=models.CASCADE, related_name='jobs')
    style_id = models.CharField(max_length=100)
    idempotency_key = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='PENDING')
    progress = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=80, blank=True)
    card = models.ForeignKey('GeneratedEmotionCard', on_delete=models.SET_NULL, blank=True, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'created_at'])]


class GeneratedEmotionCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emotion_cards')
    scene = models.ForeignKey(EmotionCardScene, on_delete=models.PROTECT, related_name='cards')
    style_id = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, default='')
    image_alt = models.CharField(max_length=240)
    summary = models.CharField(max_length=240)
    feedback = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'created_at'])]


class EmotionCardUsageReset(models.Model):
    """사용자가 오늘의 이미지 생성 사용량을 초기화한 시점을 보관한다."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emotion_card_usage_reset')
    reset_at = models.DateTimeField()

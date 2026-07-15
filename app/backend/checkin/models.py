from django.conf import settings
from django.db import models


EMOTION_CHOICES = [(value, value) for value in ('JOY', 'SADNESS', 'ANGER', 'ANXIETY')]
ENERGY_CHOICES = [(value, value) for value in ('LOW', 'MEDIUM', 'HIGH', 'UNKNOWN')]
STAGE_CHOICES = [(value, value) for value in ('REFLECTION', 'CAUSE', 'NEED', 'RECOMMENDATION', 'FINAL_ROUTE', 'COMPLETED')]
ROUTE_CHOICES = [(value, value) for value in ('CHAT', 'ACTION', 'RECORD_ONLY')]
CAUSE_CONTEXT_CHOICES = [(value, value) for value in ('POSITIVE', 'DIFFICULT', 'MIXED', 'NEUTRAL', 'SKIP')]


class ReflectionOption(models.Model):
    reflection_id = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=180)
    hint = models.CharField(max_length=240, blank=True)
    icon = models.CharField(max_length=16, blank=True)
    primary_emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES, blank=True)
    secondary_emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES, blank=True)
    emotion_intensity_default = models.PositiveSmallIntegerField(default=0)
    state_tags = models.JSONField(default=list, blank=True)
    energy_level = models.CharField(max_length=10, choices=ENERGY_CHOICES, default='MEDIUM')
    cause_context = models.CharField(max_length=20, choices=CAUSE_CONTEXT_CHOICES, default='DIFFICULT')
    ack_key = models.CharField(max_length=60, blank=True)
    next_stage = models.CharField(max_length=30, default='CAUSE')
    include_weekly = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'checkin_reflection_options'
        ordering = ['display_order', 'reflection_id']


class CauseContextConfig(models.Model):
    cause_context = models.CharField(max_length=20, choices=CAUSE_CONTEXT_CHOICES, primary_key=True)
    display_order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=120)
    question_text = models.CharField(max_length=240)
    option_text_field = models.CharField(max_length=50, blank=True)
    show_cause_options = models.BooleanField(default=True)
    next_stage = models.CharField(max_length=30, default='CAUSE')
    weekly_label = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = 'checkin_cause_contexts'
        ordering = ['display_order', 'cause_context']


class CauseOption(models.Model):
    cause_id = models.CharField(max_length=50, primary_key=True)
    cause_code = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=180)
    hint = models.CharField(max_length=240, blank=True)
    icon = models.CharField(max_length=16, blank=True)
    available_contexts = models.JSONField(default=list, blank=True)
    option_text_neutral = models.CharField(max_length=240, blank=True)
    option_text_positive = models.CharField(max_length=240, blank=True)
    option_text_difficult = models.CharField(max_length=240, blank=True)
    option_text_mixed = models.CharField(max_length=240, blank=True)
    examples_internal = models.CharField(max_length=240, blank=True)
    sensitive = models.BooleanField(default=False)
    chat_seed = models.CharField(max_length=240, blank=True)
    chat_seed_templates = models.JSONField(default=dict, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'checkin_cause_options'
        ordering = ['display_order', 'cause_id']


class NeedOption(models.Model):
    need_id = models.CharField(max_length=50, primary_key=True)
    need_code = models.CharField(max_length=50, blank=True, db_index=True)
    label = models.CharField(max_length=180)
    hint = models.CharField(max_length=240, blank=True)
    icon = models.CharField(max_length=16, blank=True)
    response_mode = models.CharField(max_length=50, default='GENTLE')
    llm_instruction = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'checkin_need_options'
        ordering = ['display_order', 'need_id']


class CharacterToneRule(models.Model):
    character_id = models.CharField(max_length=20, primary_key=True)
    tone = models.CharField(max_length=120)
    avoid_phrases = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'checkin_character_tone_rules'


class CharacterFragment(models.Model):
    character_id = models.CharField(max_length=20)
    stage = models.CharField(max_length=30)
    fragment_key = models.CharField(max_length=50)
    text = models.CharField(max_length=240)

    class Meta:
        db_table = 'checkin_character_fragments'
        constraints = [
            models.UniqueConstraint(fields=['character_id', 'stage', 'fragment_key'], name='uniq_checkin_character_fragment'),
        ]


class DialogueTemplate(models.Model):
    stage = models.CharField(max_length=30)
    context_key = models.CharField(max_length=50, default='base')
    template = models.CharField(max_length=500)

    class Meta:
        db_table = 'checkin_dialogue_templates'
        constraints = [
            models.UniqueConstraint(fields=['stage', 'context_key'], name='uniq_checkin_dialogue_template'),
        ]


class PreferenceMapping(models.Model):
    source_label = models.CharField(max_length=100)
    target_action_ids = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'checkin_preference_mappings'
        constraints = [
            models.UniqueConstraint(fields=['source_label'], name='uniq_checkin_preference_source'),
        ]


class RecommendationAction(models.Model):
    action_id = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=180)
    description = models.TextField()
    expected_minutes = models.PositiveIntegerField(default=3)
    icon = models.CharField(max_length=16, blank=True)
    tags = models.JSONField(default=list, blank=True)
    suitable_needs = models.JSONField(default=list, blank=True)
    suitable_emotions = models.JSONField(default=list, blank=True)
    energy_levels = models.JSONField(default=list, blank=True)
    linked_keywords = models.JSONField(default=list, blank=True)
    avoid_emotions = models.JSONField(default=list, blank=True)
    avoid_causes = models.JSONField(default=list, blank=True)
    default_weight = models.IntegerField(default=0)
    safety_notice = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = 'checkin_recommendation_actions'
        ordering = ['-default_weight', 'action_id']


class DailyCheckin(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_checkins')
    checkin_date = models.DateField()
    stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='REFLECTION')
    reflection = models.ForeignKey(ReflectionOption, null=True, blank=True, on_delete=models.PROTECT, related_name='checkins')
    cause_context = models.CharField(max_length=20, choices=CAUSE_CONTEXT_CHOICES, blank=True)
    primary_emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES, blank=True)
    secondary_emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES, blank=True)
    state_tags = models.JSONField(default=list, blank=True)
    energy_level = models.CharField(max_length=10, choices=ENERGY_CHOICES, blank=True)
    cause = models.ForeignKey(CauseOption, null=True, blank=True, on_delete=models.PROTECT, related_name='checkins')
    cause_display_text_snapshot = models.CharField(max_length=240, blank=True)
    need = models.ForeignKey(NeedOption, null=True, blank=True, on_delete=models.PROTECT, related_name='checkins')
    selected_action = models.ForeignKey(RecommendationAction, null=True, blank=True, on_delete=models.PROTECT, related_name='selected_checkins')
    final_route = models.CharField(max_length=20, choices=ROUTE_CHOICES, blank=True)
    character_id = models.CharField(max_length=20, blank=True)
    character_snapshot = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'checkin_daily_checkins'
        constraints = [
            models.UniqueConstraint(fields=['user', 'checkin_date'], name='uniq_checkin_user_date'),
        ]
        indexes = [models.Index(fields=['user', 'checkin_date']), models.Index(fields=['user', 'stage'])]


class CheckinRecommendation(models.Model):
    checkin = models.ForeignKey(DailyCheckin, on_delete=models.CASCADE, related_name='recommendations')
    action = models.ForeignKey(RecommendationAction, on_delete=models.PROTECT, related_name='recommendations')
    score = models.IntegerField(default=0)
    rank = models.PositiveIntegerField(default=0)
    reason_codes = models.JSONField(default=list, blank=True)
    selected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'checkin_recommendations'
        constraints = [
            models.UniqueConstraint(fields=['checkin', 'action'], name='uniq_checkin_recommendation_action'),
        ]
        ordering = ['rank', 'action_id']


class ActionFeedback(models.Model):
    checkin = models.ForeignKey(DailyCheckin, on_delete=models.CASCADE, related_name='feedback')
    action = models.ForeignKey(RecommendationAction, on_delete=models.PROTECT, related_name='feedback')
    completed = models.BooleanField(default=False)
    helpfulness = models.PositiveSmallIntegerField()
    feedback_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'checkin_action_feedback'
        constraints = [
            models.UniqueConstraint(fields=['checkin', 'action'], name='uniq_checkin_action_feedback'),
        ]

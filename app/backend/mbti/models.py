from django.db import models


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
ANALYSIS_JOB_STATUS_CHOICES = [
    ('pending', 'pending'),
    ('running', 'running'),
    ('complete', 'complete'),
    ('skipped', 'skipped'),
    ('failed', 'failed'),
]
ANALYSIS_JOB_TRIGGER_CHOICES = [
    ('monthly_scheduler', 'monthly_scheduler'),
    ('dashboard_on_demand', 'dashboard_on_demand'),
    ('manual', 'manual'),
]


class MbtiQuestionResponse(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    conversation_id = models.BigIntegerField(null=True, blank=True)
    question_message_id = models.BigIntegerField(null=True, blank=True)
    answer_message_id = models.BigIntegerField(null=True, blank=True)
    question_text = models.TextField()
    answer_text = models.TextField()
    target_axis = models.CharField(max_length=2, choices=AXIS_CHOICES)
    period_key = models.CharField(max_length=7, db_index=True)
    answered_at = models.DateTimeField()
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'mbti'
        db_table = 'mbti_question_responses'
        indexes = [
            models.Index(fields=['user_id', 'period_key', 'target_axis']),
            models.Index(fields=['user_id', 'answered_at']),
        ]
        ordering = ['answered_at', 'id']


class MbtiResponseScore(models.Model):
    question_response = models.OneToOneField(
        MbtiQuestionResponse,
        db_column='question_response_id',
        on_delete=models.DO_NOTHING,
        related_name='score_result',
    )
    user_id = models.BigIntegerField(db_index=True)
    period_key = models.CharField(max_length=7, db_index=True)
    axis = models.CharField(max_length=2, choices=AXIS_CHOICES, db_index=True)
    score = models.FloatField(null=True, blank=True)
    direction = models.CharField(max_length=16, default='unknown')
    coding_status = models.CharField(
        max_length=32,
        choices=CODING_STATUS_CHOICES,
        db_index=True,
    )
    evidence_span = models.TextField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    model = models.CharField(max_length=64, null=True, blank=True)
    scored_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'mbti'
        db_table = 'mbti_response_scores'
        indexes = [
            models.Index(fields=['user_id', 'period_key', 'axis']),
            models.Index(fields=['axis', 'coding_status']),
            models.Index(fields=['question_response']),
        ]
        ordering = ['question_response_id']


class MbtiMonthlyResultRecord(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    period_key = models.CharField(max_length=7, db_index=True)
    previous_estimated_mbti_type = models.CharField(
        max_length=4,
        null=True,
        blank=True,
    )
    previous_period_key = models.CharField(max_length=7, null=True, blank=True)
    estimated_mbti_type = models.CharField(max_length=4, null=True, blank=True)
    changed_axes_json = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=32, default='complete')
    analyzed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'mbti'
        db_table = 'mbti_monthly_results'
        indexes = [
            models.Index(fields=['user_id', 'period_key']),
            models.Index(fields=['user_id', 'status', 'period_key']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'period_key'],
                name='uniq_mbti_monthly_result_user_period',
            ),
        ]
        ordering = ['-period_key', '-id']


class MbtiMonthlyAxisResult(models.Model):
    monthly_result = models.ForeignKey(
        MbtiMonthlyResultRecord,
        db_column='monthly_result_id',
        on_delete=models.DO_NOTHING,
        related_name='axis_results',
    )
    user_id = models.BigIntegerField(db_index=True)
    period_key = models.CharField(max_length=7, db_index=True)
    axis = models.CharField(max_length=2, choices=AXIS_CHOICES, db_index=True)
    qna_count = models.IntegerField(default=0)
    required_qna_count = models.IntegerField(default=5)
    primary_open = models.BooleanField(default=False)
    scored_count = models.IntegerField(default=0)
    required_scored_count = models.IntegerField(default=1)
    secondary_open = models.BooleanField(default=False)
    axis_avg = models.FloatField(null=True, blank=True)
    axis_ratios_json = models.JSONField(default=dict, blank=True)
    selected_letter = models.CharField(max_length=1, null=True, blank=True)
    data_status = models.CharField(
        max_length=32,
        choices=AXIS_DATA_STATUS_CHOICES,
        db_index=True,
    )
    calculation_status = models.CharField(max_length=32, null=True, blank=True)
    baseline_letter = models.CharField(max_length=1, null=True, blank=True)
    baseline_source = models.CharField(
        max_length=32,
        choices=BASELINE_SOURCE_CHOICES,
        null=True,
        blank=True,
    )
    baseline_period_key = models.CharField(max_length=7, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'mbti'
        db_table = 'mbti_monthly_axis_results'
        indexes = [
            models.Index(fields=['monthly_result', 'axis']),
            models.Index(fields=['user_id', 'period_key', 'axis']),
            models.Index(fields=['user_id', 'axis', 'period_key']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['monthly_result', 'axis'],
                name='uniq_mbti_monthly_axis_result',
            ),
        ]
        ordering = ['monthly_result_id', 'axis']


class MbtiMonthlyReport(models.Model):
    monthly_result = models.OneToOneField(
        MbtiMonthlyResultRecord,
        db_column='monthly_result_id',
        on_delete=models.DO_NOTHING,
        related_name='report',
    )
    report_sections_json = models.JSONField(default=list, blank=True)
    evidence_items_json = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'mbti'
        db_table = 'mbti_monthly_reports'
        indexes = [
            models.Index(fields=['monthly_result']),
        ]
        ordering = ['-generated_at', '-id']





class MbtiOnboardingProfile(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    mbti_type = models.CharField(max_length=4, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'mbti'
        db_table = 'mbti_onboarding_profiles'
        indexes = [
            models.Index(fields=['user_id']),
        ]
        ordering = ['-updated_at', '-id']

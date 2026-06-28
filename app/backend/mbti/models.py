from django.db import models


class MbtiQuestionResponse(models.Model):
    AXIS_CHOICES = [
        ('IE', 'IE'),
        ('SN', 'SN'),
        ('TF', 'TF'),
        ('JP', 'JP'),
    ]

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
        managed = False
        db_table = 'mbti_question_responses'
        indexes = [
            models.Index(fields=['user_id', 'period_key', 'target_axis']),
            models.Index(fields=['user_id', 'answered_at']),
        ]
        ordering = ['answered_at', 'id']

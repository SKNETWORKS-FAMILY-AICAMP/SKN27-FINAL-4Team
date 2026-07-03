from datetime import timedelta

from django.db import models
from django.utils import timezone


class ConversationLogQuerySet(models.QuerySet):
    def analysis_source_for_user(self, user_id):
        return self.filter(user_id=user_id)

    def user_messages(self):
        return self.filter(role="user").exclude(message_text="")

    def within_recent_days(self, days=30, reference_at=None):
        reference_at = reference_at or timezone.now()
        started_at = reference_at - timedelta(days=days)
        return self.filter(created_at__gte=started_at, created_at__lte=reference_at)

    def recent_user_messages(self, user_id, days=30, reference_at=None):
        return (
            self.analysis_source_for_user(user_id)
            .user_messages()
            .within_recent_days(days=days, reference_at=reference_at)
            .order_by("created_at", "conversation_id", "id")
        )

    def as_analysis_input(self):
        return self.values(
            "id",
            "user_id",
            "conversation_id",
            "message_text",
            "created_at",
        )


class ConversationLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(db_index=True)
    conversation_id = models.BigIntegerField(db_index=True)
    role = models.CharField(max_length=20, db_index=True)
    message_text = models.TextField()
    created_at = models.DateTimeField(db_index=True)

    objects = ConversationLogQuerySet.as_manager()

    class Meta:
        db_table = "conversation_logs"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["user_id", "role", "created_at"]),
            models.Index(fields=["conversation_id", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.role}:{self.created_at:%Y-%m-%d %H:%M}"


class PreferenceEvidence(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(db_index=True)
    message = models.ForeignKey(
        ConversationLog,
        db_column="message_id",
        on_delete=models.DO_NOTHING,
        related_name="preference_evidence",
    )
    period_key = models.CharField(max_length=20, db_index=True)
    normalized_keyword = models.CharField(max_length=100, db_index=True)
    preference_type = models.CharField(max_length=50, db_index=True)
    evidence_text = models.TextField()
    conversation_context = models.TextField()
    source_created_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "preference_evidence"
        ordering = ["-source_created_at", "-id"]
        indexes = [
            models.Index(fields=["user_id", "period_key", "normalized_keyword"]),
            models.Index(fields=["user_id", "preference_type", "period_key"]),
            models.Index(fields=["message"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.normalized_keyword}:{self.preference_type}"


class PreferenceKeywordSummary(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(db_index=True)
    period_type = models.CharField(max_length=20, db_index=True)
    period_key = models.CharField(max_length=20, db_index=True)
    reflected_conversation_count = models.IntegerField(default=0)
    reflected_message_count = models.IntegerField(default=0)
    display_threshold = models.IntegerField(default=5)
    keywords_json = models.TextField(default="[]", blank=True)
    analyzed_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "preference_keyword_summaries"
        ordering = ["-analyzed_at", "-id"]
        indexes = [
            models.Index(fields=["user_id", "period_type", "period_key"]),
            models.Index(fields=["user_id", "analyzed_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.period_type}:{self.period_key}"

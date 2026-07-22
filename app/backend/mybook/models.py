from django.conf import settings
from django.db import models


class DailyBookRecommendation(models.Model):
    """One stable recommendation payload per user and local calendar day."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_book_recommendations",
    )
    recommendation_date = models.DateField()
    payload = models.JSONField(default=dict)
    profile_basis = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "daily_book_recommendations"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recommendation_date"],
                name="uniq_daily_book_recommendation_user_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "-recommendation_date"],
                name="daily_book_user_date_idx",
            ),
        ]

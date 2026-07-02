from django.conf import settings
from django.db import models


class DailyFortune(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_fortunes',
        blank=True,
        null=True,
    )
    client_id = models.CharField(max_length=64, blank=True, db_index=True)
    reading_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    date = models.DateField(db_index=True)
    topic = models.CharField(max_length=32, default='general')
    title = models.CharField(max_length=120, default='Daily fortune')
    content = models.TextField()
    keyword = models.CharField(max_length=80, blank=True)
    question = models.CharField(max_length=500, blank=True)
    cards = models.JSONField(default=list, blank=True)
    category_results = models.JSONField(default=dict, blank=True)
    disclaimer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-updated_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['client_id', 'date']),
        ]

    def __str__(self):
        owner = self.user_id or self.client_id or 'anonymous'
        return f'{owner} {self.date} {self.title}'


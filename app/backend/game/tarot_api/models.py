from django.db import models


class DailyTarotFortune(models.Model):
    SOURCE_CHOICES = [
        ('rule', 'Rule'),
        ('llm', 'LLM'),
        ('hybrid', 'Hybrid'),
    ]

    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='daily_tarot_fortunes',
    )
    target_date = models.DateField(db_index=True)
    fortune_type = models.CharField(max_length=30, default='daily_major')

    birth_number = models.PositiveSmallIntegerField()
    date_number = models.PositiveSmallIntegerField()
    daily_number = models.PositiveSmallIntegerField()

    card_number = models.IntegerField(db_index=True)
    card_name = models.CharField(max_length=100)
    card_name_ko = models.CharField(max_length=100, blank=True)

    title = models.CharField(max_length=120, default='오늘의 메이저 카드')
    message = models.TextField(blank=True)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='rule')
    model_name = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_tarot_fortunes'
        ordering = ['-target_date', '-updated_at']
        indexes = [
            models.Index(fields=['user', 'target_date', 'fortune_type'], name='daily_tarot_user_id_910d58_idx'),
            models.Index(fields=['card_number', 'target_date'], name='daily_tarot_card_nu_0e62a0_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'target_date', 'fortune_type'],
                name='uniq_daily_tarot_user_date_type',
            ),
        ]

    def __str__(self):
        return f'{self.user_id} {self.target_date} {self.card_name}'

from django.conf import settings
from django.db import models


class CharacterPreference(models.Model):
    CHARACTER_CHOICES = [
        ('otter', 'Otter'),
        ('cat', 'Cat'),
        ('redpanda', 'Red panda'),
        ('bird', 'Bird'),
    ]
    EXPRESSION_CHOICES = [
        ('joy', 'Joy'),
        ('anger', 'Anger'),
        ('sadness', 'Sadness'),
        ('anxiety', 'Anxiety'),
        ('hurt', 'Hurt'),
        ('panic', 'Panic'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='character_preferences',
        blank=True,
        null=True,
    )
    client_id = models.CharField(max_length=64, blank=True, db_index=True)
    character_id = models.CharField(max_length=24, choices=CHARACTER_CHOICES, default='otter')
    expression_id = models.CharField(max_length=24, choices=EXPRESSION_CHOICES, default='joy')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'updated_at']),
            models.Index(fields=['client_id', 'updated_at']),
        ]

    def __str__(self):
        owner = self.user_id or self.client_id or 'anonymous'
        return f'{owner} {self.character_id}/{self.expression_id}'


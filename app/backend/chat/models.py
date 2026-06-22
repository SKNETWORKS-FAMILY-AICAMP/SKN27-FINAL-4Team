from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    CHARACTER_CHOICES = [
        ('haeon', '해온'),
        ('greung', '그릉'),
        ('dalkong', '달콩'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True,
    )
    character = models.CharField(max_length=10, choices=CHARACTER_CHOICES, default='haeon')
    is_secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.character}] {self.user} ({self.created_at:%Y-%m-%d})'


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    EMOTION_CHOICES = [
        ('encourage', '응원'),
        ('sad', '속상'),
        ('angry', '화남'),
        ('plan', '계획'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    emotion_label = models.CharField(max_length=20, choices=EMOTION_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

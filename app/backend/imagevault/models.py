from django.conf import settings
from django.db import models


class SavedCardImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_card_images",
    )
    name = models.CharField(max_length=80)
    image_url = models.TextField()
    thumbnail_url = models.TextField(blank=True)
    source = models.CharField(max_length=40, blank=True)
    source_id = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_card_images"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="saved_card_user_created_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.name}"

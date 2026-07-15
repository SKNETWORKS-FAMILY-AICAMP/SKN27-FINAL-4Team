from django.contrib import admin

from .models import SavedCardImage


@admin.register(SavedCardImage)
class SavedCardImageAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "source", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("name", "user__email", "source_id")

from django.contrib import admin

from .models import DailyFortune


@admin.register(DailyFortune)
class DailyFortuneAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'client_id', 'date', 'topic', 'keyword', 'updated_at')
    list_filter = ('topic', 'date')
    search_fields = ('client_id', 'user__email', 'question', 'content')


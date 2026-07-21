from django.contrib import admin

from .models import DailyBookRecommendation


@admin.register(DailyBookRecommendation)
class DailyBookRecommendationAdmin(admin.ModelAdmin):
    list_display = ("user", "recommendation_date", "created_at", "updated_at")
    list_filter = ("recommendation_date",)
    search_fields = ("user__email", "user__nickname")

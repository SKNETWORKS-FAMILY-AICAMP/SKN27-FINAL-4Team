from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'mbti', 'selected_character', 'updated_at')
    search_fields = ('user__email', 'name', 'mbti')

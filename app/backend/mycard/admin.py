from django.contrib import admin

from .models import MyCard


@admin.register(MyCard)
class MyCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'title', 'is_saved', 'created_at')
    list_filter = ('date', 'is_saved', 'style')

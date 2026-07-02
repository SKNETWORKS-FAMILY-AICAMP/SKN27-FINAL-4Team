from django.contrib import admin

from .models import CharacterPreference


@admin.register(CharacterPreference)
class CharacterPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'client_id', 'character_id', 'expression_id', 'updated_at')
    list_filter = ('character_id', 'expression_id')
    search_fields = ('client_id', 'user__email')


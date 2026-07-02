from django.contrib import admin

from .models import OAuthAccount


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    list_display = ('provider', 'provider_user_id', 'email', 'user', 'connected_at')
    search_fields = ('provider_user_id', 'email', 'user__email', 'user__nickname')
    list_filter = ('provider',)

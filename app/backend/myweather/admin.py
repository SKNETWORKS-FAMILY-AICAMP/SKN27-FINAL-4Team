from django.contrib import admin

from .models import WeatherPhrasingFilter, WeatherRegion


@admin.register(WeatherRegion)
class WeatherRegionAdmin(admin.ModelAdmin):
    list_display = ("name", "warning_display_name", "mid_land_code", "mid_temp_code")
    search_fields = ("name", "warning_display_name")


@admin.register(WeatherPhrasingFilter)
class WeatherPhrasingFilterAdmin(admin.ModelAdmin):
    list_display = ("source_word", "target_word", "condition_trigger")
    list_filter = ("condition_trigger",)
    search_fields = ("source_word", "target_word")

from django.db import models

class WeatherRegion(models.Model):
    name = models.CharField(max_length=64, unique=True)
    lat = models.FloatField()
    lon = models.FloatField()
    warning_code_prefixes = models.JSONField(default=list, blank=True)
    warning_display_name = models.CharField(max_length=64, blank=True)
    mid_land_code = models.CharField(max_length=32, blank=True)
    mid_temp_code = models.CharField(max_length=32, blank=True)
    aliases = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "weather_regions"
        verbose_name = "날씨 조회 지역"
        verbose_name_plural = "날씨 조회 지역 목록"

    def __str__(self):
        return self.name


class WeatherPhrasingFilter(models.Model):
    source_word = models.CharField(max_length=64, unique=True, verbose_name="기본 단어")
    target_word = models.CharField(max_length=64, verbose_name="순화 단어")
    condition_trigger = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name="기상 조건 트리거(맑음 등)",
        db_index=True
    )

    class Meta:
        db_table = "weather_phrasing_filters"
        verbose_name = "날씨 순화 필터"
        verbose_name_plural = "날씨 순화 필터 목록"

    def __str__(self):
        return f"{self.source_word} -> {self.target_word}"


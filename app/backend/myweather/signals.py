from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import WeatherRegion
from .service.region_service import clear_db_regions_cache


@receiver(post_save, sender=WeatherRegion)
@receiver(post_delete, sender=WeatherRegion)
def invalidate_weather_region_cache(**kwargs):
    """운영 중 지역 설정 변경을 다음 요청부터 즉시 반영한다."""
    clear_db_regions_cache()

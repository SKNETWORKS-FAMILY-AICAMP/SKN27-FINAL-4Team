from django.urls import path

from .views import create_tarot_reading, daily_major_fortune


urlpatterns = [
    path('daily-major/', daily_major_fortune),
    path('readings/', create_tarot_reading),
]

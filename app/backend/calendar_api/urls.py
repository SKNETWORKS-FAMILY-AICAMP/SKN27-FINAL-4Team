from django.urls import path

from .views import get_calendar_day, get_calendar_month


urlpatterns = [
    path('month/', get_calendar_month),
    path('day/', get_calendar_day),
]


from django.urls import path

from . import views


urlpatterns = [
    path("current/", views.current_weather, name="myweather-current"),
]

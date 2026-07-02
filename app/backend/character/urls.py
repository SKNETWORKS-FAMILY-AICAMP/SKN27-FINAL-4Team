from django.urls import path

from .views import character_preference


urlpatterns = [
    path('preference/', character_preference),
]


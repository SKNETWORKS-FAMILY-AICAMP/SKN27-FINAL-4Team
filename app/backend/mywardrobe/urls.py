from django.urls import path

from . import views


urlpatterns = [
    path("recommendation/", views.wardrobe_recommendation, name="mywardrobe-recommendation"),
]

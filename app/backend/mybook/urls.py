from django.urls import path
from . import views

urlpatterns = [
    path("recommendation/", views.book_recommendation, name="mybook-recommendation"),
]

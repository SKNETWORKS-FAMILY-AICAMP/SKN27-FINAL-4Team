from django.urls import path

from . import views


urlpatterns = [
    path('monthly-demo/', views.monthly_demo, name='mbti-monthly-demo'),
]

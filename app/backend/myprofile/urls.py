from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_detail, name='myprofile-detail'),
    path('today-emotion/', views.today_emotion_summary, name='myprofile-today-emotion'),
]

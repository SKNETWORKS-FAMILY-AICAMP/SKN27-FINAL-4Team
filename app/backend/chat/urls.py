from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.session_list),
    path('sessions/create/', views.create_session),
    path('sessions/<int:session_id>/messages/', views.send_message),
]

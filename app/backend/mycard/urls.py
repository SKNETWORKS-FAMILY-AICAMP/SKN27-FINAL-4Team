from django.urls import path

from . import views


urlpatterns = [
    path('bootstrap/', views.bootstrap),
    path('generate/', views.generate),
    path('<int:card_id>/save/', views.save),
]

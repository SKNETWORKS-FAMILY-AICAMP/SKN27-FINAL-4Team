from django.urls import path

from . import views


urlpatterns = [
    path('analyze/', views.analyze_view),
    path('analyses/<uuid:analysis_id>/', views.analysis_detail),
    path('analyses/<uuid:analysis_id>/scene/', views.scene_preview),
    path('scenes/<uuid:scene_id>/generate/', views.generate_view),
    path('jobs/<uuid:job_id>/', views.job_detail),
    path('today/', views.today_card),
    path('today/reset/', views.reset_today_usage),
    path('<uuid:card_id>/', views.card_detail),
    path('<uuid:card_id>/feedback/', views.card_feedback),
]

from django.urls import path

from . import views

urlpatterns = [
    path('checkin/bootstrap/', views.bootstrap),
    path('checkin/', views.create_checkin),
    path('checkin/today/', views.today),
    path('checkin/<int:checkin_id>/reflection/', views.save_reflection),
    path('checkin/<int:checkin_id>/restart/', views.restart),
    path('checkin/<int:checkin_id>/cause/', views.save_cause),
    path('checkin/<int:checkin_id>/need/', views.save_need),
    path('checkin/<int:checkin_id>/recommendations/', views.recommendations),
    path('checkin/<int:checkin_id>/complete/', views.complete),
    path('checkin/<int:checkin_id>/feedback/', views.feedback),
    path('insights/weekly/current/', views.weekly_current),
]

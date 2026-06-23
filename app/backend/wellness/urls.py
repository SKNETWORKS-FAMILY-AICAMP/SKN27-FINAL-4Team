from django.urls import path
from . import views

urlpatterns = [
    path('reports/', views.report_list),
    path('reports/today/', views.today_report),
]

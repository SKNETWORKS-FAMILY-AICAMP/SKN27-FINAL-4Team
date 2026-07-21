from django.urls import include, path
from . import views

urlpatterns = [
    path('reports/', views.report_list),
    path('reports/today/', views.today_report),
    path('memory/', include('memorystorage.urls')),
]

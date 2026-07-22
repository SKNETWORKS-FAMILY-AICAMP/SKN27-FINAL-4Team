from django.urls import path
from .views import MindReportGenerateAPIView

app_name = 'mindreport'

urlpatterns = [
    path('generate/', MindReportGenerateAPIView.as_view(), name='generate_report'),
]

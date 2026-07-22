from django.urls import path

from . import views


urlpatterns = [
    path('monthly-demo/', views.monthly_demo, name='mbti-monthly-demo'),
    path('monthly-analysis/', views.request_monthly_analysis, name='mbti-monthly-analysis'),
    path('onboarding/', views.set_onboarding_mbti, name='mbti-onboarding'),
    path('mock-qna/question/', views.get_mock_question, name='mbti-mock-question'),
    path('mock-qna/answer/', views.save_mock_answer, name='mbti-mock-answer'),
    path('mock-qna/reset/', views.reset_mock_qna, name='mbti-mock-reset'),
]

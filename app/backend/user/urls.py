from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register),
    path('login/', views.login_view),
    path('me/', views.current_user),
    path('social-login/', views.social_login_mock),
    path('social-login/providers/', views.social_login_providers),
    path('social-login/<str:provider>/url/', views.social_login_url),
    path('social-login/<str:provider>/callback/', views.social_login_callback),
    path('logout/', views.logout_view),
    path('profile/', views.profile),
]

# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    # GET /api/mymemory/memories/ & DELETE /api/mymemory/memories/<memory_id>/
    path('memories/', views.memory_vault_list, name='memory-vault-list'),
    path('memories/<str:memory_id>/', views.memory_vault_delete, name='memory-vault-delete'),
    
    # GET /api/mypage/memory/ & DELETE /api/mypage/memory/<memory_id>/
    path('', views.memory_vault_list, name='memory-vault-list-root'),
    path('<str:memory_id>/', views.memory_vault_delete, name='memory-vault-delete-root'),
]

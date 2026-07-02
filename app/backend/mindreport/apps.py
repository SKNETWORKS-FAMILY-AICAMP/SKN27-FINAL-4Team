"""
기능: mindreport 앱의 기본 환경설정(앱 이름, 고유 ID 속성 등)을 관리하는 파일입니다.
"""
from django.apps import AppConfig

class MindreportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mindreport'

from django.apps import AppConfig


class MbtiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mbti'

    def ready(self):
        from mbti.services.runtime import start_background_service

        start_background_service()

from django.apps import AppConfig


class MyweatherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myweather'

    def ready(self):
        from . import checks  # noqa: F401
        from . import signals  # noqa: F401

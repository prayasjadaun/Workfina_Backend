from django.apps import AppConfig


class RecruitersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recruiters'

    def ready(self):
        import apps.recruiters.signals

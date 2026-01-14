from django.apps import AppConfig
import os


class CandidatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.candidates'

    def ready(self):
        import apps.candidates.signals

        # Start scheduler only in main process (not in migrations/shell)
        if os.environ.get('RUN_MAIN') == 'true':
            from server.scheduler import get_scheduler
            get_scheduler()

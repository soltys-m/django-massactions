from django.apps import AppConfig
from django.conf import settings


class MassActionsConfig(AppConfig):
    name = 'massactions'
    verbose_name = 'Mass actions'

    def ready(self):
        if getattr(settings, 'MASSACTIONS_AUTODISCOVER', True):
            from massactions.registry import autodiscover
            autodiscover()

from django.apps import AppConfig

from massactions.settings import get_autodiscover


class MassActionsConfig(AppConfig):
    name = 'massactions'
    verbose_name = 'Mass actions'

    def ready(self):
        if get_autodiscover():
            from massactions.registry import autodiscover
            autodiscover()

"""Settings of the massactions app, read from the project settings at call time (``override_settings`` works)."""
from django.conf import settings as django_settings


def get_autodiscover():
    return getattr(django_settings, 'MASSACTIONS_AUTODISCOVER', True)


def get_default_success_url():
    return getattr(django_settings, 'MASSACTIONS_DEFAULT_SUCCESS_URL', '/')

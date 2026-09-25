"""Settings of the massactions app, read from the project settings at call time (``override_settings`` works)."""
from django.conf import settings as django_settings


def get_autodiscover():
    return getattr(django_settings, 'MASSACTIONS_AUTODISCOVER', True)


def get_default_success_url():
    return getattr(django_settings, 'MASSACTIONS_DEFAULT_SUCCESS_URL', '/')


def get_selection_max_age():
    """Seconds a signed selection stays valid; the list page sets the cookie to expire after one hour as well."""
    return getattr(django_settings, 'MASSACTIONS_SELECTION_MAX_AGE', 3600)

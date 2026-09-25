from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import autodiscover_modules

from massactions.settings import get_default_success_url


class MassActionConfig:
    """
    Declares how mass actions behave for one list of objects.

    Subclass it, set ``model`` and register the subclass with ``@register`` in a
    ``massactions.py`` module of your app (discovered automatically, like ``admin.py``).
    Only registered keys are reachable from the mass action views: the ``key`` is the
    only thing the client sends, everything else (queryset, filter, permissions,
    forms) is resolved from the config on the server.
    """
    model = None
    key = None                       # identifier used in URLs and in the selection cookie; defaults to model name
    actions = ['delete']             # action names rendered in the menu ('update', 'delete' are built in)
    update_fields = []               # [{'field_name', 'field_name_localized', 'localized_action', 'choices'?}, ...]
    filter_class = None              # optional django-filter FilterSet applied with the list's query string
    update_form_class = None         # optional BSModalMassUpdateForm subclass used by the update action
    permission_map = {'update': 'change'}

    def __init__(self):
        if self.model is None:
            raise ImproperlyConfigured('%s.model must be set.' % type(self).__name__)
        if self.key is None:
            self.key = self.model._meta.object_name

    @property
    def opts(self):
        return self.model._meta

    # -- querysets ---------------------------------------------------------------------------------------------------

    def get_queryset(self, request):
        """Objects the current user may see in the list. Scope by tenant/ownership here."""
        return self.model._default_manager.all()

    def filter_queryset(self, request, queryset, data):
        """Apply the list filter so 'select all' respects what the user was looking at."""
        if self.filter_class is None or not data:
            return queryset
        return self.filter_class(data, queryset=queryset).qs

    def restrict_queryset(self, request, queryset, action):
        """Objects of the selection the user may run ``action`` on. The rest is shown as 'not allowed'."""
        return queryset

    # -- permissions -------------------------------------------------------------------------------------------------

    def get_permission_required(self, action):
        codename = self.permission_map.get(action, action)
        return '%s.%s_%s' % (self.opts.app_label, codename, self.opts.model_name)

    def has_permission(self, request, action):
        """Extra check on top of Django permissions (e.g. account flags, plan quotas)."""
        return True

    # -- update action -----------------------------------------------------------------------------------------------

    def get_update_field(self, field_name):
        if not field_name:
            return None
        for field in self.update_fields:
            if field.get('field_name') == field_name:
                return field
        return None

    def get_update_form_class(self, field_name):
        return self.update_form_class

    def update_object(self, request, obj, values):
        """Apply the cleaned form values to one object. Override for special save semantics."""
        for name, value in values.items():
            setattr(obj, name, value)
        obj.save()

    # -- delete action -----------------------------------------------------------------------------------------------

    def get_related_list_url(self, request, model, ids):
        """
        URL of a list showing the given objects of ``model`` (protected related objects that block a delete).
        Return ``None`` to render them as plain text.
        """
        return None

    # -- misc --------------------------------------------------------------------------------------------------------

    def get_success_url(self, request):
        """Fallback redirect target when ``back_url`` is missing or points to another host."""
        return get_default_success_url()


class MassActionRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, config_class):
        if not (isinstance(config_class, type) and issubclass(config_class, MassActionConfig)):
            raise ImproperlyConfigured('register() expects a MassActionConfig subclass, got %r.' % (config_class,))

        config = config_class()
        existing = self._registry.get(config.key)

        if existing is not None and type(existing) is not config_class:
            raise ImproperlyConfigured('Mass action key %r is already registered by %s.'
                                       % (config.key, type(existing).__name__))

        self._registry[config.key] = config
        return config_class

    def unregister(self, key):
        self._registry.pop(key, None)

    def get(self, key):
        if not key:
            return None
        return self._registry.get(key)

    def resolve(self, value):
        """Accept a key, a config class or a config instance and return the registered instance."""
        if isinstance(value, MassActionConfig):
            return value

        if isinstance(value, type) and issubclass(value, MassActionConfig):
            for config in self._registry.values():
                if type(config) is value:
                    return config
            raise ImproperlyConfigured('%s is not registered. Decorate it with @massactions.registry.register.'
                                       % value.__name__)

        config = self.get(value)

        if config is None:
            raise ImproperlyConfigured('Unknown mass action config %r. Registered keys: %s'
                                       % (value, ', '.join(sorted(self._registry)) or '(none)'))
        return config

    def keys(self):
        return list(self._registry)

    def __contains__(self, key):
        return key in self._registry

    def __iter__(self):
        return iter(self._registry.values())


registry = MassActionRegistry()
register = registry.register


def autodiscover():
    autodiscover_modules('massactions', register_to=registry)

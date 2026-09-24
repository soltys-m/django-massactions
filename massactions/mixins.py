from django.db.models import QuerySet

from massactions.registry import registry


class MassActionListViewMixin:
    """
    Add ``mass_action_context`` to a list view so ``massactions/mass_action.html`` can be included.
    ``mass_action_config`` is the registered key, the config class or a config instance.
    """
    mass_action_config = None

    def get_mass_action_config(self):
        return registry.resolve(self.mass_action_config)

    def get_mass_actions(self, config):
        """Hook to add or remove actions per request (e.g. by user plan). Return a new list."""
        return list(config.actions)

    def get_mass_action_items_count(self, context):
        """Size of the whole (filtered) list, not only of the current page."""
        paginator = context.get('paginator')

        if paginator is not None:
            return paginator.count

        object_list = context.get('object_list')

        if object_list is None:
            return 0

        if isinstance(object_list, QuerySet):
            return object_list.count()

        return len(object_list)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.get_mass_action_config()
        context['mass_action_context'] = {
            'key': config.key,
            'config': config,
            'actions': self.get_mass_actions(config),
            'update_fields': config.update_fields,
            'items_count': self.get_mass_action_items_count(context),
            'model_name': config.opts.object_name,
            'app_label': config.opts.app_label,
        }
        return context

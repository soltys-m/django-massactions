import math

from django import template
from django.db.models import QuerySet

from massactions.registry import MassActionConfig

register = template.Library()


class _Defaults(MassActionConfig):
    """Unregistered config lending its default hooks to includes that have no config in the context."""
    model = object
    key = '-'


DEFAULTS = _Defaults()


@register.simple_tag
def massaction_object_listing(object_list, config=None, limit=None, columns=1):
    """
    Objects for ``mass_action_modal_object_list.html``:
    ``{'objects': [(label, url), ...], 'columns': [[(label, url), ...], ...], 'more': int}``.

    ``config`` supplies ``get_object_label()`` / ``get_object_url()`` / ``modal_object_limit``; without it
    the ``MassActionConfig`` defaults apply (``str(obj)``, ``get_absolute_url()``, 100), so the template can
    be included on project pages that have no config in their context. ``columns`` splits the objects into
    that many even chunks in reading order (top to bottom, then the next column).
    """
    if not isinstance(config, MassActionConfig):
        config = DEFAULTS

    if limit in (None, ''):
        limit = config.modal_object_limit

    limit = int(limit)
    columns = max(int(columns or 1), 1)

    if isinstance(object_list, QuerySet):
        total = object_list.count()
        objects = object_list[:limit] if limit else object_list
    else:
        objects = list(object_list)
        total = len(objects)
        if limit:
            objects = objects[:limit]

    items = [(config.get_object_label(obj), config.get_object_url(obj)) for obj in objects]
    size = math.ceil(len(items) / columns) if items else 0

    return {
        'objects': items,
        'columns': [items[start:start + size] for start in range(0, len(items), size)] if size else [],
        'more': max(total - limit, 0) if limit else 0,
    }

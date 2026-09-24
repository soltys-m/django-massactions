# Configuration

## Registering a config

Create `massactions.py` in the app that owns the list and register one `MassActionConfig` per list:

```python
from massactions.registry import MassActionConfig, register
from .filters import OrderFilter
from .models import Order


@register
class OrderMassActions(MassActionConfig):
    model = Order
    key = 'Order'
    actions = ['update', 'delete']
    update_fields = [
        {'field_name': 'status', 'field_name_localized': 'Status',
         'localized_action': 'Update status', 'choices': Order.STATUS},
    ]
    filter_class = OrderFilter

    def get_queryset(self, request):
        return Order.objects.filter(workspace=request.user.workspace)
```

The modules are imported on startup (`AppConfig.ready()` → `autodiscover_modules('massactions')`).
Registering two configs with the same key raises `ImproperlyConfigured`; registering the same class
twice is a no-op.

One model can have several configs with different keys (for example `Customer` and `Carrier` on a
`Company` model, or `Driver` on the user model). The key is used in URLs and as part of the cookie and
`sessionStorage` names, so keep it stable.

## Attributes

| Attribute | Default | Purpose |
|---|---|---|
| `model` | – | Required. |
| `key` | `model._meta.object_name` | Identifier in URLs and cookie names. |
| `actions` | `['delete']` | Action names rendered in the menu. `update` and `delete` are built in. |
| `update_fields` | `[]` | Fields offered by the update action (see below). |
| `filter_class` | `None` | django-filter `FilterSet` applied with the query string of `back_url`, so "select all" acts on the filtered list. |
| `update_form_class` | `None` | `BSModalMassUpdateForm` subclass for the update action. |
| `permission_map` | `{'update': 'change'}` | Action name → permission codename prefix. |

`update_fields` entries are dicts with:

* `field_name` – model field to update,
* `field_name_localized` – label used in the confirmation message,
* `localized_action` – menu label,
* `choices` (optional) – iterable of `(value, label)`; renders a submenu and the chosen value is validated
  against it. Without `choices` the form has to provide the inputs (custom form).

## Hooks

| Hook | Called | Default |
|---|---|---|
| `get_queryset(request)` | first, for every action | `model._default_manager.all()` – **override in multi-tenant projects** |
| `filter_queryset(request, queryset, data)` | when `back_url` has a query string | `filter_class(data, queryset=queryset).qs` |
| `restrict_queryset(request, queryset, action)` | after the selection is applied | `queryset` unchanged; the difference to the selection is shown as "not allowed" |
| `has_permission(request, action)` | with Django's permission check | `True` |
| `get_permission_required(action)` | before anything else | `'<app_label>.<codename>_<model_name>'` with `permission_map` |
| `get_update_form_class(field_name)` | update action | `update_form_class` |
| `update_object(request, obj, values)` | update action, per object | `setattr` for every value, then `obj.save()` |
| `get_related_list_url(request, model, ids)` | delete blocked by protected objects | `None` (objects listed as text) |
| `get_success_url(request)` | when `back_url` is missing or external | `MASSACTIONS_DEFAULT_SUCCESS_URL` |

An explicit `permission_required` on a view wins over `get_permission_required()`.

## The list view

```python
from django.views.generic import ListView
from massactions.mixins import MassActionListViewMixin


class OrderListView(MassActionListViewMixin, ListView):
    model = Order
    mass_action_config = 'Order'      # key, config class or instance
    paginate_by = 50
```

The mixin adds `mass_action_context` to the template context:

| Key | Value |
|---|---|
| `key` | config key |
| `config` | the config instance |
| `actions` | result of `get_mass_actions(config)`; override it to add or remove actions per request |
| `update_fields` | `config.update_fields` |
| `items_count` | size of the whole (filtered) list, taken from the paginator when present |
| `model_name`, `app_label` | of `config.model` |

Override `get_mass_action_items_count(context)` if the count cannot be derived from the context.

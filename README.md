# django-massactions

[![tests](https://github.com/soltys-m/django-massactions/actions/workflows/tests.yml/badge.svg)](https://github.com/soltys-m/django-massactions/actions/workflows/tests.yml)

Mass (bulk) actions for Django list views: users select rows with checkboxes (or "select all"
across pages), pick an action from a dropdown and confirm it in a Bootstrap modal (Bootstrap 4 and 5). Built-in
actions: **delete** and **update a field**. Custom actions plug into the same selection mechanism.

## How it works

1. A list view mixes in `MassActionListViewMixin` and includes `massactions/mass_action.html`
   (the action bar) and `massactions/mass_action_checkbox.html` (one per row).
2. The selection lives in `sessionStorage` on the client (`ids` + `selectAll` flag + the current filter).
3. When the user picks an action, the page posts the selection to `massactions:encrypt`, stores the
   returned **signed** value (`django.core.signing`, one hour) in a cookie and opens the action URL in a modal.
4. The action view resolves everything from a **registered config** (`?key=...`): the queryset the
   user may see, the list filter (so "select all" respects the filtered list), the permission and
   the per-action restriction. The client never sends model names, queryset methods or form classes.
5. The modal submits its form with one AJAX POST. Validation errors come back as the form and are shown in
   the modal again; a finished action answers `{"redirect": back_url}` and sets the cookie to `True`, which
   makes the list page reset the stored selection.

## Requirements

* Django >= 4.2, django-crispy-forms >= 1.13 (1.x and 2.x), django-bootstrap-modal-forms >= 2.2 (2.x and 3.x).
  The crispy template pack of your Bootstrap version: `crispy-bootstrap5` (extra `[bootstrap5]`)
  or, for Bootstrap 4 with crispy-forms 2.x, `crispy-bootstrap4` (extra `[bootstrap4]`; crispy-forms 1.x ships
  the `bootstrap4` pack itself). CI runs the suite on Python 3.10 to 3.12 with Django 4.2, 5.0 and 5.1
  (crispy 2.x stack) and on Django 4.2 with the crispy 1.13 stack.
* Optional: django-filter (for `filter_class`)
* Frontend: jQuery, Bootstrap 4 or 5, Font Awesome (icons) and [js-cookie](https://github.com/js-cookie/js-cookie).
  The modal needs no modal forms plugin; the bundled `massactions/js/jquery.bootstrap.modal.forms.js` is kept
  only for projects that still load it.
* `django.contrib.messages` (success/error messages) and `django.contrib.sessions`.

## Installation

```
pip install django-massactions[bootstrap5]      # or [bootstrap4] with crispy-forms 2.x
```

Until the package is on PyPI, or to pin a specific release from GitHub:

```
django-massactions @ git+https://github.com/soltys-m/django-massactions.git@v0.1.0
```

```python
INSTALLED_APPS = [
    ...
    'crispy_forms',
    'crispy_bootstrap5',                # 'crispy_bootstrap4' with crispy-forms 2.x; nothing for Bootstrap 4 with crispy-forms 1.x
    'bootstrap_modal_forms',
    'massactions',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'   # 'bootstrap4' on a Bootstrap 4 page
```

```python
# urls.py
urlpatterns = [
    ...
    path('massactions/', include('massactions.urls')),   # namespace "massactions"
]
```

## Quick start

**1. Register a config** in `<your_app>/massactions.py` (discovered automatically on startup,
like `admin.py`):

```python
from massactions.registry import MassActionConfig, register
from .filters import OrderFilter
from .models import Order


@register
class OrderMassActions(MassActionConfig):
    model = Order
    key = 'Order'                                   # used in URLs and the selection cookie
    actions = ['update', 'delete']
    update_fields = [
        {'field_name': 'status', 'field_name_localized': 'Status',
         'localized_action': 'Update status', 'choices': Order.STATUS},
    ]
    filter_class = OrderFilter                      # optional, django-filter FilterSet

    def get_queryset(self, request):
        # everything the user may see in the list; scope by tenant / ownership here
        return Order.objects.filter(workspace=request.user.workspace)

    def restrict_queryset(self, request, queryset, action):
        # subset of the selection the user may run `action` on; the rest is listed as "not allowed"
        if action == 'delete':
            return queryset.filter(is_locked=False)
        return queryset
```

**2. The list view:**

```python
from django.views.generic import ListView
from massactions.mixins import MassActionListViewMixin


class OrderListView(MassActionListViewMixin, ListView):
    model = Order
    mass_action_config = 'Order'                    # key, config class or instance
    paginate_by = 50

    def get_queryset(self):
        self.filter = OrderFilter(self.request.GET, queryset=Order.objects.all())
        return self.filter.qs
```

**3. The template:**

```django
{% include 'massactions/mass_action.html' %}

{% for object in object_list %}
    <tr>
        <td>{% include 'massactions/mass_action_checkbox.html' %}</td>
        <td>{{ object }}</td>
    </tr>
{% endfor %}
```

The action bar renders only when `object_list` is not empty. It needs `request` and `csrf_token`
in the template context (`django.template.context_processors.request`).

## Config reference

| Attribute / hook | Purpose |
|---|---|
| `model` | Required. |
| `key` | Identifier in URLs and cookie names. Defaults to `model._meta.object_name`. One model can have several configs (e.g. `Customer` and `Carrier` on a `Company` model). |
| `actions` | Names rendered in the menu. `update` and `delete` are built in; other names are for your own menu items (see *Custom actions*). |
| `update_fields` | List of dicts: `field_name`, `field_name_localized`, `localized_action`, optional `choices` (renders a submenu; the chosen value is validated against it). |
| `filter_class` | django-filter `FilterSet` applied with the query string of `back_url`. |
| `update_form_class` | `BSModalMassUpdateForm` subclass for the update action (extra inputs, custom layout). |
| `permission_map` | Maps action name to permission codename prefix; default `{'update': 'change'}`. |
| `get_queryset(request)` | Base queryset. **Override this** in multi-tenant projects. |
| `filter_queryset(request, queryset, data)` | Override when your FilterSet needs extra constructor arguments. |
| `restrict_queryset(request, queryset, action)` | Per-action object-level permission. |
| `has_permission(request, action)` | Extra check next to Django permissions (account flags, plan quotas). |
| `get_permission_required(action)` | Default `'<app_label>.<codename>_<model_name>'`. An explicit `permission_required` on the view wins. |
| `get_update_form_class(field_name)` | Per-field form class. |
| `update_object(request, obj, values)` | How the update action applies values to one object (default `setattr` + `save()`). |
| `get_related_list_url(request, model, ids)` | Link for protected related objects that block a delete (default: plain text). |
| `modal_object_limit` | Objects listed in the confirmation modal, the rest is shown as "and N more" (default `100`, `0` lists all). |
| `get_object_label(obj)` / `get_object_url(obj)` | Text and link of one object in the confirmation modal (defaults `str(obj)`, `get_absolute_url()`). |
| `get_success_url(request)` | Fallback redirect when `back_url` is missing or external. |

## Custom actions

Subclass one of the views, set `action`, and add a menu item in your template. The config's
`restrict_queryset()` and `get_permission_required()` receive your action name.

```python
from massactions.views import BSModalMassActionViewMixin
from massactions.forms import BSModalMassActionFormMixin


class BSModalMassArchiveForm(BSModalMassActionFormMixin):
    def get_modal_submit(self):
        return _('Archive')

    def get_modal_title(self, object):
        return _('Archive objects of type: %s') % self.get_verbose_name(object)

    def get_confirmation_message(self, count):
        return ngettext('Archive %(count)d object?', 'Archive %(count)d objects?', count) % {'count': count}


class MassArchiveView(BSModalMassActionViewMixin):
    action = 'archive'                              # permission: <app>.archive_<model>
    form_class = BSModalMassArchiveForm

    def post(self, request, *args, **kwargs):
        count = self.restricted_object_list.update(is_archived=True)
        messages.success(request, _('%d objects archived.') % count)
        return self.finish()                        # redirect back + reset selection
```

```django
{# templates/<app>/mass_action.html #}
{% extends 'massactions/mass_action.html' %}

{% block mass_action_menu_extra %}
    {% if 'archive' in ctx.actions %}
        <a href="#" class="dropdown-item mass-action-{{ ctx.key|slugify }}"
           data-form-url="{% url 'myapp:mass_archive' %}?key={{ ctx.key|urlencode }}&back_url={{ request.get_full_path|urlencode }}">
            {% trans 'Archive' %}
        </a>
    {% endif %}
{% endblock %}
```

Include your template instead of `massactions/mass_action.html`. Available blocks:
`mass_action_bar` (the whole bar), `mass_action_selection`, `mass_action_selected_class`,
`mass_action_button_class`, `mass_action_menu` (the `dropdown-menu` element), `mass_action_menu_items`,
`mass_action_menu_start`, `mass_action_menu_update`, `mass_action_menu_extra`, `mass_action_menu_delete`,
`mass_action_menu_end`, `mass_action_js_extra`. The selection dropdown template takes `button_class`
(default `btn-outline-secondary`).
The modal content template `massactions/mass_action_modal_content.html` has
`mass_action_modal_heading`, `mass_action_modal_not_allowed_heading` and `mass_action_modal_extra`.

Two flavours of menu links are supported by the page script:

* `class="mass-action-<key|slugify>"` with `data-form-url`: stores the selection and opens the URL in the modal.
* `class="mass-action"` with `data-form-url`: stores the selection and redirects to the URL (full page action).
* `class="mass-action-export"` with `data-export-url`: redirects to the URL with the current filter and
  `ids=` / `exclude_ids=` appended (for exports).

Views that are not modals can use `MassActionViewMixin` directly; set `action` or `permission_required`.
`window.massActions[key].resetSelection()` is available to project scripts.

When a modal has been loaded and shown, and again whenever its form is re-rendered with validation errors, the
page triggers `massactions:modal-shown` on `document` with the modal element, the config key and the form URL,
so project scripts can initialise widgets in the form (date pickers, select2, ...):

```js
$(document).on('massactions:modal-shown', function (event, modal, key, formUrl) {
    init_date_and_time_pickers($(modal));
});
```

## Bootstrap 4 and 5

The templates carry both attribute sets side by side (`data-toggle="dropdown" data-bs-toggle="dropdown"`,
`text-end text-right`, `me-2 mr-2`, ...); each Bootstrap version ignores the other's. The only markup that
differs, the close button of the modal header, follows `CRISPY_TEMPLATE_PACK` (`bootstrap4` renders the
`close` button, anything else `btn-close`; with crispy-forms 2.x the `bootstrap4` pack comes from the
`crispy-bootstrap4` package). The modal container is appended to `<body>` by the helper script (an existing
`#modal` element on the page is reused and has to contain a `.crispy-modal-content` element), so
`massactions/mass_action.html` can be included anywhere, also inside an existing dropdown menu:

```django
{% extends 'massactions/mass_action.html' %}

{% block mass_action_bar %}
    {% block mass_action_menu_items %}{{ block.super }}{% endblock %}
{% endblock %}
```

renders only the menu items (`<a class="dropdown-item">`); include the selection dropdown with
`is_table=True` in the table header.

## Views

* `MassDeleteView` (`massactions:mass_delete`): shows the objects to delete, the ones the user may
  not delete and protected related objects (`on_delete=PROTECT`); override `perform_delete()`.
* `MassUpdateFieldView` (`massactions:mass_update`): `?field_name=` must be declared in
  `update_fields`, `?field_name_value=` must be one of its `choices`. Objects are saved one by one
  (signals, `auto_now`); override `perform_update()` for `queryset.update()`.
* `EncryptSelectionView` (`massactions:encrypt`): POST only, login required; validates the posted JSON and
  returns it signed (the name is historical, nothing is encrypted).

Views answer with a small modal (`massactions/helpers/modal_content.html`) when the user has no
permission, is not logged in or has nothing selected.

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `MASSACTIONS_AUTODISCOVER` | `True` | Import `massactions.py` from every installed app on startup. |
| `MASSACTIONS_DEFAULT_SUCCESS_URL` | `'/'` | Redirect target when `back_url` is missing or points to another host. |
| `MASSACTIONS_SELECTION_MAX_AGE` | `3600` | Seconds a signed selection is accepted (the page lets the cookie expire after one hour as well). |

## Security notes

* Only registered keys are reachable; the model, queryset, filter and form are never taken from the request.
* `back_url` is only followed when it points to the current host.
* The selection cookie is signed with `SECRET_KEY` (`django.core.signing`, salted, expiring), so it cannot be
  tampered with or replayed after an hour. It is not encrypted: the payload is compressed JSON with ids and
  flags. `get_queryset()` / `restrict_queryset()` remain the authorization boundary for every id.
* Object names are inserted into the modal as escaped HTML, not re-parsed as templates.

## Translations

The package ships message catalogs in `massactions/locale/` (Slovak, Czech and Polish complete; Hungarian and
Romanian nearly complete; German only started; apart from Slovak they are not reviewed by native speakers).
Regenerate with
`cd massactions && django-admin makemessages -a --ignore='tests/*' --no-location` and compile with
`django-admin compilemessages` (or `msgfmt`). Projects that translated these strings before can drop them
from their own catalogs; Django finds the app catalog automatically.

## Tests

```
pip install -r requirements-test.txt
pytest                       # or: python runtests.py
```

GitHub Actions (`.github/workflows/tests.yml`) runs the suite for every push to `main` and every pull
request across the supported Django/crispy combinations, plus `pyflakes` and a package build check.

## Documentation

Full documentation lives in `docs/` (mkdocs): installation, configuration reference, templates and
JavaScript, custom actions, migration from an inline implementation and security notes.

## License

GPLv2, see `LICENSE`.

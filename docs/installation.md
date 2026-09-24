# Installation

```
pip install django-massactions
```

Requirements: Django ≥ 3.2, django-crispy-forms ≥ 1.14 (2.x supported, less tested), crispy-bootstrap5,
django-bootstrap-modal-forms ≥ 2.2, pycryptodome. django-filter is optional (`filter_class`).

## Settings

```python
INSTALLED_APPS = [
    ...
    'django.contrib.messages',      # success / error messages
    'django.contrib.sessions',
    'crispy_forms',
    'crispy_bootstrap5',
    'bootstrap_modal_forms',
    'massactions',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

TEMPLATES = [{
    ...
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',   # required: request and csrf_token in templates
        ...
    ]},
}]
```

| Setting | Default | Purpose |
|---|---|---|
| `MASSACTIONS_AUTODISCOVER` | `True` | Import `massactions.py` from every installed app on startup. |
| `MASSACTIONS_DEFAULT_SUCCESS_URL` | `'/'` | Redirect target when `back_url` is missing or points to another host. |

## URLs

```python
urlpatterns = [
    ...
    path('massactions/', include('massactions.urls')),
]
```

This registers the namespace `massactions` with `mass_delete`, `mass_update` and `encrypt`. The templates
reverse these names, so the namespace must be `massactions` (the default from `app_name`).

## Frontend

The templates expect on the page: jQuery, Bootstrap 5 (dropdown, collapse, modal), Font Awesome icons,
[js-cookie](https://github.com/js-cookie/js-cookie) (`Cookies`) and the bundled fork of the
django-bootstrap-modal-forms plugin:

```django
<script src="{% static 'massactions/js/jquery.bootstrap.modal.forms.js' %}"></script>
```

Use it **instead of** the plugin's own `jquery.bootstrap.modal.forms.js`; the fork adds `showModal()`
and the `initOnClick` option that the action bar relies on.

# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

`django-massactions` is a reusable Django app: bulk actions on list views (checkbox selection incl.
"select all" across pages, action dropdown, confirmation in a Bootstrap 5 modal, built-in delete and
field update). It is distributed as a package, not a standalone project.

## Commands

```bash
pip install -r requirements-test.txt
python runtests.py                       # Django test runner, settings: massactions.tests.settings
pytest                                   # same suite via pytest-django (pytest.ini)
python runtests.py massactions.tests.test_views.DeleteTests
python -m build                          # sdist + wheel (templates and static included, tests excluded)
```

Tests use an in-memory SQLite database and the test app `massactions.tests` (label `massactions_tests`).
CI: `.github/workflows/tests.yml` (Python 3.10-3.12 x Django 4.2/5.0/5.1 with the crispy 2.x stack, plus Django 4.2 with crispy 1.x; pyflakes; build).

## Architecture

* `registry.py` – `MassActionConfig` (one per list: model, key, actions, queryset/filter/permission
  hooks) and the `registry`. Configs live in `<app>/massactions.py` modules and are discovered from
  `apps.py` (`autodiscover_modules('massactions')`). The **key** is the only identifier the client sends.
* `views.py` – `MassActionViewMixin` resolves the config from `?key=`, parses the selection cookie,
  builds `restricted_object_list` / `not_allowed_object_list`. `BSModalMassActionViewMixin` adds the
  modal form handling; `MassDeleteView`, `MassUpdateFieldView` and `EncryptSelectionView` are routed in `urls.py`.
* `forms.py` – crispy layout for the modal (`MassActionModalContentLayout`), `BSModalMassActionFormMixin`
  and the delete/update forms. `RawHTML` inserts rendered HTML without re-parsing it as a template.
* `mixins.py` – `MassActionListViewMixin` puts `mass_action_context` into the list view context.
* `helpers.py` – selection cookie (AES obfuscation, key travels with the value), parsing and cleaning.
* `templates/massactions/` – action bar (`mass_action.html`, contains the selection JS), modal helper,
  modal content. Projects extend them with `{% extends %}` and the documented blocks.
* `static/massactions/js/` – fork of the django-bootstrap-modal-forms plugin (`showModal`, `initOnClick`).

## Conventions

* Anything that comes from the request (`key`, `field_name`, `field_name_value`, `back_url`) is validated
  against the config; never resolve models, querysets, filters or forms from request data.
* Keep the webapp-agnostic: no project template tags, URL namespaces or queryset methods in the library.
  Project specifics go into config hooks (`get_queryset`, `restrict_queryset`, `has_permission`, ...).
* Every behaviour change needs a test in `massactions/tests/`.
* Docs: `README.md` (overview and reference) and `docs/` (mkdocs). Update both when hooks or blocks change.

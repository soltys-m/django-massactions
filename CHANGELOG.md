# Changelog

## 0.1.0 (unreleased)

First usable release, extracted from the transportly webapp.

* Registry of `MassActionConfig` classes; views resolve model, queryset, filter, permissions and forms
  from the registered `key` instead of request parameters.
* `MassDeleteView`, `MassUpdateFieldView`, `EncryptSelectionView` with own URL namespace `massactions`.
* `MassActionListViewMixin` with `get_mass_actions()` hook and paginator based item count.
* Config hooks: `get_queryset`, `filter_queryset`, `restrict_queryset`, `has_permission`,
  `get_permission_required`, `get_update_form_class`, `update_object`, `get_related_list_url`, `get_success_url`.
* Hardening: `back_url` host check, `field_name`/`field_name_value` validation, invalid cookies and stale ids
  handled, object names no longer parsed as templates, invalid pks dropped.
* Templates with override blocks, bundled fork of the modal forms JS plugin.
* Bootstrap 4 and 5 with one set of templates: the markup carries both attribute sets, the modal close button
  follows `CRISPY_TEMPLATE_PACK`, the choices submenu is toggled by the page script, the menu-driven update
  field is hidden with `d-none`. The modal container is appended to `<body>` by the helper script and the bar
  got the blocks `mass_action_bar`, `mass_action_menu` and `mass_action_menu_items`, so a project can render
  only the menu items into its own dropdown. Modal close buttons use `data-dismiss`/`data-bs-dismiss="modal"`
  instead of the `modal_id` value.
* App settings (`MASSACTIONS_AUTODISCOVER`, `MASSACTIONS_DEFAULT_SUCCESS_URL`) are read through `massactions.settings`.
* Dependencies: django-crispy-forms >= 1.13; the crispy template pack is an extra (`[bootstrap5]`, `[bootstrap4]`)
  instead of a hard dependency on crispy-bootstrap5.
* `massactions:modal-shown` document event after a modal is shown; message catalogs (`massactions/locale/`).
* Test suite (`python runtests.py` / `pytest`) and GitHub Actions workflow (Python 3.10-3.12, Django 4.2/5.0/5.1, crispy-forms 1.x and 2.x, pyflakes, package build).

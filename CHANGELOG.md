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
* Test suite (`python runtests.py` / `pytest`) and GitHub Actions workflow (Python 3.10-3.12, Django 4.2/5.0/5.1, crispy-forms 1.x and 2.x, pyflakes, package build).

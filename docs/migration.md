# Migrating from an inline implementation

The library replaces the copy of the mass action code that used to live in the transportly webapp.
If your project has that copy, the mapping is:

| Before (inline) | After (library) |
|---|---|
| `mass_action_object_name`, `mass_actions`, `mass_action_update_dict`, `mass_action_qs_method` on the list view | one `MassActionConfig` per list, `mass_action_config = '<key>'` on the view |
| `?model=&app_label=&object_name=&qs_method=&custom_form=&field_name_localized=` in action URLs | `?key=<key>` |
| `restrict_objects_by_user_permission()` with `if object_name == ...` branches | `config.restrict_queryset(request, queryset, action)` |
| `get_required_permission_string()` | `config.get_permission_required(action)` / `permission_map`, or `permission_required` on the view |
| `filter_object_list()` importing `<app>.filters.<Model>Filter` | `config.filter_class` / `filter_queryset()` |
| `MassAction<Object>Form` looked up by name | `config.update_form_class` |
| `bulk_update_field()` | `post()` + `self.finish()` |
| `response.set_cookie(self.user_mass_action_cookie, True)` | `self.finish()` or `massactions.helpers.set_selection_done_cookie()` |
| `helpers/mass_action*.html`, `forms/crispy_modal_form_helper_mass_action.html` | `massactions/...` templates; project template extends `massactions/mass_action.html` |
| `{% url 'manager:mass_delete' %}` | `{% url 'massactions:mass_delete' %}` |
| `{% url 'encrypt_string' %}` API view | `massactions:encrypt` (bundled) |
| `transportly.helpers.encrypt_string` | `massactions.helpers.encrypt_string` |

Keys should equal the former `object_name` (or model name) so that existing `sessionStorage` entries and
the cookie reset after a single delete keep working.

Checklist:

1. `INSTALLED_APPS += ['massactions']`, include `massactions.urls`.
2. Write `massactions.py` per app; move per-model restriction logic into `restrict_queryset()`.
3. Replace the list view attributes with `mass_action_config`.
4. Rebuild custom views on `BSModalMassActionViewMixin` / `MassActionViewMixin` with `action = '...'`.
5. Replace the project templates with overrides of the library templates; update `include` paths.
6. Update tests: request parameter `key` instead of `model`/`app_label`, cookies via
   `massactions.helpers.encrypt_string`.

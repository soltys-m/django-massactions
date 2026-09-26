# django-massactions

Mass (bulk) actions for Django list views.

Users select rows with checkboxes or "select all" (across pages, respecting the active list filter),
choose an action from a dropdown and confirm it in a Bootstrap modal (Bootstrap 4 and 5). The package ships two actions,
**delete** and **update a field**, and the plumbing for your own.

## Flow

```
list page ──(checkbox changes)──► sessionStorage["<key>"] = {ids, selectAll, currentFilter}
   │
   │ click on an action
   ▼
POST massactions:encrypt ──► cookie "<user_id>_<key>" = signed selection (SECRET_KEY, 1 hour)
   │
   ▼
GET  <action url>?key=<key>&back_url=<list url>   ──► modal with the objects and a confirmation
POST <action url>?key=...  (AJAX, once)            ──► errors: the form again, shown in the modal
                                                    ──► done: {"redirect": back_url}, the page goes there,
                                                        cookie "<user_id>_<key>" = "True" resets the selection
```

Everything about *what* is acted upon is resolved on the server from a registered
[`MassActionConfig`](configuration.md): the queryset the user may see, the list filter, the permission
and the per-action restriction. The client only sends the config `key`, the selection and `back_url`.

## Contents

* [Installation](installation.md)
* [Configuration](configuration.md) – `MassActionConfig`, registry, list view mixin
* [Templates and JavaScript](templates.md) – what to include, blocks to override, frontend dependencies
* [Custom actions](custom-actions.md) – views, forms and menu items for your own actions
* [Migrating from an inline implementation](migration.md)
* [Security](security.md)

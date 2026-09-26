# Templates and JavaScript

## What to include

```django
{% include 'massactions/mass_action.html' %}          {# action bar + selection JS + modal container #}

{% for object in object_list %}
    {% include 'massactions/mass_action_checkbox.html' %}   {# uses `object` #}
{% endfor %}
```

The action bar renders only when `object_list` is not empty. Variables understood by the bar:

* `selection_dropdown_disabled` – hide the "Select visible / all / clear" dropdown (for example when the
  list is a table that has its own header dropdown: include
  `massactions/mass_action_selection_dropdown.html` with `is_table=True` there instead),
* `button_class` – CSS class of the selection dropdown button (default `btn-outline-secondary`).

## Bootstrap 4 and 5

One set of templates serves both versions: the markup carries both attribute sets side by side
(`data-toggle="dropdown" data-bs-toggle="dropdown"`, `data-dismiss="modal" data-bs-dismiss="modal"`,
`text-end text-right`, `me-2 mr-2`, `ms-0 ml-0`) and each Bootstrap version ignores the other's. Menu items
are `<a class="dropdown-item">` inside a `<div class="dropdown-menu">`, which both versions support. The
choices submenu is toggled by the page script, because a click inside the menu would close the dropdown.

The only markup that differs is the close button of the modal header (`btn-close` vs. `close`); it follows
`CRISPY_TEMPLATE_PACK`, which the project has to set anyway for the modal body. With crispy-forms 2.x the
`bootstrap4` pack comes from the `crispy-bootstrap4` package.

### Menu items only

The modal container is appended to `<body>` by the helper script (an existing `#modal` element is reused
and has to contain a `.crispy-modal-content` element), so the bar template can be included anywhere. A page that already has an actions dropdown renders just the menu items into it and includes the
selection dropdown with `is_table=True` in the table header:

```django
{# templates/helpers/mass_action.html #}
{% extends 'massactions/mass_action.html' %}

{% block mass_action_bar %}
    {% block mass_action_menu_items %}{{ block.super }}{% endblock %}
{% endblock %}
```

## Overriding

Create a project template that extends the library one and include *that* in your list templates:

```django
{# templates/helpers/mass_action.html #}
{% extends 'massactions/mass_action.html' %}

{% block mass_action_button_class %}btn-outline-primary{% endblock %}

{% block mass_action_menu_extra %}
    {% if 'archive' in ctx.actions %}
        <a href="#" class="dropdown-item mass-action-{{ ctx.key|slugify }}"
           data-form-url="{% url 'myapp:mass_archive' %}?key={{ ctx.key|urlencode }}&back_url={{ request.get_full_path|urlencode }}">
            Archive
        </a>
    {% endif %}
{% endblock %}
```

Inside the blocks `ctx` is `mass_action_context`.

### Blocks of `massactions/mass_action.html`

| Block | Content |
|---|---|
| `mass_action_bar` | the whole bar (selection dropdown, label, actions button and menu) |
| `mass_action_selection` | the selection dropdown (left column) |
| `mass_action_selected_class` | CSS class of the "Number of selected items" label |
| `mass_action_button_class` | CSS class of the "Actions" button |
| `mass_action_menu` | the `dropdown-menu` element with the items |
| `mass_action_menu_items` | the menu items without the menu element |
| `mass_action_menu_start` | first menu items |
| `mass_action_menu_update` | the generated update items |
| `mass_action_menu_extra` | items between update and delete |
| `mass_action_menu_delete` | the delete item |
| `mass_action_menu_end` | items after delete |
| `mass_action_js_extra` | JavaScript appended inside the page script (has access to `resetSelection()`, `getSelection()`) |

### Blocks of `massactions/mass_action_modal_content.html`

`mass_action_modal_heading`, `mass_action_modal_not_allowed_heading`, `mass_action_modal_extra`.
Point a form at your override with `modal_content_template = 'helpers/mass_action_modal_content.html'`
on the form class; `get_modal_content_context()` supplies extra variables.

### The object list

`massactions/mass_action_modal_object_list.html` renders `object_list` inside `<div class="mass-action-items">`
as Bootstrap grid columns (`columns` include variable, default 3; `col-sm-6 col-md`, so they stack on phones), one
object per line, linked when the config's `get_object_url()` returns a URL, labelled by `get_object_label()`, and
cut after `modal_object_limit` objects with an "and N more objects" line. It reads `config` from the context;
without one (for example on a project page that includes it with `object_list=...`) the defaults apply:
`str(obj)`, `get_absolute_url()`, 100 objects. The modal content template uses two columns when the "not allowed"
list is shown next to it and the modal container has `modal-dialog-scrollable`, so long lists scroll inside the
modal. The template tag behind it, `{% massaction_object_listing object_list config=config limit=limit
columns=3 as listing %}` (`{% load massactions %}`), returns `objects`, `columns` and `more` for your own markup.

## Menu link flavours

The page script binds three kinds of links:

| Class | Attribute | Behaviour |
|---|---|---|
| `mass-action-<key slug>` | `data-form-url` | store the selection, open the URL in the modal |
| `mass-action` | `data-form-url` | store the selection, redirect to the URL (full page action) |
| `mass-action-export` | `data-export-url` | redirect to the URL with the current filter and `ids=` / `exclude_ids=` appended |

`window.massActions[key]` exposes `getSelection()` and `resetSelection()` to project scripts.

## Modal shown event

After a confirmation modal has been loaded and shown, `massactions:modal-shown` is triggered on `document`
with `(event, modal, key, formUrl)`. Use it to initialise widgets rendered inside the form:

```js
$(document).on('massactions:modal-shown', function (event, modal, key, formUrl) {
    init_date_and_time_pickers($(modal));
});
```

Widgets that ship their own inline `<script>` (django-tempus-dominus for example) initialise themselves
when the form HTML is inserted and do not need the event.

## Element ids

`id_mass_actions_btn`, `id_mass_action_delete`, `id_mass_action_selection`,
`id_mass_action_selection_table`, `id_select_visible`, `id_select_all`, `id_clear_all`,
`id_mass_action_checkbox_<pk>` – stable for functional tests.

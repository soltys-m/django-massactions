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

## Overriding

Create a project template that extends the library one and include *that* in your list templates:

```django
{# templates/helpers/mass_action.html #}
{% extends 'massactions/mass_action.html' %}

{% block mass_action_button_class %}btn-outline-primary{% endblock %}

{% block mass_action_menu_extra %}
    {% if 'archive' in ctx.actions %}
        <li>
            <a href="#" class="dropdown-item mass-action-{{ ctx.key|slugify }}"
               data-form-url="{% url 'myapp:mass_archive' %}?key={{ ctx.key|urlencode }}&back_url={{ request.get_full_path|urlencode }}">
                Archive
            </a>
        </li>
    {% endif %}
{% endblock %}
```

Inside the blocks `ctx` is `mass_action_context`.

### Blocks of `massactions/mass_action.html`

| Block | Content |
|---|---|
| `mass_action_selection` | the selection dropdown (left column) |
| `mass_action_selected_class` | CSS class of the "Number of selected items" label |
| `mass_action_button_class` | CSS class of the "Actions" button |
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

## Menu link flavours

The page script binds three kinds of links:

| Class | Attribute | Behaviour |
|---|---|---|
| `mass-action-<key slug>` | `data-form-url` | store the selection, open the URL in the modal |
| `mass-action` | `data-form-url` | store the selection, redirect to the URL (full page action) |
| `mass-action-export` | `data-export-url` | redirect to the URL with the current filter and `ids=` / `exclude_ids=` appended |

`window.massActions[key]` exposes `getSelection()` and `resetSelection()` to project scripts.

## Element ids

`id_mass_actions_btn`, `id_mass_action_delete`, `id_mass_action_selection`,
`id_mass_action_selection_table`, `id_select_visible`, `id_select_all`, `id_clear_all`,
`id_mass_action_checkbox_<pk>` – stable for functional tests.

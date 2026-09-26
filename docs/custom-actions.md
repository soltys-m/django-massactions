# Custom actions

An action is a view that consumes the selection prepared by `MassActionViewMixin`, plus a menu item.

## Modal action

```python
from django.contrib import messages
from django.utils.translation import gettext_lazy as _, ngettext
from massactions.forms import BSModalMassActionFormMixin
from massactions.views import BSModalMassActionViewMixin


class BSModalMassArchiveForm(BSModalMassActionFormMixin):
    def get_modal_submit(self):
        return _('Archive')

    def get_modal_title(self, object):
        return _('Archive objects of type: %s') % self.get_verbose_name(object)

    def get_confirmation_message(self, count):
        return ngettext('Archive %(count)d object?', 'Archive %(count)d objects?', count) % {'count': count}


class MassArchiveView(BSModalMassActionViewMixin):
    action = 'archive'                     # permission <app>.archive_<model> unless permission_required is set
    form_class = BSModalMassArchiveForm

    def post(self, request, *args, **kwargs):
        count = self.restricted_object_list.update(is_archived=True)
        messages.success(request, _('%d objects archived.') % count)
        return self.finish()               # redirect to back_url and reset the stored selection
```

The modal posts the form with AJAX, once. A view with inputs validates them and answers
`self.form_invalid(form)` when they are wrong (the modal shows the errors), otherwise it runs the action and
answers `self.finish()`, which returns `{"redirect": back_url}` to AJAX requests and a redirect otherwise:

```python
    def post(self, request, *args, **kwargs):
        form = self.get_form_class()(request.POST, **self.get_form_kwargs())

        if not form.is_valid():
            return self.form_invalid(form)

        ...
        return self.finish()
```

```python
urlpatterns = [
    path('archive/', MassArchiveView.as_view(), name='mass_archive'),
]
```

Add `'archive'` to the config's `actions` and handle it in `restrict_queryset()` if the objects need an
extra check. The config's `permission_map` can map `'archive'` to another codename.

What the mixin gives you in the view:

| Attribute | Meaning |
|---|---|
| `config` | the resolved `MassActionConfig` |
| `model`, `key` | shortcuts |
| `selection` | `{'ids': [...], 'selectAll': bool, ...}` from the cookie |
| `restricted_object_list` | objects the user may act on |
| `not_allowed_object_list` | selected objects excluded by `restrict_queryset()` |
| `finish(success=True)` | redirect (JSON `{"redirect": url}` for AJAX requests) + reset cookie |
| `is_ajax()` | whether the request came from the modal's AJAX submit |
| `render_modal_message(title, message)` | small modal with a message (modal views) |

## Full page action

Views that are not modals mix `MassActionViewMixin` into an ordinary view (for example a `CreateView`
that pre-fills a form with the selected objects). Use the `mass-action` link class in the menu, so the
page script stores the selection and redirects instead of opening a modal.

```python
class InvoiceForOrdersCreateView(MassActionViewMixin, CreateView):
    action = 'issue-invoice'
    permission_required = 'billing.add_invoice'    # explicit permission wins over the config

    def get_initial(self):
        return {'orders': self.restricted_object_list}
```

## Update forms

`update_fields` entries without `choices` need a form that asks for the values:

```python
from crispy_forms.layout import Div
from massactions.forms import BSModalMassUpdateForm


class MassActionItemForm(BSModalMassUpdateForm):
    note = forms.CharField(required=True)

    def build_form_fields(self):
        return [Div('note')]
```

Set it as `update_form_class` on the config (or return it from `get_update_form_class(field_name)`).
Every field of the form is applied to every selected object through `config.update_object()`.

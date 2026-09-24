from crispy_forms.helper import FormHelper
from crispy_forms.layout import LayoutObject, Layout, Div
from crispy_forms.utils import flatatt, TEMPLATE_PACK
from django.core.exceptions import ValidationError, FieldDoesNotExist, ImproperlyConfigured
from django.template import loader
from django.template.loader import render_to_string
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, ngettext

from bootstrap_modal_forms.forms import BSModalForm


class RawHTML:
    """
    Layout object inserting already rendered HTML verbatim.

    crispy's ``HTML`` re-parses its content as a Django template, which is a template
    injection vector when the content contains user supplied strings (object names).
    """

    def __init__(self, html):
        self.html = html

    def render(self, *args, **kwargs):
        return mark_safe(self.html)


class MassActionModalContentLayout(LayoutObject):
    template = 'massactions/helpers/modal_content.html'

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)
        self.modal_id = kwargs.pop('modal_id', None)
        self.modal_title = kwargs.pop('modal_title', None)
        self.modal_close = kwargs.pop('modal_close', None)
        self.modal_submit = kwargs.pop('modal_submit', None)
        self.modal_message = kwargs.pop('modal_message', None)
        self.modal_body = kwargs.pop('modal_body', None)
        self.template = kwargs.pop('template', self.template)
        self.flat_attrs = flatatt(kwargs)

    def render(self, form, *args, **kwargs):
        template_pack = kwargs.pop('template_pack', TEMPLATE_PACK)

        if len(args) >= 2:
            # django-crispy-forms 1.x: render(form, form_style, context, template_pack=...)
            form_style, context = args[0], args[1]
            fields = self.get_rendered_fields(form, form_style, context, template_pack, **kwargs)
        else:
            # django-crispy-forms 2.x: render(form, context, template_pack=...)
            form_style = None
            context = args[0] if args else kwargs.pop('context')
            fields = self.get_rendered_fields(form, context, template_pack, **kwargs)

        return render_to_string(self.get_template_name(template_pack), {
            'fieldset': self,
            'modal_id': self.modal_id,
            'modal_title': self.modal_title,
            'modal_close': self.modal_close,
            'modal_submit': self.modal_submit,
            'modal_message': self.modal_message,
            'modal_body': self.modal_body,
            'fields': fields,
            'form_style': form_style,
        })


class BSModalMassActionFormMixin(BSModalForm):
    modal_content_template = 'massactions/mass_action_modal_content.html'

    def __init__(self, *args, **kwargs):
        self.object_list = kwargs.pop('object_list')
        self.not_allowed_object_list = kwargs.pop('not_allowed_object_list', None)
        self.action = kwargs.pop('action', None)
        self.config = kwargs.pop('config', None)
        self.request = kwargs.get('request')  # popped again by BSModalForm, needed before super().__init__()

        if self.not_allowed_object_list is None:
            self.not_allowed_object_list = self.object_list.none()

        self.first_object = self.object_list.first() or self.not_allowed_object_list.first()
        self.modal_title = self.get_modal_title(self.first_object)
        self.modal_submit = self.get_modal_submit()
        self.modal_message = self.get_modal_message()
        self.modal_html_content = self.get_modal_html_content()
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = self.get_layout()

    def has_objects(self):
        return self.object_list.exists() or self.not_allowed_object_list.exists()

    def get_verbose_name(self, object):
        if object is not None:
            return object._meta.verbose_name
        return self.object_list.model._meta.verbose_name

    def get_modal_title(self, object):
        return _('Process objects of type: %s') % self.get_verbose_name(object)

    def get_modal_submit(self):
        return (self.action or '').replace('-', ' ').capitalize()

    def get_modal_content_context(self):
        return {
            'action': self.action,
            'object_list': self.object_list,
            'not_allowed_object_list': self.not_allowed_object_list,
        }

    def get_modal_html_content(self):
        if not self.has_objects():
            return ''
        return loader.render_to_string(self.modal_content_template, self.get_modal_content_context())

    def get_modal_message(self):
        if self.has_objects():
            count = self.object_list.count()

            if count > 0:
                return self.get_confirmation_message(count)

        self.modal_submit = False
        return self.get_not_possible_message()

    def get_not_possible_message(self):
        return _('Not possible to process any of the selected objects.')

    def get_confirmation_message(self, count):
        return ''

    def build_form_fields(self):
        return []

    def get_layout(self):
        return Layout(
            MassActionModalContentLayout(
                *self.build_form_fields(),
                RawHTML(self.modal_html_content),
                modal_title=self.modal_title,
                modal_submit=self.modal_submit,
                modal_message=self.modal_message,
                modal_close=True
            )
        )


class BSModalMassDeleteForm(BSModalMassActionFormMixin):

    def __init__(self, *args, **kwargs):
        self.protected_object_list = kwargs.pop('protected_object_list', None) or []
        super().__init__(*args, **kwargs)

    def get_modal_submit(self):
        return _('Delete')

    def get_modal_title(self, object):
        return _('Delete objects of type: %s') % self.get_verbose_name(object)

    def get_modal_message(self):
        if self.protected_object_list:
            self.modal_submit = False
            return _('Deleting the selected objects requires deleting the following related objects:')
        return super().get_modal_message()

    def get_confirmation_message(self, count):
        return ngettext(
            'Are you sure you want to delete %(count)d object?',
            'Are you sure you want to delete %(count)d objects?',
            count,
        ) % {'count': count}

    def get_modal_html_content(self):
        if self.protected_object_list:
            return self.get_protected_objects_html()
        return super().get_modal_html_content()

    def get_protected_objects_html(self):
        """
        Protected objects grouped by model. When the config knows a list URL for the model
        (``get_related_list_url``), the group links there; otherwise the objects are listed as text.
        """
        grouped = {}

        for obj in self.protected_object_list:
            grouped.setdefault(type(obj), []).append(obj)

        parts = []

        for obj_type, objects in grouped.items():
            ids = [obj.pk for obj in objects]
            url = None

            if self.config is not None and self.request is not None:
                url = self.config.get_related_list_url(self.request, obj_type, ids)

            label = '%s (%d)' % (obj_type._meta.verbose_name_plural, len(ids))

            if url:
                parts.append(format_html('<div><a href="{}" target="_blank">{}</a></div>', url, label))
            else:
                parts.append(format_html('<div><strong>{}</strong>: {}</div>', label,
                                         ', '.join(str(obj) for obj in objects[:20])))

        return mark_safe(''.join(parts))

    # backwards compatible name
    get_protected_object_link = get_protected_objects_html


class BSModalMassUpdateForm(BSModalMassActionFormMixin):

    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        self.field_name_value = kwargs.pop('field_name_value', None)
        self.field_name_localized = kwargs.pop('field_name_localized', None) or self.field_name
        self.form_model = kwargs.pop('form_model', None)
        super().__init__(*args, **kwargs)

    def get_modal_submit(self):
        return _('Update')

    def get_modal_title(self, object):
        return _('Update objects of type: %s') % self.get_verbose_name(object)

    def get_confirmation_message(self, count):
        return ngettext(
            "Are you sure you want to update '%(field_name)s' of this object?",
            "Are you sure you want to update '%(field_name)s' of %(count)d objects?",
            count,
        ) % {'count': count, 'field_name': self.field_name_localized}

    def build_form_fields(self):
        """Default form: one hidden field built from the model field; the value comes from the menu."""
        try:
            form_field = self.form_model._meta.get_field(self.field_name).formfield()
        except (FieldDoesNotExist, AttributeError):
            form_field = None

        if form_field is None:
            raise ImproperlyConfigured('%r is not an editable field of %s. Use a custom update form.'
                                       % (self.field_name, self.form_model.__name__))

        form_field.required = False
        form_field.initial = self.field_name_value
        self.fields[self.field_name] = form_field
        return [Div(self.field_name, css_class='visually-hidden')]

    def clean(self):
        cleaned_data = super().clean()

        # the value chosen in the menu wins over whatever was posted for the hidden field
        if self.field_name_value not in (None, '') and self.field_name in self.fields:
            try:
                cleaned_data[self.field_name] = self.fields[self.field_name].clean(self.field_name_value)
            except ValidationError as e:
                self.add_error(self.field_name, e)

        return cleaned_data

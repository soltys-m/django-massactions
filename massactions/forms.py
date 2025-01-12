from itertools import groupby

from crispy_forms.helper import FormHelper
from crispy_forms.layout import LayoutObject, Layout, HTML, Div
from crispy_forms.utils import flatatt, TEMPLATE_PACK
from django.core.exceptions import ValidationError
from django.template import loader
from django.template.loader import render_to_string
from django.urls import reverse_lazy, NoReverseMatch
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, ngettext

from bootstrap_modal_forms.forms import BSModalForm

class MassActionModalContentLayout(LayoutObject):
    template = "%s/layout/modal_content.html"
    modal_title = ''

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)
        self.modal_id = kwargs.pop("modal_id", None)
        self.modal_title = kwargs.pop("modal_title", None)
        self.modal_close = kwargs.pop("modal_close", None)
        self.modal_submit = kwargs.pop("modal_submit", None)
        self.modal_message = kwargs.pop("modal_message", None)
        self.modal_body = kwargs.pop("modal_body", None)
        self.template = kwargs.pop("template", self.template)
        self.flat_attrs = flatatt(kwargs)

    def render(self, template_pack=TEMPLATE_PACK, **kwargs):
        template = self.get_template_name(template_pack)

        return render_to_string(
            template, {
                "fieldset": self,
                "modal_id": self.modal_id,
                "modal_title": self.modal_title,
                "modal_close": self.modal_close,
                "modal_submit": self.modal_submit,
                "modal_message": self.modal_message,
                "modal_body": self.modal_body,
            }
        )


class BSModalMassActionFormMixin(BSModalForm):
    modal_html_content = ''

    def __init__(self, *args, **kwargs):
        self.object_list = kwargs.pop('object_list')
        self.not_allowed_object_list = kwargs.pop('not_allowed_object_list', None)
        self.action = kwargs.pop('action', None)
        self.first_object = self.object_list[0] if self.object_list.exists() else self.not_allowed_object_list[0] \
            if self.not_allowed_object_list.exists() else None
        self.modal_title = self.get_modal_title(self.first_object)
        self.modal_submit = self.get_modal_submit()
        self.modal_message = self.get_modal_message()
        self.modal_html_content = self.get_modal_html_content()
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = self.get_layout()

    def get_modal_submit(self):
        return _(self.action.capitalize())

    def get_modal_html_content(self):
        html = ''
        if self.object_list or self.not_allowed_object_list:
            template_name = 'massactions/mass_action_modal_content.html'
            context_data = {
                'action': self.action,
                'object_list': self.object_list,
                'not_allowed_object_list': self.not_allowed_object_list,
            }
            html = loader.render_to_string(template_name, context_data)
        return html

    def get_modal_message(self):
        modal_message = ''

        if self.object_list.exists() or self.not_allowed_object_list.exists():
            count = self.object_list.count()

            if count == 0:
                self.modal_submit = False
                modal_message = self.get_not_possible_message()
            else:
                modal_message = self.get_confirmation_message(count)
        return modal_message

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
                HTML(self.modal_html_content),
                modal_title=self.modal_title,
                modal_submit=self.modal_submit,
                modal_message=self.modal_message,
                modal_close=True
            )
        )

class BSModalMassDeleteForm(BSModalMassActionFormMixin):

    def __init__(self, *args, **kwargs):
        self.protected_object_list = kwargs.pop('protected_object_list', None)
        super().__init__(*args, **kwargs)

    def get_modal_submit(self):
        return _('Delete')

    def get_modal_title(self, object):
        return _('Delete objects of type: %s') % object._meta.verbose_name

    def get_modal_message(self):
        modal_message = ''
        if self.protected_object_list:
            self.modal_submit = False
            modal_message = _(
                'Deleting the selected objects requires deleting the following related objects:')

        elif self.object_list.exists() or self.not_allowed_object_list.exists():
            count = self.object_list.count()

            if count == 0:
                self.modal_submit = False
                modal_message = self.get_not_possible_message()
            else:
                modal_message = self.get_confirmation_message(count)

        return modal_message

    def get_confirmation_message(self, count):
        return ngettext(
            'Are you sure you want to delete %(count)d object?',
            'Are you sure you want to delete %(count)d objects?',
            count,
        ) % {'count': count, }

    def get_modal_html_content(self):
        html = ''
        if self.protected_object_list:
            html = self.get_protected_object_link()
        elif self.object_list.exists() or self.not_allowed_object_list.exists():
            template_name = 'massactions/mass_action_modal_content.html'
            context_data = {
                'action': self.action,
                'object_list': self.object_list,
                'not_allowed_object_list': self.not_allowed_object_list
            }
            html = loader.render_to_string(template_name, context_data)
        return html

    def get_protected_object_link(self):
        return ''


class BSModalMassUpdateForm(BSModalMassActionFormMixin):

    def __init__(self, *args, **kwargs):
        self.field_name = kwargs.pop('field_name', None)
        self.field_name_value = kwargs.pop('field_name_value', None)
        self.field_name_localized = kwargs.pop('field_name_localized', None)
        self.form_model = kwargs.pop('form_model', None)
        super().__init__(*args, **kwargs)

    def get_modal_submit(self):
        return _('Update')

    def get_modal_title(self, object):
        return _('Update objects of type: %s') % object._meta.verbose_name

    def get_confirmation_message(self, count):
        return ngettext(
            "Are you sure you want to update '%(field_name)s' of this object?",
            "Are you sure you want to update '%(field_name)s' of %(count)d objects?",
            count,
        ) % {'count': count,
             'field_name':  self.field_name_localized}

    def build_form_fields(self):
        div_layout = []
        try:
            self.fields[self.field_name] = self.form_model._meta.get_field(self.field_name).formfield()
            self.fields[self.field_name].required = False
            div_layout.append(Div(self.field_name, css_class='visually-hidden'))
        except Exception:
            raise ValidationError(_('Entered the wrong attribute'))
        return []

    def clean(self):
        if self.field_name_value:
            self.cleaned_data[self.field_name] = self.field_name_value
        return super().clean()

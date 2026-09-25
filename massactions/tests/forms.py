from crispy_forms.layout import Div
from django import forms

from massactions.forms import BSModalMassUpdateForm
from massactions.tests.models import Item


class MassActionItemForm(BSModalMassUpdateForm):
    status = forms.ChoiceField(choices=Item.STATUS, required=False)
    note = forms.CharField(required=True)

    def build_form_fields(self):
        self.fields['status'].initial = self.field_name_value
        return [Div('status', css_class='d-none'), Div('note')]

from django.urls import path
from django.utils.translation import pgettext_lazy

from massactions.views import MassDeleteView, MassUpdateFieldView

app_name = 'massactions'

urlpatterns = [
    path(pgettext_lazy("url", 'delete/'), MassDeleteView.as_view(), name='mass_delete'),
    path(pgettext_lazy("url", 'update/'), MassUpdateFieldView.as_view(), name='mass_update'),
]

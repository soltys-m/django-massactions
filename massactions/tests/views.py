from django.views.generic import ListView

from massactions.mixins import MassActionListViewMixin
from massactions.tests.filters import ItemFilter
from massactions.tests.models import Item


class ItemListView(MassActionListViewMixin, ListView):
    model = Item
    template_name = 'massactions_tests/item_list.html'
    mass_action_config = 'Item'
    paginate_by = 2

    def get_queryset(self):
        self.filter = ItemFilter(self.request.GET, queryset=Item.objects.order_by('pk'))
        return self.filter.qs


class ItemOverrideListView(ItemListView):
    template_name = 'massactions_tests/item_list_override.html'


class MisconfiguredListView(ItemListView):
    mass_action_config = 'DoesNotExist'

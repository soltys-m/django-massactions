from massactions.registry import MassActionConfig, register
from massactions.tests.filters import ItemFilter
from massactions.tests.forms import MassActionItemForm
from massactions.tests.models import Item

STATUS_UPDATE = {
    'field_name': 'status',
    'field_name_localized': 'Status',
    'localized_action': 'Update status',
    'choices': Item.STATUS,
}


@register
class ItemMassActions(MassActionConfig):
    model = Item
    key = 'Item'
    actions = ['update', 'delete']
    update_fields = [STATUS_UPDATE]
    filter_class = ItemFilter


@register
class ActiveItemMassActions(MassActionConfig):
    """Same model, different list: only active items, custom update form, 'locked' cannot be deleted."""
    model = Item
    key = 'ActiveItem'
    actions = ['update', 'delete']
    update_fields = [STATUS_UPDATE]
    update_form_class = MassActionItemForm

    def get_queryset(self, request):
        return Item.objects.active_only()

    def restrict_queryset(self, request, queryset, action):
        if action == 'delete':
            return queryset.exclude(name='locked')
        return queryset

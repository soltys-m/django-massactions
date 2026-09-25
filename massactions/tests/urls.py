from django.urls import path, include

from massactions.tests.views import ItemListView, ItemOverrideListView, ItemMenuOnlyListView, MisconfiguredListView

urlpatterns = [
    path('massactions/', include('massactions.urls')),
    path('items/', ItemListView.as_view(), name='item_list'),
    path('items/override/', ItemOverrideListView.as_view(), name='item_list_override'),
    path('items/menu-only/', ItemMenuOnlyListView.as_view(), name='item_list_menu_only'),
    path('items/misconfigured/', MisconfiguredListView.as_view(), name='item_list_misconfigured'),
]

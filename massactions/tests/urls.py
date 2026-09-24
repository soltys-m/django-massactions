from django.urls import path, include

from massactions.tests.views import ItemListView, ItemOverrideListView, MisconfiguredListView

urlpatterns = [
    path('massactions/', include('massactions.urls')),
    path('items/', ItemListView.as_view(), name='item_list'),
    path('items/override/', ItemOverrideListView.as_view(), name='item_list_override'),
    path('items/misconfigured/', MisconfiguredListView.as_view(), name='item_list_misconfigured'),
]

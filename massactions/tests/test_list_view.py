from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from massactions.tests.models import Item


class ListViewTests(TestCase):
    def setUp(self):
        for name in ('a', 'b', 'c'):
            Item.objects.create(name=name)

    def test_renders_mass_action_bar_with_registry_urls(self):
        response = self.client.get('/items/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_mass_actions_btn"')
        self.assertContains(response, '/massactions/delete/?key=Item&back_url=')
        self.assertContains(response, '/massactions/update/?key=Item&field_name=status&field_name_value=DONE')
        self.assertContains(response, 'class="dropdown-item mass-action-item"')
        self.assertContains(response, "const massActionKey = 'Item';")
        self.assertContains(response, '/massactions/encrypt/')
        self.assertNotContains(response, 'qs_method')
        self.assertNotContains(response, 'app_label=')

    def test_items_count_is_whole_list_not_page(self):
        response = self.client.get('/items/')  # paginate_by = 2
        self.assertContains(response, 'const itemsCount = 3;')
        self.assertEqual(len(response.context['object_list']), 2)

    def test_items_count_follows_filter(self):
        response = self.client.get('/items/?name=a')
        self.assertContains(response, 'const itemsCount = 1;')

    def test_checkboxes(self):
        response = self.client.get('/items/')
        for item in Item.objects.order_by('pk')[:2]:
            self.assertContains(response, 'id="id_mass_action_checkbox_%s"' % item.pk)

    def test_project_template_can_extend_and_add_menu_items(self):
        response = self.client.get('/items/override/')
        self.assertContains(response, 'id="id_custom_action"')
        self.assertContains(response, 'data-form-url="/custom/?key=Item"')
        self.assertContains(response, 'id="id_mass_action_delete"')

    def test_unknown_config_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.get('/items/misconfigured/')

    def test_context(self):
        context = self.client.get('/items/').context['mass_action_context']
        self.assertEqual(context['key'], 'Item')
        self.assertEqual(context['actions'], ['update', 'delete'])
        self.assertEqual(context['model_name'], 'Item')
        self.assertEqual(context['app_label'], 'massactions_tests')

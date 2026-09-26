from django.template import Context, Template
from django.test import TestCase

from massactions.registry import MassActionConfig
from massactions.templatetags.massactions import massaction_object_listing
from massactions.tests.models import Item


class Plain:
    def __str__(self):
        return 'plain'


class LabelConfig(MassActionConfig):
    model = Item
    modal_object_limit = 2

    def get_object_label(self, obj):
        return 'Item %s' % obj.name

    def get_object_url(self, obj):
        return None


def render_list(**context):
    return Template("{% include 'massactions/mass_action_modal_object_list.html' %}").render(Context(context))


class ObjectListingTests(TestCase):
    def setUp(self):
        self.items = [Item.objects.create(name=name) for name in ('a', 'b', 'c')]

    def test_defaults_without_config(self):
        listing = massaction_object_listing(Item.objects.order_by('pk'))
        self.assertEqual(listing['objects'], [('a', '/items/%s/' % self.items[0].pk),
                                             ('b', '/items/%s/' % self.items[1].pk),
                                             ('c', '/items/%s/' % self.items[2].pk)])
        self.assertEqual(listing['columns'], [listing['objects']])
        self.assertEqual(listing['more'], 0)

    def test_objects_without_get_absolute_url_have_no_link(self):
        listing = massaction_object_listing([Plain()])
        self.assertEqual(listing['objects'], [('plain', None)])

    def test_config_hooks_and_limit(self):
        listing = massaction_object_listing(Item.objects.order_by('pk'), LabelConfig())
        self.assertEqual(listing['objects'], [('Item a', None), ('Item b', None)])
        self.assertEqual(listing['more'], 1)

    def test_explicit_limit_and_lists(self):
        listing = massaction_object_listing(self.items, limit=1)
        self.assertEqual(len(listing['objects']), 1)
        self.assertEqual(listing['more'], 2)
        self.assertEqual(massaction_object_listing(self.items, limit=0)['more'], 0)

    def test_columns_are_filled_in_reading_order(self):
        listing = massaction_object_listing(self.items, columns=2)
        self.assertEqual([[label for label, url in column] for column in listing['columns']], [['a', 'b'], ['c']])
        self.assertEqual(len(massaction_object_listing(self.items, columns='3')['columns']), 3)
        self.assertEqual(len(massaction_object_listing(self.items, columns=5)['columns']), 3)
        self.assertEqual(massaction_object_listing([], columns=3)['columns'], [])

    def test_template_renders_columns_and_the_rest_as_count(self):
        html = render_list(object_list=Item.objects.order_by('pk'), config=LabelConfig(), columns=2)
        self.assertEqual(html.count('<ul class="col-sm-6 col-md list-unstyled mb-0">'), 2)
        self.assertEqual(html.count('<li>'), 2)
        self.assertIn('Item a', html)
        self.assertNotIn('href=', html)
        self.assertIn('and 1 more object', html)

    def test_template_without_config_links_the_objects_in_three_columns(self):
        html = render_list(object_list=Item.objects.order_by('pk'))
        self.assertEqual(html.count('<ul class="col-sm-6 col-md list-unstyled mb-0">'), 3)
        self.assertIn('<a href="/items/%s/" target="_blank">a</a>' % self.items[0].pk, html)
        self.assertNotIn('more object', html)

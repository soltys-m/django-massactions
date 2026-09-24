from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from massactions.registry import MassActionConfig, MassActionRegistry, registry
from massactions.tests.massactions import ItemMassActions, ActiveItemMassActions
from massactions.tests.models import Item


class RegistryTests(SimpleTestCase):
    def test_autodiscover_registered_test_configs(self):
        self.assertIn('Item', registry)
        self.assertIn('ActiveItem', registry)
        self.assertIsInstance(registry.get('Item'), ItemMassActions)

    def test_key_defaults_to_model_name(self):
        class Config(MassActionConfig):
            model = Item
        self.assertEqual(Config().key, 'Item')

    def test_model_is_required(self):
        class Config(MassActionConfig):
            pass
        with self.assertRaises(ImproperlyConfigured):
            Config()

    def test_duplicate_key_raises(self):
        local = MassActionRegistry()

        @local.register
        class First(MassActionConfig):
            model = Item
            key = 'X'

        class Second(MassActionConfig):
            model = Item
            key = 'X'

        with self.assertRaises(ImproperlyConfigured):
            local.register(Second)

        local.register(First)  # re-registering the same class is fine
        self.assertEqual(local.keys(), ['X'])

    def test_register_rejects_non_config(self):
        with self.assertRaises(ImproperlyConfigured):
            MassActionRegistry().register(object)

    def test_resolve_accepts_key_class_and_instance(self):
        config = registry.get('ActiveItem')
        self.assertIs(registry.resolve('ActiveItem'), config)
        self.assertIs(registry.resolve(ActiveItemMassActions), config)
        self.assertIs(registry.resolve(config), config)

    def test_resolve_unknown_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            registry.resolve('Nope')

        class Unregistered(MassActionConfig):
            model = Item

        with self.assertRaises(ImproperlyConfigured):
            registry.resolve(Unregistered)

    def test_get_returns_none_for_missing_or_empty_key(self):
        self.assertIsNone(registry.get(None))
        self.assertIsNone(registry.get(''))
        self.assertIsNone(registry.get('Nope'))

    def test_permission_string(self):
        config = registry.get('Item')
        self.assertEqual(config.get_permission_required('delete'), 'massactions_tests.delete_item')
        self.assertEqual(config.get_permission_required('update'), 'massactions_tests.change_item')
        self.assertEqual(config.get_permission_required('lock'), 'massactions_tests.lock_item')

    def test_get_update_field(self):
        config = registry.get('Item')
        self.assertEqual(config.get_update_field('status')['field_name_localized'], 'Status')
        self.assertIsNone(config.get_update_field('nope'))
        self.assertIsNone(config.get_update_field(None))

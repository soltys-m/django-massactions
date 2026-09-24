import json

from django.test import TestCase

from massactions.helpers import encrypt_string, decrypt_string, parse_selection, clean_ids, apply_selection
from massactions.tests.models import Item


class CryptoTests(TestCase):
    def test_roundtrip(self):
        self.assertEqual(decrypt_string(encrypt_string('{"ids": ["1"]}')), '{"ids": ["1"]}')

    def test_key_travels_with_ciphertext(self):
        # documents the current design: the value can be produced and read without any server secret
        value = encrypt_string(json.dumps({'ids': [], 'selectAll': True}))
        self.assertTrue(json.loads(decrypt_string(value))['selectAll'])


class ParseSelectionTests(TestCase):
    def test_missing(self):
        self.assertIsNone(parse_selection(None))
        self.assertIsNone(parse_selection(''))

    def test_garbage(self):
        self.assertIsNone(parse_selection('not-a-cookie'))
        self.assertIsNone(parse_selection('x'))

    def test_non_dict_payload(self):
        self.assertIsNone(parse_selection(encrypt_string('[1, 2]')))
        self.assertIsNone(parse_selection(encrypt_string('{"ids": "1,2"}')))

    def test_ids_are_strings_and_select_all_is_bool(self):
        selection = parse_selection(encrypt_string(json.dumps({'ids': [1, '2'], 'selectAll': 'yes'})))
        self.assertEqual(selection['ids'], ['1', '2'])
        self.assertTrue(selection['selectAll'])

    def test_defaults(self):
        selection = parse_selection(encrypt_string('{}'))
        self.assertEqual(selection, {'ids': [], 'selectAll': False, 'user': None, 'currentFilter': None})


class ApplySelectionTests(TestCase):
    def setUp(self):
        self.a = Item.objects.create(name='a')
        self.b = Item.objects.create(name='b')
        self.c = Item.objects.create(name='c')

    def test_clean_ids_drops_invalid_values(self):
        self.assertEqual(clean_ids(Item, [str(self.a.pk), 'abc', None, self.b.pk]), [self.a.pk, self.b.pk])

    def test_explicit_ids(self):
        qs = apply_selection(Item.objects.all(), {'ids': [str(self.a.pk), 'abc'], 'selectAll': False})
        self.assertEqual(list(qs), [self.a])

    def test_select_all(self):
        qs = apply_selection(Item.objects.all(), {'ids': [], 'selectAll': True})
        self.assertEqual(qs.count(), 3)

    def test_select_all_with_exclusions(self):
        qs = apply_selection(Item.objects.all(), {'ids': [str(self.b.pk)], 'selectAll': True})
        self.assertEqual(set(qs), {self.a, self.c})

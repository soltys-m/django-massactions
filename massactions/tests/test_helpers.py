import json
import time
from unittest import mock
from urllib.parse import quote

from django.core import signing
from django.test import TestCase, override_settings

from massactions.helpers import sign_selection, unsign_selection, parse_selection, clean_ids, apply_selection
from massactions.tests.models import Item


class SigningTests(TestCase):
    def test_roundtrip(self):
        value = sign_selection({'ids': ['1'], 'selectAll': False})
        self.assertEqual(unsign_selection(value), {'ids': ['1'], 'selectAll': False})

    def test_accepts_json_string(self):
        self.assertEqual(unsign_selection(sign_selection('{"ids": ["1"]}')), {'ids': ['1']})

    def test_rejects_non_dict(self):
        with self.assertRaises(ValueError):
            sign_selection('[1, 2]')

    def test_tampered_value_is_rejected(self):
        value = sign_selection({'ids': ['1'], 'selectAll': False})
        payload, timestamp, signature = value.rsplit(':', 2)
        forged = ':'.join([signing.b64_encode(b'{"ids":[],"selectAll":true}').decode(), timestamp, signature])
        self.assertIsNone(unsign_selection(forged))
        self.assertIsNone(unsign_selection(value[:-1] + ('a' if value[-1] != 'a' else 'b')))

    def test_value_signed_with_another_secret_is_rejected(self):
        value = sign_selection({'ids': ['1']})
        with override_settings(SECRET_KEY='another-secret'):
            self.assertIsNone(unsign_selection(value))

    def test_expired_value_is_rejected(self):
        with mock.patch('django.core.signing.time.time', return_value=time.time() - 7200):
            value = sign_selection({'ids': ['1']})
        self.assertIsNone(unsign_selection(value))          # default max age is one hour
        self.assertIsNotNone(unsign_selection(value, max_age=3 * 3600))

    def test_garbage(self):
        self.assertIsNone(unsign_selection(None))
        self.assertIsNone(unsign_selection(''))
        self.assertIsNone(unsign_selection('not-a-cookie'))
        self.assertIsNone(unsign_selection('a:b:c'))

    def test_url_encoded_cookie_value(self):
        value = sign_selection({'ids': ['1']})
        self.assertEqual(unsign_selection(quote(value)), {'ids': ['1']})


class ParseSelectionTests(TestCase):
    def test_missing(self):
        self.assertIsNone(parse_selection(None))
        self.assertIsNone(parse_selection(''))

    def test_garbage(self):
        self.assertIsNone(parse_selection('not-a-cookie'))
        self.assertIsNone(parse_selection('x'))

    def test_non_dict_payload(self):
        self.assertIsNone(parse_selection(signing.dumps([1, 2], salt='massactions.selection', compress=True)))
        self.assertIsNone(parse_selection(sign_selection('{"ids": "1,2"}')))

    def test_ids_are_strings_and_select_all_is_bool(self):
        selection = parse_selection(sign_selection(json.dumps({'ids': [1, '2'], 'selectAll': 'yes'})))
        self.assertEqual(selection['ids'], ['1', '2'])
        self.assertTrue(selection['selectAll'])

    def test_defaults(self):
        selection = parse_selection(sign_selection('{}'))
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

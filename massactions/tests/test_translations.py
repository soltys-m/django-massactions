from django.test import SimpleTestCase
from django.utils import translation


class TranslationTests(SimpleTestCase):
    def test_slovak_catalog_is_shipped(self):
        with translation.override('sk'):
            self.assertEqual(translation.gettext('Login required'), 'Vyžaduje sa prihlásenie')
            self.assertEqual(translation.gettext('Delete objects of type: %s') % 'x', 'Zmazať objekty typu: x')
            self.assertEqual(translation.ngettext('%(count)d object was successfully deleted.',
                                                  '%(count)d objects were successfully deleted.', 5) % {'count': 5},
                             '5 objektov bolo úspešne zmazaných.')

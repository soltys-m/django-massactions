from urllib.parse import urlencode

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from massactions.helpers import decrypt_string
from massactions.tests.models import Item, Child
from massactions.tests.utils import set_selection


class MassActionTestCase(TestCase):
    key = 'Item'

    def setUp(self):
        self.user = User.objects.create_user('user', password='pw')
        self.grant('delete_item', 'change_item')
        self.client.force_login(self.user)
        self.a = Item.objects.create(name='a')
        self.b = Item.objects.create(name='b', status='DONE')
        self.c = Item.objects.create(name='c', is_active=False)
        self.locked = Item.objects.create(name='locked')

    def grant(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='massactions_tests', codename__in=codenames))

    def select(self, ids=(), select_all=False, key=None):
        set_selection(self.client, self.user, key or self.key, ids, select_all)

    def url(self, name, key=None, **params):
        return reverse('massactions:' + name) + '?' + urlencode({'key': key or self.key, **params})

    def names(self):
        return set(Item.objects.values_list('name', flat=True))


class DeleteTests(MassActionTestCase):
    def test_get_renders_confirmation_modal(self):
        self.select([self.a.pk, self.b.pk])
        response = self.client.get(self.url('mass_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete objects of type: item')
        self.assertContains(response, 'Are you sure you want to delete 2 objects?')
        self.assertContains(response, 'Following objects will be deleted')
        self.assertContains(response, 'href="/items/%s/"' % self.a.pk)
        self.assertContains(response, 'id="id_submit_btn"')

    def test_post_deletes_selected_and_redirects_back(self):
        self.select([self.a.pk, self.b.pk])
        response = self.client.post(self.url('mass_delete', back_url='/items/?page=2'))
        self.assertRedirects(response, '/items/?page=2', fetch_redirect_response=False)
        self.assertEqual(self.names(), {'c', 'locked'})
        self.assertEqual(response.cookies['%s_Item' % self.user.id].value, 'True')

    def test_select_all(self):
        self.select(select_all=True)
        self.client.post(self.url('mass_delete'))
        self.assertEqual(Item.objects.count(), 0)

    def test_select_all_minus_excluded(self):
        self.select([self.a.pk], select_all=True)
        self.client.post(self.url('mass_delete'))
        self.assertEqual(self.names(), {'a'})

    def test_select_all_respects_list_filter_from_back_url(self):
        self.select(select_all=True)
        self.client.post(self.url('mass_delete', back_url='/items/?status=DONE&page=1'))
        self.assertEqual(self.names(), {'a', 'c', 'locked'})

    def test_config_queryset_and_restriction(self):
        self.select(select_all=True, key='ActiveItem')
        response = self.client.get(self.url('mass_delete', key='ActiveItem'))
        self.assertContains(response, 'Missing permissions to delete')
        self.assertContains(response, '>locked<')
        self.client.post(self.url('mass_delete', key='ActiveItem'))
        # inactive item is outside the config queryset, 'locked' is restricted by the config
        self.assertEqual(self.names(), {'c', 'locked'})

    def test_protected_objects_block_delete(self):
        Child.objects.create(item=self.a, label='the child')
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'requires deleting the following related objects')
        self.assertContains(response, 'the child')
        self.assertNotContains(response, 'id="id_submit_btn"')
        response = self.client.post(self.url('mass_delete'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Item.objects.filter(pk=self.a.pk).exists())
        self.assertEqual(response.cookies['%s_Item' % self.user.id].value, 'False')

    def test_no_cookie(self):
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'No object selected')

    def test_empty_selection(self):
        self.select([])
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'No object selected')

    def test_garbage_cookie(self):
        self.client.cookies['%s_Item' % self.user.id] = 'garbage'
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'No object selected')

    def test_stale_ids(self):
        self.select([99999, 'abc'])
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'Not possible to process any of the selected objects')
        self.assertNotContains(response, 'id="id_submit_btn"')
        self.client.post(self.url('mass_delete'))
        self.assertEqual(Item.objects.count(), 4)

    def test_missing_or_unknown_key_is_404(self):
        self.select([self.a.pk])
        self.assertEqual(self.client.get(reverse('massactions:mass_delete')).status_code, 404)
        self.assertEqual(self.client.get(self.url('mass_delete', key='Nope')).status_code, 404)
        self.assertEqual(self.client.post(self.url('mass_delete', key='auth.User')).status_code, 404)

    def test_no_permission(self):
        self.user.user_permissions.clear()
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'Permission missing')
        self.client.post(self.url('mass_delete'))
        self.assertEqual(Item.objects.count(), 4)

    def test_anonymous(self):
        self.client.logout()
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'Login required')
        self.client.post(self.url('mass_delete'))
        self.assertEqual(Item.objects.count(), 4)

    def test_external_back_url_is_not_used_for_redirect(self):
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_delete', back_url='https://evil.example/phish'))
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_object_names_are_not_rendered_as_template(self):
        evil = Item.objects.create(name='{{ csrf_token }}{% if 1 %}x{% endif %}')
        self.select([evil.pk])
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, '{{ csrf_token }}{% if 1 %}x{% endif %}')


class UpdateTests(MassActionTestCase):
    def test_get_renders_modal_with_hidden_field(self):
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_update', field_name='status', field_name_value='DONE'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update objects of type: item')
        self.assertContains(response, 'update &#x27;Status&#x27; of this object?')
        self.assertContains(response, 'Following objects will be updated')
        self.assertContains(response, 'name="status"')
        self.assertContains(response, '<option value="DONE" selected>')

    def test_post_updates_field(self):
        self.select([self.a.pk, self.c.pk])
        response = self.client.post(self.url('mass_update', field_name='status', field_name_value='DONE'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Item.objects.get(pk=self.a.pk).status, 'DONE')
        self.assertEqual(Item.objects.get(pk=self.c.pk).status, 'DONE')
        self.assertEqual(Item.objects.get(pk=self.b.pk).status, 'DONE')  # unchanged, was DONE
        self.assertEqual(Item.objects.get(pk=self.locked.pk).status, 'NEW')

    def test_menu_value_wins_over_posted_hidden_field(self):
        self.select([self.a.pk])
        self.client.post(self.url('mass_update', field_name='status', field_name_value='DONE'), {'status': 'NEW'})
        self.assertEqual(Item.objects.get(pk=self.a.pk).status, 'DONE')

    def test_custom_form(self):
        self.select([self.a.pk, self.c.pk], key='ActiveItem')
        url = self.url('mass_update', key='ActiveItem', field_name='status', field_name_value='DONE')
        response = self.client.get(url)
        self.assertContains(response, 'name="note"')
        response = self.client.post(url, {'note': 'hello'})
        self.assertEqual(response.status_code, 302)
        self.a.refresh_from_db()
        self.c.refresh_from_db()
        self.assertEqual((self.a.status, self.a.note), ('DONE', 'hello'))
        self.assertEqual((self.c.status, self.c.note), ('NEW', ''))  # inactive: outside the config queryset

    def test_custom_form_invalid_post_rerenders_modal(self):
        self.select([self.a.pk], key='ActiveItem')
        url = self.url('mass_update', key='ActiveItem', field_name='status', field_name_value='DONE')
        response = self.client.post(url, {'note': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        self.assertEqual(Item.objects.get(pk=self.a.pk).status, 'NEW')

    def test_unknown_field_is_400(self):
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_update', field_name='name', field_name_value='x'))
        self.assertEqual(response.status_code, 400)

    def test_invalid_value_is_400(self):
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_update', field_name='status', field_name_value='HACK'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Item.objects.get(pk=self.a.pk).status, 'NEW')

    def test_requires_change_permission(self):
        self.user.user_permissions.clear()
        self.grant('delete_item')
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_update', field_name='status', field_name_value='DONE'))
        self.assertContains(response, 'Permission missing')


class EncryptViewTests(MassActionTestCase):
    def test_post_returns_encrypted_selection(self):
        response = self.client.post(reverse('massactions:encrypt'), {'string': '{"ids": ["1"]}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(decrypt_string(response.json()['encrypted_string']), '{"ids": ["1"]}')

    def test_anonymous_is_403(self):
        self.client.logout()
        self.assertEqual(self.client.post(reverse('massactions:encrypt'), {'string': 'x'}).status_code, 403)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse('massactions:encrypt')).status_code, 405)

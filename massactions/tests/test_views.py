from unittest import mock
from urllib.parse import urlencode

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse

from massactions.helpers import unsign_selection
from massactions.tests.massactions import ActiveItemMassActions
from massactions.tests.models import Item, Child
from massactions.tests.utils import set_selection, make_selection_cookie


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
        self.assertContains(response, '<div class="col-12">')
        self.assertContains(response, '<li>', count=2)
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
        self.assertContains(response, '<div class="col-md-6">', count=2)
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


class AjaxSubmitTests(MassActionTestCase):
    """The modal submits its form with one AJAX POST; the view answers with the form or with a JSON redirect."""
    ajax = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    def test_valid_update_answers_with_json_redirect_and_resets_the_selection(self):
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_update', field_name='status', field_name_value='DONE', back_url='/items/?page=2'), **self.ajax)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'redirect': '/items/?page=2'})
        self.assertEqual(response.cookies['%s_Item' % self.user.id].value, 'True')
        self.assertEqual(Item.objects.get(pk=self.a.pk).status, 'DONE')

    def test_invalid_form_answers_with_the_form_and_changes_nothing(self):
        self.select([self.a.pk], key='ActiveItem')
        url = self.url('mass_update', key='ActiveItem', field_name='status', field_name_value='DONE')
        response = self.client.post(url, {'note': ''}, **self.ajax)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'].split(';')[0], 'text/html')
        self.assertContains(response, 'This field is required')
        self.assertContains(response, 'id="id_submit_btn"')
        self.assertNotIn('%s_ActiveItem' % self.user.id, response.cookies)
        self.assertEqual(Item.objects.get(pk=self.a.pk).status, 'NEW')

    def test_action_runs_once_per_submit(self):
        self.select([self.a.pk], key='ActiveItem')
        url = self.url('mass_update', key='ActiveItem', field_name='status', field_name_value='DONE')
        with mock.patch.object(ActiveItemMassActions, 'update_object', autospec=True) as update_object:
            self.client.post(url, {'note': 'hello'}, **self.ajax)
        self.assertEqual(update_object.call_count, 1)

    def test_delete_answers_with_json_redirect(self):
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_delete', back_url='/items/'), **self.ajax)
        self.assertEqual(response.json(), {'redirect': '/items/'})
        self.assertFalse(Item.objects.filter(pk=self.a.pk).exists())

    def test_protected_delete_answers_with_json_redirect_and_failed_cookie(self):
        Child.objects.create(item=self.a, label='child')
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_delete', back_url='/items/'), **self.ajax)
        self.assertEqual(response.json(), {'redirect': '/items/'})
        self.assertEqual(response.cookies['%s_Item' % self.user.id].value, 'False')

    def test_external_back_url_is_not_used_for_the_json_redirect(self):
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_delete', back_url='https://evil.example/'), **self.ajax)
        self.assertEqual(response.json(), {'redirect': '/'})

    def test_no_permission_answers_with_the_message_modal(self):
        self.user.user_permissions.clear()
        self.select([self.a.pk])
        response = self.client.post(self.url('mass_delete'), **self.ajax)
        self.assertContains(response, 'Permission missing')
        self.assertTrue(Item.objects.filter(pk=self.a.pk).exists())


class EncryptViewTests(MassActionTestCase):
    def test_post_returns_signed_selection(self):
        response = self.client.post(reverse('massactions:encrypt'), {'string': '{"ids": ["1"], "selectAll": false}'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['encrypted_string'], data['selection'])
        self.assertEqual(unsign_selection(data['selection']), {'ids': ['1'], 'selectAll': False})

    def test_invalid_json_is_400(self):
        self.assertEqual(self.client.post(reverse('massactions:encrypt'), {'string': 'x'}).status_code, 400)
        self.assertEqual(self.client.post(reverse('massactions:encrypt'), {'string': '[1]'}).status_code, 400)
        self.assertEqual(self.client.post(reverse('massactions:encrypt')).status_code, 400)

    def test_anonymous_is_403(self):
        self.client.logout()
        self.assertEqual(self.client.post(reverse('massactions:encrypt'), {'string': '{}'}).status_code, 403)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse('massactions:encrypt')).status_code, 405)

    def test_tampered_cookie_means_nothing_selected(self):
        name, value = make_selection_cookie(self.user, self.key, [self.a.pk])
        self.client.cookies[name] = value[:-2] + 'zz'
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'No object selected')
        self.client.post(self.url('mass_delete'))
        self.assertEqual(Item.objects.count(), 4)

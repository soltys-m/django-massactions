from contextlib import contextmanager
from unittest import skipUnless

from django.template import TemplateDoesNotExist, engines
from django.template.loader import get_template
from django.test import TestCase, override_settings

from massactions.tests.models import Item
from massactions.tests.test_views import MassActionTestCase


def crispy_bootstrap4_pack_installed():
    try:
        get_template('bootstrap4/field.html')
    except TemplateDoesNotExist:
        return False
    return True


def reset_template_cache():
    for engine in engines.all():
        for loader in engine.engine.template_loaders:
            if hasattr(loader, 'reset'):
                loader.reset()


@contextmanager
def crispy_bootstrap4():
    """
    Render with ``CRISPY_TEMPLATE_PACK = 'bootstrap4'``. The ``{% crispy %}`` tag bakes the pack into the
    compiled template, so the cached templates are dropped before and after the override.
    """
    reset_template_cache()
    try:
        with override_settings(CRISPY_TEMPLATE_PACK='bootstrap4', CRISPY_ALLOWED_TEMPLATE_PACKS=('bootstrap4', 'bootstrap5')):
            yield
    finally:
        reset_template_cache()


class MarkupTests(TestCase):
    """The markup carries the Bootstrap 4 and 5 attribute sets side by side; each version ignores the other's."""

    def setUp(self):
        Item.objects.create(name='a')

    def test_dropdowns(self):
        response = self.client.get('/items/')
        self.assertContains(response, 'data-toggle="dropdown" data-bs-toggle="dropdown"', count=2)
        self.assertContains(response, 'class="col-md px-2 text-end text-right"')
        self.assertContains(response, 'fa-fw me-2 mr-2')
        self.assertNotContains(response, '<li>')

    def test_checkbox(self):
        response = self.client.get('/items/')
        self.assertContains(response, 'class="form-check-input mass-action-checkbox position-relative ms-0 ml-0"')

    def test_choices_submenu_is_toggled_by_the_page_script(self):
        response = self.client.get('/items/')
        self.assertContains(response, 'mass-action-submenu-toggle" href="#"')
        self.assertContains(response, 'data-target="#status_submenu"')
        self.assertContains(response, "$('.mass-action-submenu-toggle').on('click'")
        self.assertNotContains(response, 'data-bs-toggle="collapse"')
        self.assertNotContains(response, 'data-bs-auto-close')

    def test_modal_container_is_appended_to_body_by_the_helper_script(self):
        response = self.client.get('/items/')
        self.assertContains(response, "appendTo('body')")
        self.assertContains(response, 'id="modal"', count=1)
        self.assertContains(response, 'modal-dialog modal-lg modal-dialog-scrollable')

    def test_helper_triggers_modal_shown_event(self):
        response = self.client.get('/items/')
        self.assertContains(response, "$(document).trigger('massactions:modal-shown'")

    def test_helper_submits_the_modal_form_itself(self):
        response = self.client.get('/items/')
        self.assertContains(response, 'data: new FormData(this)')
        self.assertContains(response, 'window.location.href = data.redirect;')
        self.assertNotContains(response, '.modalForm(')
        self.assertNotContains(response, 'showModal($.extend')

    def test_menu_items_only(self):
        """A project with its own actions dropdown renders just the items (block ``mass_action_menu_items``)."""
        response = self.client.get('/items/menu-only/')
        self.assertContains(response, 'id="id_project_menu"')
        self.assertContains(response, 'id="id_mass_action_delete"')
        self.assertContains(response, 'field_name_value=DONE')
        self.assertNotContains(response, 'id="id_mass_actions_btn"')
        self.assertNotContains(response, 'id="id_select_all"')
        self.assertNotContains(response, 'mass-action-bar')
        # the helper script and the page script are outside the bar block
        self.assertContains(response, "appendTo('body')")
        self.assertContains(response, "const massActionKey = 'Item';")

    def test_js_extra_block_runs_inside_the_page_script(self):
        content = self.client.get('/items/override/').content.decode()
        marker = content.index('window.massActionsExtra = resetSelection;')
        start = content.index('window.massActions[massActionKey] = {')
        self.assertLess(start, marker)
        self.assertLess(marker, content.index('})(jQuery);', start))


class ModalTests(MassActionTestCase):
    def test_close_button_follows_crispy_template_pack(self):
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'No object selected')
        self.assertContains(response, 'class="btn-close" data-bs-dismiss="modal"')
        self.assertContains(response, 'data-dismiss="modal" data-bs-dismiss="modal"')

        with crispy_bootstrap4():
            response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'class="close" data-dismiss="modal"')
        self.assertNotContains(response, 'btn-close')

    @skipUnless(crispy_bootstrap4_pack_installed(), 'crispy bootstrap4 template pack is not installed')
    def test_form_modal_close_button_follows_crispy_template_pack(self):
        self.select([self.a.pk])
        with crispy_bootstrap4():
            response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'Are you sure you want to delete 1 object?')
        self.assertContains(response, 'class="close" data-dismiss="modal"')
        self.assertContains(response, 'id="id_submit_btn"')

    def test_form_modal_default_close_button(self):
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_delete'))
        self.assertContains(response, 'class="btn-close" data-bs-dismiss="modal"')

    def test_update_form_hides_menu_driven_field(self):
        self.select([self.a.pk])
        response = self.client.get(self.url('mass_update', field_name='status', field_name_value='DONE'))
        self.assertContains(response, 'class="d-none"')

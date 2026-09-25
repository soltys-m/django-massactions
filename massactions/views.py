import json
from urllib.parse import urlparse

from bootstrap_modal_forms.generic import BSModalFormView
from crispy_forms.utils import get_template_pack
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.db import router
from django.db.models import ProtectedError
from django.http import Http404, HttpResponseBadRequest, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _, ngettext
from django.views import View

from massactions.forms import BSModalMassDeleteForm, BSModalMassUpdateForm
from massactions.helpers import (sign_selection, get_selection_cookie_name, parse_selection, apply_selection,
                                 set_selection_done_cookie)
from massactions.registry import registry


class EncryptSelectionView(LoginRequiredMixin, View):
    """
    Called by the list page JS before opening an action: signs the stored selection so the action view
    can trust the cookie value. The name is historical, the value is signed, not encrypted.
    """
    raise_exception = True
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        try:
            selection = json.loads(request.POST.get('string', ''))
        except ValueError:
            selection = None

        if not isinstance(selection, dict):
            return HttpResponseBadRequest('Invalid selection.')

        signed = sign_selection(selection)
        return JsonResponse({'encrypted_string': signed, 'selection': signed})


class MassActionViewMixin(PermissionRequiredMixin):
    """
    Resolves the registered config from ``?key=`` and the selection from the cookie, then exposes
    ``restricted_object_list`` (objects the user may act on) and ``not_allowed_object_list``.
    """
    action = None
    permission_denied_message = _('You do not have permission to perform this action.')
    login_required_message = _('Your session has expired. Please, log in again.')
    select_object_message = _('Please, select an object first.')
    restricted_object_list = None
    not_allowed_object_list = None

    def dispatch(self, request, *args, **kwargs):
        self.config = registry.get(request.GET.get('key'))

        if self.config is None:
            raise Http404('Unknown mass action key.')

        self.model = self.config.model
        self.key = self.config.key
        self.back_url = request.GET.get('back_url') or None
        self.user_mass_action_cookie = get_selection_cookie_name(request.user.id, self.key)
        self.permission_required = self.get_required_permission_string()

        if not self.has_permission():
            return self.handle_no_permission()

        error_response = self.validate_request()

        if error_response is not None:
            return error_response

        self.selection = parse_selection(request.COOKIES.get(self.user_mass_action_cookie))

        if not self.selection or (not self.selection['ids'] and not self.selection['selectAll']):
            return self.handle_no_object_selected()

        object_list = self.get_selected_queryset(self.selection)
        self.restricted_object_list = self.restrict_objects_by_user_permission(object_list)
        self.not_allowed_object_list = object_list.exclude(pk__in=self.restricted_object_list.values('pk'))

        return super().dispatch(request, *args, **kwargs)

    def get_action(self):
        return self.action

    def validate_request(self):
        """Return an HttpResponse to abort (e.g. 400) or None to continue. Runs after the permission check."""
        return None

    def get_required_permission_string(self):
        """An explicit ``permission_required`` on the view wins; otherwise it is derived from the config and action."""
        if self.permission_required is not None:
            return self.permission_required

        action = self.get_action()

        if action:
            return self.config.get_permission_required(action)

        raise ImproperlyConfigured('%s needs either "action" or "permission_required".' % type(self).__name__)

    def has_permission(self):
        return super().has_permission() and self.config.has_permission(self.request, self.get_action())

    def get_filter_data(self):
        if not self.back_url:
            return None

        query = urlparse(self.back_url).query
        return QueryDict(query) if query else None

    def get_selected_queryset(self, selection):
        queryset = self.config.get_queryset(self.request)
        queryset = self.config.filter_queryset(self.request, queryset, self.get_filter_data())
        return apply_selection(queryset, selection)

    def restrict_objects_by_user_permission(self, object_list):
        return self.config.restrict_queryset(self.request, object_list, self.get_action())

    def get_success_url(self):
        if self.back_url and url_has_allowed_host_and_scheme(self.back_url,
                                                              allowed_hosts={self.request.get_host()},
                                                              require_https=self.request.is_secure()):
            return self.back_url
        return self.config.get_success_url(self.request)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()  # redirect to login

        messages.error(self.request, self.permission_denied_message)
        return redirect(self.get_success_url())

    def handle_no_object_selected(self):
        messages.error(self.request, self.select_object_message)
        return redirect(self.get_success_url())

    def finish(self, success=True):
        """Redirect back and tell the list page to reset the stored selection."""
        response = redirect(self.get_success_url())
        return set_selection_done_cookie(response, self.user_mass_action_cookie, success)


class BSModalMassActionViewMixin(MassActionViewMixin, BSModalFormView):
    template_name = 'massactions/helpers/crispy_form.html'
    modal_content_template = 'massactions/helpers/modal_content.html'

    def get_form_kwargs(self):
        return {
            'request': self.request,
            'config': self.config,
            'object_list': self.restricted_object_list,
            'not_allowed_object_list': self.not_allowed_object_list,
            'action': self.get_action(),
        }

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    def render_modal_message(self, title, message):
        return render(self.request, self.modal_content_template, {
            'modal_title': title,
            'modal_message': message,
            'modal_close': True,
            'template_pack': get_template_pack(),
        })

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return self.render_modal_message(_('Login required'), self.login_required_message)
        return self.render_modal_message(_('Permission missing'), self.permission_denied_message)

    def handle_no_object_selected(self):
        return self.render_modal_message(_('No object selected'), self.select_object_message)


class MassDeleteView(BSModalMassActionViewMixin):
    action = 'delete'
    form_class = BSModalMassDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['protected_object_list'] = self.get_protected_objects(self.restricted_object_list)
        return kwargs

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        try:
            count = self.perform_delete(self.restricted_object_list)
        except ProtectedError:
            messages.error(request, _('Objects could not be deleted, because they are associated with other objects.'))
            return self.finish(success=False)

        messages.success(request, ngettext(
            '%(count)d object was successfully deleted.',
            '%(count)d objects were successfully deleted.',
            count,
        ) % {'count': count})
        return self.finish()

    def perform_delete(self, queryset):
        count = queryset.count()

        try:
            queryset.delete()
        except TypeError:
            # sliced or distinct querysets cannot be deleted in bulk
            for obj in queryset:
                obj.delete()

        return count

    def get_protected_objects(self, queryset):
        if not queryset.exists():
            return []

        collector = NestedObjects(using=router.db_for_write(queryset.model))
        collector.collect(queryset)
        return collector.protected


class MassUpdateFieldView(BSModalMassActionViewMixin):
    action = 'update'
    form_class = BSModalMassUpdateForm

    def validate_request(self):
        self.field_name = self.request.GET.get('field_name')
        self.field_name_value = self.request.GET.get('field_name_value')
        self.update_field = self.config.get_update_field(self.field_name)

        if self.update_field is None:
            return HttpResponseBadRequest('Unknown field.')

        choices = self.update_field.get('choices')

        if choices and self.field_name_value is not None:
            if str(self.field_name_value) not in {str(choice[0]) for choice in choices}:
                return HttpResponseBadRequest('Invalid value.')

        return None

    def get_form_class(self):
        return self.config.get_update_form_class(self.field_name) or self.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'field_name': self.field_name,
            'field_name_value': self.field_name_value,
            'field_name_localized': self.update_field.get('field_name_localized'),
            'form_model': self.model,
        })
        return kwargs

    def post(self, request, *args, **kwargs):
        return self.bulk_update_field(request, *args, **kwargs)

    def bulk_update_field(self, request, *args, **kwargs):
        form = self.get_form_class()(request.POST, **self.get_form_kwargs())

        if not form.is_valid():
            return self.form_invalid(form)

        count = self.perform_update(self.restricted_object_list, form)
        messages.success(request, ngettext(
            '%(count)d object was successfully updated.',
            '%(count)d objects were successfully updated.',
            count,
        ) % {'count': count})
        return self.finish()

    def get_update_values(self, form):
        return {name: form.cleaned_data.get(name) for name in form.fields}

    def perform_update(self, queryset, form):
        """Objects are updated one by one through ``config.update_object()``. Override for ``queryset.update()``."""
        values = self.get_update_values(form)
        count = 0

        for obj in queryset:
            self.config.update_object(self.request, obj, values)
            count += 1

        return count

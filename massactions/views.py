import importlib
import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from urllib.parse import unquote, urlparse, parse_qs

from django.apps import apps

from bootstrap_modal_forms.generic import BSModalFormView
from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.db import router
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.utils.datastructures import MultiValueDict
from django.utils.translation import gettext_lazy as _, ngettext
from django.core.exceptions import ValidationError

from massactions.forms import BSModalMassUpdateForm, BSModalMassDeleteForm
from massactions.helpers import decrypt_string


class MassActionListViewMixin(object):
    mass_actions = ['delete']
    mass_action_update_dict = []
    mass_action_object_name = ''
    mass_action_qs_method = ''

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        context_data['mass_action_context'] = {'model_name': self.model._meta.object_name,
                                               'app_label': self.model._meta.app_label,
                                               'object_name': self.mass_action_object_name,
                                               'actions': self.mass_actions,
                                               'update_fields_dict': self.mass_action_update_dict,
                                               'qs_method': self.mass_action_qs_method,
                                               'items_count': self.filter.qs.count()}
        return context_data


class MassActionViewMixin(PermissionRequiredMixin):
    permission_denied_message = _('You do not have permission to perform this action.')
    select_object_message = _('Please, select an object first.')
    restricted_object_list = None
    not_allowed_object_list = None

    def dispatch(self, request, *args, **kwargs):
        self.model_name = request.GET.get('model', None)
        self.app_label = request.GET.get('app_label', None)
        self.object_name = request.GET.get('object_name', None) if request.GET.get('object_name') else self.model_name
        self.qs_method = request.GET.get('qs_method', None)
        self.back_url = request.GET.get('back_url', None)
        self.user_mass_action_cookie = str(request.user.id) + "_" + self.object_name
        self.permission_required = self.get_required_permission_string()

        if not self.has_permission():
            return self.handle_no_permission()

        selection_cookie = request.COOKIES.get(self.user_mass_action_cookie)

        if selection_cookie:
            encrypted_selection = unquote(selection_cookie)
            selection = decrypt_string(encrypted_selection)
            selection_json = json.loads(selection) if selection else None

            if not selection_json['ids'] and not selection_json['selectAll']:
                return self.handle_no_object_selected()

            object_list = self.filter_object_list(selection_json)

            # restrict qs based on user permission for given objects
            self.restricted_object_list = self.restrict_objects_by_user_permission(object_list)
            self.not_allowed_object_list = object_list.exclude(pk__in=self.restricted_object_list.values('id'))

        return super().dispatch(request, *args, **kwargs)

    def filter_object_list(self, selection_json):
        self.model = apps.get_model(self.app_label, self.model_name)
        user = self.request.user
        object_list = self.model.objects.restrict_list_user(user).of_workspace(user.workspace)

        # filter qs based on given queryset method
        if self.qs_method:
            imported_module = importlib.import_module(self.model.__module__.replace('models', 'querysets'))
            queryset_class = getattr(imported_module, self.model.__name__ + 'QuerySet')
            queryset_method = getattr(queryset_class, self.qs_method)
            object_list = queryset_method(object_list)

        filter_data = None
        if self.back_url:
            filter_data = MultiValueDict(parse_qs(urlparse(self.back_url).query))

        # filter qs based on current filter data
        if filter_data:
            imported_module = importlib.import_module(self.model.__module__.replace('models', 'filters'))
            filter_class = getattr(imported_module, self.model.__name__ + 'Filter')
            object_list = filter_class(filter_data, queryset=object_list).qs

        if selection_json['selectAll']:
            object_list = object_list.exclude(pk__in=selection_json['ids'])
        else:
            object_list = object_list.filter(pk__in=selection_json['ids'])

        return object_list

    def handle_no_object_selected(self):
        messages.error(self.request, self.select_object_message)
        return redirect(self.request.GET.get('back_url', self.get_success_url()))

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect(self.request.GET.get('back_url', self.get_success_url()))

    def get_required_permission_string(self):
        return self.permission_required

    def restrict_objects_by_user_permission(self, object_list):
        return object_list


class BSModalMassActionViewMixin(MassActionViewMixin, BSModalFormView):
    template_name = 'massactions/helpers/crispy_form.html'

    def get_form_kwargs(self):
        return {'object_list': self.restricted_object_list,
                'not_allowed_object_list': self.not_allowed_object_list,
                'action': self.get_action()
                }

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['form'] = self.form_class(**self.get_form_kwargs())
        return context_data

    def get_required_permission_string(self):
        return self.app_label + '.' + self.get_action() + '_' + self.model_name.lower()

    def get_success_url(self):
        return self.request.GET.get('back_url', reverse('manager:dashboard'))

    def handle_no_permission(self):
        return render(self.request, "bootstrap5/layout/modal_content.html",
                      {"modal_title": _('Permission missing'),
                       "modal_message": self.permission_denied_message,
                       "modal_close": True
                       })

    def handle_no_object_selected(self):
        return render(self.request, "bootstrap5/layout/modal_content.html",
                      {"modal_title": _('No object selected'),
                       "modal_message": self.select_object_message,
                       "modal_close": True
                       })


class MassDeleteView(BSModalMassActionViewMixin):
    form_class = BSModalMassDeleteForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'protected_object_list': self.get_protected_objects(self.restricted_object_list)})
        return kwargs

    def get_action(self):
        return 'delete'

    def restrict_objects_by_user_permission(self, object_list):
        return object_list

    def post(self, request, *args, **kwargs):
        return self.delete(request)

    def delete(self, request, *args, **kwargs):
        # TODO: add tracking
        is_success = True
        try:
            count = self.restricted_object_list.count()

            # Cannot call delete() on a QuerySet that has had a slice taken or can otherwise no longer be filtered.
            # E.g. after distinct() on QuerySet. In that case delete items individually.
            try:
                self.restricted_object_list.delete()
            except TypeError:
                for obj in self.restricted_object_list:
                    obj.delete()

            message = ngettext(
                '%(count)d object was successfully deleted.',
                '%(count)d objects were successfully deleted.',
                count,
            ) % {'count': count, }
            messages.success(request, message)

        except ProtectedError:
            is_success = False
            message = _('Objects could not be deleted, because they are associated with other objects.')
            messages.error(request, message)

        response = redirect(self.get_success_url())
        response.set_cookie(self.user_mass_action_cookie, is_success)
        return response

    def get_protected_objects(self, objs):
        if not objs.exists():
            return objs

        using = router.db_for_write(objs[0]._meta.model)
        collector = NestedObjects(using=using)
        collector.collect(objs)
        return collector.protected


class MassUpdateFieldView(BSModalMassActionViewMixin):
    form_class = BSModalMassUpdateForm

    def dispatch(self, request, *args, **kwargs):
        self.field_name = request.GET.get('field_name', None)
        self.field_name_localized = request.GET.get('field_name_localized', None)
        self.field_name_value = request.GET.get('field_name_value', None)
        self.custom_form = request.GET.get('custom_form', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        if self.custom_form:
            imported_module = importlib.import_module(self.model.__module__.replace('models', 'forms'))
            self.form_class = getattr(imported_module, 'MassAction' + self.object_name + 'Form')
        return self.form_class

    def get_form(self, form_class=None):
        return self.get_form_class()(**self.get_form_kwargs())

    def get_action(self):
        return 'update'

    def restrict_objects_by_user_permission(self, object_list):
        return object_list

    def get_required_permission_string(self):
        return self.app_label + '.change_' + self.model_name.lower()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'field_name': self.field_name})
        kwargs.update({'field_name_value': self.field_name_value})
        kwargs.update({'field_name_localized': self.field_name_localized})
        kwargs.update({'form_model': self.model})
        return kwargs

    def get_localized_field_value(self):
        for choice in getattr(self.model, self.field_name).field.choices:
            if choice[0] == self.field_name_value:
                return choice[0]
        return self.field_name_value

    def post(self, request, *args, **kwargs):
        return self.bulk_update_field(request)

    def bulk_update_field(self, request, *args, **kwargs):
        for obj in self.restricted_object_list:
            form = self.get_form_class()(request.POST, **self.get_form_kwargs())

            if form.is_valid():
                obj.save()
            else:
                raise ValidationError(_('Invalid form'))

        count = self.restricted_object_list.count()
        message = ngettext(
            '%(count)d object was successfully updated.',
            '%(count)d objects were successfully updated.',
            count,
        ) % {'count': count, }
        messages.success(request, message)

        response = redirect(self.get_success_url())
        response.set_cookie(self.user_mass_action_cookie, True)
        return response
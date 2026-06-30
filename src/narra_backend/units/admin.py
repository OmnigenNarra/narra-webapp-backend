# -*- coding: utf-8 -*-

'''Admin module
'''

from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _u
from django.views.decorators.debug import sensitive_post_parameters

from .models import (
    Organization,
    OrganizationGroup,
    Member,
    Team,
    TeamMember,
    Token,
)


class MemberAdmin(admin.ModelAdmin):
    '''Member admin class
    '''
    list_display = ('id', 'email', 'is_active', 'org_admin')
    search_fields = ('email',)
    fieldsets = (
        (_u('General'), {'fields': (
            'email', 'is_active', 'jtime', 'last_login', 'passwd_exp',
            'organization', 'org_admin')}),
    )
    readonly_fields = ('jtime', 'last_login')
    ordering = ('id',)
    filter_horizontal = []
    change_member_passwd_template = None
    change_passwd_form = AdminPasswordChangeForm

    def get_urls(self):
        return [
            path(
                r'<path:member_id>/password/',
                self.admin_site.admin_view(self.member_change_passwd),
                name='units_member_passwd_change'),
        ] + super().get_urls()

    @method_decorator(sensitive_post_parameters())
    def member_change_passwd(self, request, member_id=0, form_url=''):
        '''Member password change action
        '''
        if not self.has_change_permission(request):
            raise PermissionDenied
        member = self.get_object(request, unquote(member_id))
        if member is None:
            raise Http404(_u(
                '%(name)s object with primary key %(key)r' +
                'does not exist.') % {
                    'name': force_text(self.model._meta.verbose_name),
                    'key': escape(member_id),
                })
        if request.method == 'POST':
            form = self.change_passwd_form(member, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(
                    request, form, None)
                self.log_change(request, member, change_message)
                msg = _u('Password changed successfully.')
                messages.success(request, msg)
                update_session_auth_hash(request, form.user)
                return HttpResponseRedirect(
                    reverse('admin:units_member_changelist'))
        else:
            form = self.change_passwd_form(member)

        fieldsets = [(None, {'fields': list(form.base_fields)})]
        admin_form = admin.helpers.AdminForm(form, fieldsets, {})

        context = {
            'title': _u('Change password: %s') % escape(member.get_username()),
            'adminForm': admin_form,
            'form_url': form_url,
            'form': form,
            'is_popup': (
                IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': member,
            'save_as': False,
            'show_save': True,
        }
        context.update(admin.site.each_context(request))

        request.current_app = self.admin_site.name

        return TemplateResponse(
            request,
            self.change_member_passwd_template or
            'admin/auth/user/change_password.html',
            context)

    def save_model(self, request, obj, form, change):
        _upd_fields = [
            'email', 'is_active', 'passwd_exp', 'organization', 'org_admin']
        for field in _upd_fields:
            if field in form.cleaned_data and hasattr(obj, field):
                setattr(obj, field, form.cleaned_data[field])

        if obj.id:
            obj.save(update_fields=_upd_fields)
        else:
            obj.save()


class TeamMemberInline(admin.TabularInline):
    '''TeamMember inline admin class
    '''
    model = TeamMember
    extra = 0


class TeamAdmin(admin.ModelAdmin):
    '''Team admin class
    '''
    list_display = ('id', 'name', 'ctime')
    inlines = [TeamMemberInline]


admin.site.register(Organization)
admin.site.register(OrganizationGroup)
admin.site.register(Member, MemberAdmin)
admin.site.register(Token)
admin.site.register(Team, TeamAdmin)

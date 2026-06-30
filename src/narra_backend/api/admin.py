# -*- coding: utf-8 -*-

'''Admin module
'''

import json
import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.utils import display_for_value
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _u

from ..units.models import (
    Organization,
    OrganizationGroup,
)

from .models import (
    Node,
    NodeAsset,
    NodeLink,
    Package,
    PackageAction,
    PackageAsset,
    PackageAssetType,
    PackageHelper,
    PackageHelperNode,
    Release,
    ReleaseUID,
)
from .utils.packages import parse_package_upload, update_package_obj
from .utils.views import package_download_view


LOG = logging.getLogger(__name__)


class PackageFormAdmin(forms.ModelForm):
    '''Package form class
    '''
    upload = forms.FileField(max_length=512, required=False)

    class Meta:
        model = Package
        fields = ('upload', 'author')
        readonly_fields = ('filename', 'ctime', 'mtime')

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if (not self.instance and not cleaned_data.get('upload')) or (
                (
                    not self.instance or not self.instance.id
                ) and not cleaned_data.get('upload')):
            raise forms.ValidationError({'upload': _u('No file provided')})

        return cleaned_data


class PackageAdmin(admin.ModelAdmin):
    '''Package admin class
    '''
    list_display = (
        'id', 'story_name', 'json_ver', 'story_ver', 'author',
        'ctime', 'mtime', 'package_actions')
    fields = ('upload', 'filename', 'author', 'ctime', 'mtime')
    readonly_fields = (
        'filename', 'json_ver', 'story_ver', 'uasset_ver',
        'ctime', 'mtime', 'locked_at', 'locked_by')
    search_fields = ('story_name', 'filename')

    def get_form(self, request, obj=None, change=False, **kwargs):
        kwargs['form'] = PackageFormAdmin
        return super().get_form(request, obj, **kwargs)

    def has_change_permission(self, request, obj=None):
        return False

    def add_view(self, request, form_url='', extra_context=None):
        self.fields = ('upload', 'author')
        try:
            return super().add_view(
                request, form_url=form_url, extra_context=extra_context)
        except (
                AttributeError, LookupError, TypeError, ValueError,
                json.JSONDecodeError) as exc:
            LOG.exception(exc)
            if not isinstance(exc, AttributeError):
                messages.error(request, _u('%s - %s') % (
                    exc.__class__.__name__, str(exc)))
            return HttpResponseRedirect(request.path)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.fields = list(self.readonly_fields) + ['author']
        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if obj and obj.id:
            return

        ufile = form.cleaned_data.get('upload')
        if not ufile:
            return

        form.instance, package_dc, op_msg = parse_package_upload(
            ufile, form.cleaned_data.get('author'))
        if form.instance is None:
            messages.error(request, op_msg)

            return

        messages.success(request, op_msg)

        update_package_obj(
            obj, form.instance.filename, form.instance.author, package_dc)
        obj.id = form.instance.id
        obj.locked_by = form.instance.author

        super().save_model(request, obj, form, change)

    def get_urls(self):
        custom_urls = [
            path(
                r'<path:object_id>/download',
                self.admin_site.admin_view(self.download_view),
                name='api_package_download',
            ),
        ]

        return custom_urls + super().get_urls()

    @classmethod
    def package_actions(cls, obj):
        '''Adds actions column
        '''
        if not obj:
            return '---'

        dn_href = reverse('admin:api_package_download', args=[obj.id])

        return format_html(
            '<a class="button" href="{}" id="package_download_{}">{}</a>',
            dn_href, obj.id, _u('Download'),
            )

    package_actions.short_description = _u('Actions')
    package_actions.allow_tags = True

    @classmethod
    def download_view(cls, request, object_id):
        '''Package download view
        '''
        return package_download_view(request, object_id)


class ReleaseForm(forms.ModelForm):
    '''Release form class
    '''
    unreal_ver = forms.CharField(
        label=_u('Unreal version'), max_length=32, required=True)
    release_ver = forms.CharField(
        label=_u('Release version'), max_length=32, required=True)
    changes = forms.CharField(
        label=_u('Changes'), max_length=512, required=True,
        widget=forms.Textarea)

    class Meta:
        model = Release
        fields = '__all__'


class ReleaseAdmin(admin.ModelAdmin):
    '''Release admin class
    '''
    list_display = ('id', 'unreal_ver', 'release_ver', 'ctime')
    search_fields = ('unreal_ver', 'release_ver')
    ordering = ('release_ver', 'unreal_ver')
    readonly_fields = ('ctime',)
    filter_horizontal = []
    form = ReleaseForm


class ReleaseUIDForm(forms.ModelForm):
    '''ReleaseUID form class
    '''
    release = forms.ModelChoiceField(
        label=_u('Release'), required=True,
        queryset=Release.objects)
    organization_groups = forms.ModelMultipleChoiceField(
        label=_u('Organization groups'),
        queryset=OrganizationGroup.objects,
        required=False)
    organizations = forms.ModelMultipleChoiceField(
        label=_u('Organizations'), queryset=Organization.objects,
        required=False)

    class Meta:
        model = ReleaseUID
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['organizations'] = set(
            list(cleaned_data['organizations']) +
            list(Organization.objects.filter(
                organization_groups__in=cleaned_data['organization_groups'])))

        return cleaned_data


def releaseuid_url(obj):
    '''ReleaseUID URL column value
    '''
    return mark_safe(
        '<a target="_blank" href="' + obj.url + '">' +
        display_for_value(bool(obj.url), '', boolean=True) + '</a>') \
        if obj.url else display_for_value(False, '', boolean=True)

releaseuid_url.short_description = _u('URL')


class ReleaseUIDAdmin(admin.ModelAdmin):
    '''ReleaseUID admin class
    '''
    list_display = (
        'id', 'release', 'organization', releaseuid_url, 'uid', 'ctime')
    search_fields = ('uid',)
    ordering = ('release_id', 'organization')
    filter_horizontal = []
    form = ReleaseUIDForm

    def has_change_permission(self, request, obj=None):
        return False

    def add_view(self, request, form_url='', extra_context=None):
        self.fields = ('release', 'organization_groups', 'organizations')

        return super().add_view(
            request, form_url=form_url, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(
            request, _u('The release(s) was/were added successfully.'),
            messages.SUCCESS)

        return HttpResponseRedirect(
            reverse('admin:api_releaseuid_changelist'))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.fields = ('ctime', 'organization', 'release', 'uid', 'url')

        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if obj and obj.id:
            return

        tz_now = timezone.now()
        for organization in form.cleaned_data['organizations']:
            release = form.cleaned_data['release']
            ReleaseUID.objects.create(
                organization=organization, ctime=tz_now, release=release,
                uid=ReleaseUID.gen_uid(release, organization), url='')


admin.site.register(Package, PackageAdmin)
admin.site.register(PackageAction)
admin.site.register(PackageAsset)
admin.site.register(PackageAssetType)
admin.site.register(PackageHelper)
admin.site.register(PackageHelperNode)
admin.site.register(Node)
admin.site.register(NodeAsset)
admin.site.register(NodeLink)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(ReleaseUID, ReleaseUIDAdmin)

admin.site.index_title = _u('Narra')
admin.site.site_title = _u('stories administration')
admin.site.site_header = _u('Narra (JSON: v%s, Story: v%s)') % (
    settings.PACKAGE_JSON_VER_MIN + ' ... ' +
    settings.PACKAGE_JSON_VER if settings.PACKAGE_JSON_VER_MIN !=
    settings.PACKAGE_JSON_VER else settings.PACKAGE_JSON_VER,
    settings.PACKAGE_VERSIONS[settings.PACKAGE_JSON_VER]['StoryVersion'],
)

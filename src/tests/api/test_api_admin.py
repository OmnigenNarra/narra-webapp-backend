# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import json
import random

import pytest
from rest_framework import status

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import FileField
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseForbidden,
)
from django.test import Client
from django.test.client import RequestFactory
from django.urls import reverse

from narra_backend.api.admin import (
    PackageFormAdmin,
    PackageAdmin,
)
from narra_backend.api.models import (
    NodeType,
    Package,
)
from narra_backend.api.utils.views import (
    JSONResponse,
)

from .commons import (
    NODE_DEF,
    PACKAGE_DEF,
    TEST_DATA_FNAME,
    TEST_DATA_FPATH,
)


REQ_FACTORY = None


def setup_module(module):
    '''Module setup method
    '''
    module.REQ_FACTORY = RequestFactory()


def test_packageformadmin_empty_no_inst():
    '''Tests PackageFormAdmin empty form (no instance)
    '''
    form = PackageFormAdmin()
    form.full_clean()

    assert sorted(form.fields.keys()) == ['author', 'upload']
    assert isinstance(form.declared_fields['upload'], FileField)
    assert not form.is_valid()


def test_packageformadmin_invalid_no_inst():
    '''Tests PackageFormAdmin invalid form (no instance)
    '''
    form = PackageFormAdmin(data={}, files={
        'upload': SimpleUploadedFile(TEST_DATA_FNAME, ''),
    })
    form.full_clean()

    assert isinstance(form.declared_fields['upload'], FileField)
    assert 'upload' in form.errors
    assert not form.is_valid()


def test_packageformadmin_valid_no_inst():
    '''Tests PackageFormAdmin valid form (no instance)
    '''
    form = PackageFormAdmin(data={}, files={
        'upload': SimpleUploadedFile(
            TEST_DATA_FNAME, b'{}', content_type='application/json'),
    })
    form.full_clean()

    assert form.is_valid()
    assert isinstance(form.declared_fields['upload'], FileField)
    assert 'upload' not in form.errors
    assert 'upload' in form.cleaned_data


def test_packageformadmin_empty_with_inst():
    '''Tests PackageFormAdmin empty form (with instance)
    '''
    form = PackageFormAdmin(instance=Package(id=123))
    form.full_clean()

    assert sorted(form.fields.keys()) == ['author', 'upload']
    assert isinstance(form.declared_fields['upload'], FileField)
    assert not form.is_valid()


def test_packageformadmin_invalid_with_inst():
    '''Tests PackageFormAdmin invalid form (with instance)
    '''
    form = PackageFormAdmin(data={}, files={
        'upload': SimpleUploadedFile(TEST_DATA_FNAME, ''),
    }, instance=Package(id=123))
    form.full_clean()

    assert isinstance(form.declared_fields['upload'], FileField)
    assert 'upload' in form.errors
    assert not form.is_valid()


def test_packageformadmin_valid_with_inst():
    '''Tests PackageFormAdmin valid form (with instance)
    '''
    form = PackageFormAdmin(data={}, files={
        'upload': SimpleUploadedFile(
            TEST_DATA_FNAME, b'{}', content_type='application/json'),
    }, instance=Package(id=123))
    form.full_clean()

    assert isinstance(form.declared_fields['upload'], FileField)
    assert 'upload' not in form.errors
    assert 'upload' in form.cleaned_data
    assert form.is_valid()


def test_packageadmin_form_basic():
    '''Tests PackageAdmin form (basic)
    '''
    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get('/')

    assert list(mod_adm.get_form(request).base_fields) == ['upload', 'author']


def test_packageadmin_permissions():
    '''Tests PackageAdmin class - permissions check
    '''
    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get('/')

    assert not mod_adm.has_change_permission(request)


@pytest.mark.django_db
def test_packageadmin_add_view_no_auth():
    '''Tests PackageAdmin class - add view, no auth
    '''
    cli = Client()
    response = cli.get(reverse('admin:api_package_add'))

    if settings.HTTP_AUTHZ:
        assert isinstance(response, HttpResponse)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    else:
        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.startswith(reverse('admin:login'))


@pytest.mark.django_db
def test_packageadmin_add_view_ok_auth():
    '''Tests PackageAdmin class - add view, OK auth
    '''
    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get('/')
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.add_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Add Package'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_upload"' in response.content


@pytest.mark.django_db
def test_packageadmin_add_view_ok_auth_bad_req():
    '''Tests PackageAdmin class - add view, OK auth
    '''
    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get('/')
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.add_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Add Package'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_upload"' in response.content


@pytest.mark.django_db
def test_packageadmin_add_view_no_upload():
    '''Tests PackageAdmin class - add view, OK auth, no upload
    '''
    field_name = 'some_field_' + str(random.randint(1e5, 1e6))
    field_value = bytes(random.randint(1e2, 1e3))
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {field_name: field_value}, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'No file provided' in response.content


@pytest.mark.django_db
def test_packageadmin_add_view_empty_upload():
    '''Tests PackageAdmin class - add view, OK auth, empty upload
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_json = SimpleUploadedFile(TEST_DATA_FNAME, b'')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {'upload': package_json}, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content


@pytest.mark.django_db
def test_packageadmin_add_view_empty_json():
    '''Tests PackageAdmin class - add view, OK auth, empty JSON
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_json = SimpleUploadedFile(TEST_DATA_FNAME, b'{}')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {'upload': package_json}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_package_add')


@pytest.mark.django_db
def test_packageadmin_add_view_malformed_json():
    '''Tests PackageAdmin class - add view, OK auth, malformed JSON
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = ''
    _node_def['Type'] = NodeType.End.value
    package_dc['Nodes'].append(_node_def)

    json_str = json.dumps(package_dc)
    package_json = SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(
            json_str[:-int(len(json_str) / 2)], encoding='utf-8'),
        content_type='application/json')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {'upload': package_json}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_package_add')


@pytest.mark.django_db
def test_packageadmin_add_view_bad_upload():
    '''Tests PackageAdmin class - add view, OK auth, bad upload
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    del package_dc['UAssetVersion']

    package_json = SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='utf-8'),
        content_type='application/json')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {'upload': package_json}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_package_add')


@pytest.mark.skipif(
    not settings.USE_JSONSCHEMA,
    reason='jsonschema usage disabled')
@pytest.mark.django_db
def test_packageadmin_add_view_schema_ok_missing_field():
    '''Tests PackageAdmin class - add view, OK auth, schema OK,
        missing field
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_DialogueLine_0'
    _node_def['Type'] = NodeType.DialogueLine.value
    package_dc['Nodes'].append(_node_def)

    package_json = SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='utf-8'),
        content_type='application/json')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {'upload': package_json},
        **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_package_add')


@pytest.mark.django_db
def test_packageadmin_add_view_ok_upload():
    '''Tests PackageAdmin class - add view, OK auth, OK upload
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_json = open(TEST_DATA_FPATH, 'rb')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_add'), {'upload': package_json}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_package_changelist')


@pytest.mark.django_db
def test_packageadmin_change_view_existing_object_no_upload():
    '''Tests PackageAdmin class - change_view / save_model, OK auth,
        no upload to existing object
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    package_obj.save()

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_change', args=[package_obj.id]), **kwargs)

    assert isinstance(response, HttpResponseForbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_packageadmin_change_view_existing_object_upload():
    '''Tests PackageAdmin class - change_view / save_model, OK auth,
        upload to existing object
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    package_obj.save()

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    package_json = open(TEST_DATA_FPATH, 'rb')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_package_change', args=[package_obj.id]),
        {'upload': package_json}, **kwargs)

    assert isinstance(response, HttpResponseForbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_packageadmin_change_view():
    '''Tests PackageAdmin class - change view check
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    package_obj.save()

    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get(reverse(
        'admin:api_package_change', args=[package_obj.id]))
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.change_view(request, str(package_obj.id))
    response = tresp.render()

    assert tresp.context_data['title'] == 'View Package'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_upload"' not in response.content


@pytest.mark.django_db
def test_packageadmin_save_model_no_obj_id_no_upload():
    '''Tests PackageAdmin class - save_model, no object ID, no upload
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    form = PackageFormAdmin(data={}, files={})
    form.full_clean()

    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.post(reverse('admin:api_package_add'))
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    mod_adm.save_model(request, package_obj, form, False)

    assert package_obj.pk is None


@pytest.mark.django_db
def test_packageadmin_package_actions_no_obj():
    '''Tests PackageAdmin class - package_actions without object
    '''
    mod_adm = PackageAdmin(Package, AdminSite())
    ret = mod_adm.package_actions(None)

    assert isinstance(ret, str)
    assert 'Download' not in ret


@pytest.mark.django_db
def test_packageadmin_package_actions_ok_obj():
    '''Tests PackageAdmin class - package_actions with object
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    package_obj.save()

    mod_adm = PackageAdmin(Package, AdminSite())
    ret = mod_adm.package_actions(package_obj)

    assert isinstance(ret, str)
    assert 'id="package_download_%d"' % package_obj.id in ret


@pytest.mark.django_db
def test_packageadmin_changelist_view():
    '''Tests PackageAdmin class - changelist view check
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    package_obj.save()

    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get(reverse('admin:api_package_changelist'))
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.changelist_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Select Package to view'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="package_download_%d"' % package_obj.id in response.content


@pytest.mark.django_db
def test_packageadmin_download_view():
    '''Tests PackageAdmin class - download view check
    '''
    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()

    package_def = copy.deepcopy(PACKAGE_DEF)
    package_def['ModTime'] = str(int(package_obj.mtime.timestamp()))

    mod_adm = PackageAdmin(Package, AdminSite())
    request = REQ_FACTORY.get(reverse(
        'admin:api_package_download', args=[package_obj.id]))
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    response = mod_adm.download_view(request, package_obj.id)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'"Assets"' in response.content
    assert b'"Nodes"' in response.content
    assert b'"JSONVersion"' in response.content
    assert b'"StoryVersion"' in response.content
    assert b'"UAssetVersion"' in response.content

    package_dc = json.loads(response.content)

    assert package_dc == package_def

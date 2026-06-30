# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest
from rest_framework import status

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.test import Client
from django.test.client import RequestFactory
from django.urls import reverse

from narra_backend.api.admin import (
    ReleaseUIDAdmin,
    releaseuid_url,
)
from narra_backend.api.models import (
    Release,
    ReleaseUID,
)
from narra_backend.units.models import (
    Organization,
    OrganizationGroup,
)


REQ_FACTORY = None


def setup_module(module):
    '''Module setup method
    '''
    module.REQ_FACTORY = RequestFactory()


def test_releaseuidadmin_form_basic():
    '''Tests ReleaseUIDAdmin form (basic)
    '''
    mod_adm = ReleaseUIDAdmin(ReleaseUID, AdminSite())
    request = REQ_FACTORY.get('/')

    assert list(mod_adm.get_form(request).base_fields) == [
        'organization',
        'ctime',
        'release',
        'uid',
        'url',
        'organization_groups',
        'organizations',
    ]


@pytest.mark.django_db
def test_releaseuidadmin_add_view_no_auth():
    '''Tests ReleaseUIDAdmin class - add view, no auth
    '''
    cli = Client()
    response = cli.get(reverse('admin:api_releaseuid_add'))

    if settings.HTTP_AUTHZ:
        assert isinstance(response, HttpResponse)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    else:
        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.startswith(reverse('admin:login'))


@pytest.mark.django_db
def test_releaseuidadmin_add_view_ok_auth():
    '''Tests ReleaseUIDAdmin class - add view, OK auth
    '''
    mod_adm = ReleaseUIDAdmin(ReleaseUID, AdminSite())
    request = REQ_FACTORY.get('/')
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.add_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Add Release UID'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_organization_groups"' in response.content


@pytest.mark.django_db
def test_releaseuidadmin_add_view_ok_auth_bad_req():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, bad request
    '''
    mod_adm = ReleaseUIDAdmin(ReleaseUID, AdminSite())
    request = REQ_FACTORY.get('/')
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.add_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Add Release UID'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_organization_groups"' in response.content


@pytest.mark.django_db
def test_releaseuidadmin_add_view_no_params():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, no params
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
        reverse('admin:api_releaseuid_add'), {field_name: field_value},
        **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'field is required' in response.content


@pytest.mark.django_db
def test_releaseuidadmin_add_view_empty_release():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, empty release
    '''
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': 0,
        }, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'not one of the available choices' in response.content


@pytest.mark.django_db
def test_releaseuidadmin_add_view_no_perms():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, no perms
    '''
    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {}, **kwargs)

    assert isinstance(response, HttpResponseForbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_releaseuidadmin_add_view_with_perms_no_org():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, with perms,
        no organization nor organization group
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    cnt = ReleaseUID.objects.filter(organization=organization).count()

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    staffuser.user_permissions.add(view_perm, add_perm, change_perm)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': release.id,
        }, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_releaseuid_changelist')
    assert ReleaseUID.objects.filter(organization=organization).count() == cnt


@pytest.mark.django_db
def test_releaseuidadmin_add_view_with_perms_single_org():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, with perms,
        single organization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    cnt = ReleaseUID.objects.filter(organization=organization).count()

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    staffuser.user_permissions.add(view_perm, add_perm, change_perm)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': release.id,
            'organizations': [organization.id],
        }, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_releaseuid_changelist')
    assert ReleaseUID.objects.filter(
        organization=organization).count() == cnt + 1


@pytest.mark.django_db
def test_releaseuidadmin_add_view_with_perms_multi_orgs():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, with perms,
        multiple organizations
    '''
    mul = random.randint(1e1, 1e2)

    org_names = []
    organizations = []
    for _ in range(mul):
        org_name = ''
        while not org_name or org_name in org_names:
            org_name = 'Organization #' + str(random.randint(1e5, 1e6))
        organizations.append(Organization.objects.create(name=org_name))

    cnt = ReleaseUID.objects.filter(organization__in=organizations).count()

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    staffuser.user_permissions.add(view_perm, add_perm, change_perm)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': release.id,
            'organizations': [obj.id for obj in organizations],
        }, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_releaseuid_changelist')
    assert ReleaseUID.objects.filter(
        organization__in=organizations).count() == cnt + mul


@pytest.mark.django_db
def test_releaseuidadmin_add_view_with_perms_by_org_group():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, with perms,
        by organization group
    '''
    organization_group = OrganizationGroup.objects.create(
        name='Group #' + str(random.randint(1e5, 1e6)))
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization1.organization_groups.add(organization_group)
    organization2.organization_groups.add(organization_group)
    cnt = ReleaseUID.objects.filter(
        organization__in=[organization1, organization2]).count()

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    staffuser.user_permissions.add(view_perm, add_perm, change_perm)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': release.id,
            'organization_groups': [organization_group.id],
        }, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_releaseuid_changelist')
    assert ReleaseUID.objects.filter(
        organization__in=[organization1, organization2]).count() == cnt + 2


@pytest.mark.django_db
def test_releaseuidadmin_add_view_with_perms_by_joined_orgs_groups():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, with perms,
        by joined organization(s) and organization group(s)
    '''
    mul = random.randint(1e1, 1e2) * 3

    org_names = []
    organizations = []
    for _ in range(mul):
        org_name = ''
        while not org_name or org_name in org_names:
            org_name = 'Organization #' + str(random.randint(1e5, 1e6))
        organizations.append(Organization.objects.create(name=org_name))

    cnt = ReleaseUID.objects.filter(organization__in=organizations).count()

    organization_group1 = OrganizationGroup.objects.create(
        name='Group #' + str(random.randint(1e5, 1e6)))
    organization_group2 = OrganizationGroup.objects.create(
        name='Group #' + str(random.randint(1e5, 1e6)))
    third = int(mul / 3)
    for idx in range(third):
        organizations[idx].organization_groups.add(organization_group1)
        organizations[idx + third].organization_groups.add(organization_group2)

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    staffuser.user_permissions.add(view_perm, add_perm, change_perm)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': release.id,
            'organization_groups': [
                organization_group1.id,
                organization_group2.id,
            ],
            'organizations': [obj.id for obj in organizations],
        }, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_releaseuid_changelist')
    assert ReleaseUID.objects.filter(
        organization__in=organizations).count() == cnt + mul


@pytest.mark.django_db
def test_releaseuidadmin_add_view_with_perms_by_splitted_orgs_groups():
    '''Tests ReleaseUIDAdmin class - add view, OK auth, OK params, with perms,
        by splitted organization(s) and organization group(s)
    '''
    mul = random.randint(1e1, 1e2) * 3

    org_names = []
    organizations = []
    for _ in range(mul):
        org_name = ''
        while not org_name or org_name in org_names:
            org_name = 'Organization #' + str(random.randint(1e5, 1e6))
        organizations.append(Organization.objects.create(name=org_name))

    cnt = ReleaseUID.objects.filter(organization__in=organizations).count()

    organization_group1 = OrganizationGroup.objects.create(
        name='Group #' + str(random.randint(1e5, 1e6)))
    organization_group2 = OrganizationGroup.objects.create(
        name='Group #' + str(random.randint(1e5, 1e6)))
    third = int(mul / 3)
    for idx in range(third):
        organizations[idx].organization_groups.add(organization_group1)
        organizations[idx + third].organization_groups.add(organization_group2)

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'teststaffuser' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    staffuser.user_permissions.add(view_perm, add_perm, change_perm)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.post(
        reverse('admin:api_releaseuid_add'), {
            'release': release.id,
            'organization_groups': [
                organization_group1.id,
                organization_group2.id,
            ],
            'organizations': [obj.id for obj in organizations[2 * third:]],
        }, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:api_releaseuid_changelist')
    assert ReleaseUID.objects.filter(
        organization__in=organizations).count() == cnt + mul


@pytest.mark.django_db
def test_releaseuidadmin_change_view_save():
    '''Tests ReleaseUIDAdmin class - change view, save
    '''
    unreal_ver1 = str(random.random())
    unreal_ver2 = unreal_ver1
    while unreal_ver2 == unreal_ver1:
        unreal_ver2 = str(random.random())

    release_ver1 = 'R#' + str(random.randint(1e5, 1e6))
    release_ver2 = release_ver1
    while release_ver2 == release_ver1:
        release_ver2 = 'R#' + str(random.randint(1e5, 1e6))

    release1 = Release.objects.create(
        unreal_ver=unreal_ver1, release_ver=release_ver1, changes='')
    release2 = Release.objects.create(
        unreal_ver=unreal_ver1, release_ver=release_ver1, changes='')

    releaseuid = ReleaseUID.objects.create(release=release1)

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:api_releaseuid_change', args=[releaseuid.id]),
        {
            'release': release2.id,
        }, **kwargs)

    assert isinstance(response, HttpResponseForbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = cli.get(
        reverse('admin:api_releaseuid_change', args=[releaseuid.id]),
        **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert bytes(str(release1), encoding='utf-8') in response.content


def test_releaseuid_url_render_empty_url():
    '''Tests releaseuid_url method - column render, empty ReleaseUID.url
    '''
    obj = ReleaseUID(url='')

    html = releaseuid_url(obj)

    assert html
    assert 'icon-no' in html


def test_releaseuid_url_render_filled_url():
    '''Tests releaseuid_url method - column render, filled ReleaseUID.url
    '''
    url = 'https://' + str(random.random())
    obj = ReleaseUID(url=url)

    html = releaseuid_url(obj)

    assert html
    assert 'icon-yes' in html
    assert url in html

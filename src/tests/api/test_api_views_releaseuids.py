# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest

from rest_framework import status
from rest_framework.authtoken.models import Token as DRFToken
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import Client
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _u

from narra_backend.api.models import (
    Release,
    ReleaseUID,
)
from narra_backend.units.models import (
    Member,
    Organization,
)


@pytest.mark.django_db
def test_releaseuids_list_no_auth():
    '''Tests release UIDs list - no authorization
    '''
    url = reverse('api:releaseuids')

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(url, **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_releaseuids_list_non_staff_user():
    '''Tests release UIDs list - non-staff user
    '''
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=False, is_superuser=False)

    token = DRFToken.objects.create(user=user)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail'] == _u('Not an active release UIDs maintainer')


@pytest.mark.django_db
def test_releaseuids_list_inactive_staff_user():
    '''Tests release UIDs list - inactive staff user
    '''
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=False, is_staff=True, is_superuser=False)

    token = DRFToken.objects.create(user=user)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail']
    assert 'inactive' in json_resp['detail']


@pytest.mark.django_db
def test_releaseuids_list_staff_user_without_perms():
    '''Tests release UIDs list - staff user without perms
    '''
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True, is_superuser=False)

    token = DRFToken.objects.create(user=user)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail'] == _u('Not an active release UIDs maintainer')


@pytest.mark.django_db
def test_releaseuids_list_staff_user_with_perms_no_releases():
    '''Tests release UIDs list - staff user with perms,
        no releases
    '''
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True, is_superuser=False)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    user.user_permissions.add(view_perm, add_perm, change_perm)

    token = DRFToken.objects.create(user=user)

    assert user.has_perms((
        'api.view_releaseuid',
        'api.add_releaseuid',
        'api.change_releaseuid',
    ))

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp == []


@pytest.mark.django_db
def test_releaseuids_list_staff_user_with_perms_some_releases():
    '''Tests release UIDs list - staff user with perms,
        some releases
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    unreal_ver = str(random.random())
    release_vers = set()
    for _ in range(random.randint(1e1, 1e2)):
        release_ver = ''
        while not release_ver or release_ver in release_vers:
            release_ver = 'R#' + str(random.randint(1e5, 1e6))
        release = Release.objects.create(
            unreal_ver=unreal_ver, release_ver=release_ver, changes='')
        ReleaseUID.objects.create(organization=organization, release=release)
        release_vers.add(release_ver)

    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True, is_superuser=False)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    user.user_permissions.add(view_perm, add_perm, change_perm)

    token = DRFToken.objects.create(user=user)

    assert user.has_perms((
        'api.view_releaseuid',
        'api.add_releaseuid',
        'api.change_releaseuid',
    ))

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp[0]['organization'] == {
        'id': organization.id,
        'name': organization.name,
    }
    assert set(ruid['release']['release_ver'] for ruid in json_resp) == \
        release_vers


@pytest.mark.django_db
def test_releaseuids_list_inactive_superuser():
    '''Tests release UIDs list - inactive superuser
    '''
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username, is_active=False)

    token = DRFToken.objects.create(user=superuser)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail']
    assert 'inactive' in json_resp['detail']


@pytest.mark.django_db
def test_releaseuids_list_ok_superuser_no_releases():
    '''Tests release UIDs list - OK superuser, no releases
    '''
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp == []


@pytest.mark.django_db
def test_releaseuids_list_ok_superuser_some_releases():
    '''Tests release UIDs list - OK superuser, some releases
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    unreal_ver = str(random.random())
    release_vers = set()
    for _ in range(random.randint(1e1, 1e2)):
        release_ver = ''
        while not release_ver or release_ver in release_vers:
            release_ver = 'R#' + str(random.randint(1e5, 1e6))
        release = Release.objects.create(
            unreal_ver=unreal_ver, release_ver=release_ver, changes='')
        ReleaseUID.objects.create(organization=organization, release=release)
        release_vers.add(release_ver)

    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp[0]['organization'] == {
        'id': organization.id,
        'name': organization.name,
    }
    assert set(ruid['release']['release_ver'] for ruid in json_resp) == \
        release_vers


@pytest.mark.django_db
def test_releaseuid_create_no_auth():
    '''Tests release UID create - no authorization
    '''
    url = reverse('api:releaseuids')

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_releaseuid_create_non_staff_user():
    '''Tests release UID create - non-staff user
    '''
    release = 'R#' + str(random.randint(1e5, 1e6))
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=False, is_superuser=False)

    token = DRFToken.objects.create(user=user)

    test_data = {
        'release': release,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail'] == _u('Not an active release UIDs maintainer')


@pytest.mark.django_db
def test_releaseuid_create_inactive_staff_user():
    '''Tests release UID create - inactive staff user
    '''
    release = 'R#' + str(random.randint(1e5, 1e6))
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=False, is_staff=True, is_superuser=False)

    token = DRFToken.objects.create(user=user)

    test_data = {
        'release': release,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail']
    assert 'inactive' in json_resp['detail']


@pytest.mark.django_db
def test_releaseuid_create_staff_user_without_perms():
    '''Tests release UID create - staff user without perms
    '''
    release = 'R#' + str(random.randint(1e5, 1e6))
    url = reverse('api:releaseuids')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True, is_superuser=False)

    token = DRFToken.objects.create(user=user)

    test_data = {
        'release': release,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail'] == _u('Not an active release UIDs maintainer')


@pytest.mark.django_db
def test_releaseuid_create_staff_user_with_perms():
    '''Tests release UID create - staff user with perms
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    url = reverse('api:releaseuids')

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'testuser_' + str(random.randint(1e5, 1e6))
    user = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True, is_superuser=False)
    content_type = ContentType.objects.get_for_model(ReleaseUID)
    view_perm, _ = Permission.objects.get_or_create(
        codename='view_releaseuid', content_type=content_type)
    add_perm, _ = Permission.objects.get_or_create(
        codename='add_releaseuid', content_type=content_type)
    change_perm, _ = Permission.objects.get_or_create(
        codename='change_releaseuid', content_type=content_type)
    user.user_permissions.add(view_perm, add_perm, change_perm)

    token = DRFToken.objects.create(user=user)

    assert user.has_perms((
        'api.view_releaseuid',
        'api.add_releaseuid',
        'api.change_releaseuid',
    ))

    test_data = {
        'organization': organization.id,
        'release': release.id,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['id']
    assert json_resp['ctime']
    assert json_resp['release'] == dict(release)
    assert json_resp['uid']


@pytest.mark.django_db
def test_releaseuid_create_inactive_superuser():
    '''Tests release UID create - inactive superuser
    '''
    release = 'R#' + str(random.randint(1e5, 1e6))
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username, is_active=False)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'release': release,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['detail']
    assert 'inactive' in json_resp['detail']


@pytest.mark.django_db
def test_releaseuid_create_ok_superuser():
    '''Tests release UID create - OK superuser
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    url = reverse('api:releaseuids')

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'organization': organization.id,
        'release': release.id,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['id']
    assert json_resp['ctime']
    assert json_resp['release'] == dict(release)
    assert json_resp['uid']


@pytest.mark.django_db
def test_releaseuid_update_no_url():
    '''Tests release UID update - no URL
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    releaseuid = ReleaseUID.objects.create(organization=organization)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'id': releaseuid.id,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'field is required' in response.content


@pytest.mark.django_db
def test_releaseuid_update_empty_url():
    '''Tests release UID update - empty URL
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    releaseuid = ReleaseUID.objects.create(organization=organization)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'id': releaseuid.id,
        'url': '',
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'may not be blank' in response.content


@pytest.mark.django_db
def test_releaseuid_update_bad_url():
    '''Tests release UID update - bad URL
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    releaseuid = ReleaseUID.objects.create(organization=organization)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'id': releaseuid.id,
        'url': 'URL#' + str(random.randint(1e5, 1e6)),
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'valid URL' in response.content


@pytest.mark.django_db
def test_releaseuid_update_ok_url_no_org_admins():
    '''Tests release UID update - OK URL, no org admins
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    releaseuid = ReleaseUID.objects.create(organization=organization)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    ruid_url = 'https://%s/%s' % (
        Site.objects.get_current().domain, random.randint(1e5, 1e6))

    test_data = {
        'id': releaseuid.id,
        'url': ruid_url,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['organization'] == {
        'id': organization.id,
        'name': organization.name,
    }

    assert json_resp['id'] == releaseuid.id
    assert json_resp['url'] == ruid_url


@pytest.mark.django_db
def test_releaseuid_update_ok_url_some_org_admins():
    '''Tests release UID update - OK URL, some org admins
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    mul = random.randint(1e1, 1e2)
    emails = set()
    for _ in range(mul):
        email = ''
        while not email or email in emails:
            email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
        Member.objects.create(
            email=email, is_active=True, org_admin=True, passwd_exp=None,
            organization=organization)
        emails.add(email)

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    releaseuid = ReleaseUID.objects.create(
        organization=organization, release=release)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    ruid_url = 'https://%s/%s' % (
        Site.objects.get_current().domain, random.randint(1e5, 1e6))

    test_data = {
        'id': releaseuid.id,
        'url': ruid_url,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['organization'] == {
        'id': organization.id,
        'name': organization.name,
    }

    assert json_resp['id'] == releaseuid.id
    assert json_resp['url'] == ruid_url


@pytest.mark.django_db
def test_releaseuid_update_url_not_changed():
    '''Tests release UID update - URL not changed
    '''
    domain = Site.objects.get_current().domain
    ruid_url1 = 'https://%s/%s' % (domain, random.randint(1e5, 1e6))
    ruid_url2 = ruid_url1
    while ruid_url2 == ruid_url1:
        ruid_url2 = 'https://%s/%s' % (domain, random.randint(1e5, 1e6))

    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    releaseuid = ReleaseUID.objects.create(
        organization=organization, url=ruid_url1)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'id': releaseuid.id,
        'url': ruid_url2,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp
    assert json_resp['organization'] == {
        'id': organization.id,
        'name': organization.name,
    }

    assert json_resp['id'] == releaseuid.id
    assert json_resp['url'] == ruid_url1


@pytest.mark.django_db
def test_releaseuid_delete():
    '''Tests release UID delete
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    releaseuid = ReleaseUID.objects.create(organization=organization)
    url = reverse('api:releaseuids')

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    token = DRFToken.objects.create(user=superuser)

    test_data = {
        'id': releaseuid.id,
    }

    cli = Client()
    cli.force_login(superuser)
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

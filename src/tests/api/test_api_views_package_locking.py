# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import random

import pytest

from rest_framework import status
from rest_framework.response import Response

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from narra_backend.api.models import (
    Package,
)
from narra_backend.units.models import (
    Member,
    Team,
    Token,
)

from .commons import (
    PACKAGE_DEF,
    TEST_DATA_FNAME,
)


@pytest.mark.django_db
def test_add_package_auto_lock():
    '''Tests add package - auto locking
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    test_data = copy.deepcopy(PACKAGE_DEF)

    url = reverse('api:package-add')

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id']

    package_obj = Package.objects.get(pk=json_resp['id'])

    assert package_obj
    assert package_obj.locked_by == member


@pytest.mark.django_db
def test_package_lock_status_no_auth():
    '''Tests package lock status - no auth
    '''
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)

    url = reverse('api:package-lock', args=[package_obj.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(url, **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'credentials' in json_resp['detail']


@pytest.mark.django_db
def test_package_lock_status_access_denied():
    '''Tests package lock status - access denied
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member1,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1)

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'denied' in json_resp['detail']


@pytest.mark.django_db
def test_package_lock_status_access_granted():
    '''Tests package lock status - access granted
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_obj = Package.objects.create(
        author=member,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member, locked_at=timezone.now())

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert 'LockedAt' in json_resp
    assert json_resp['LockedAt']
    assert 'LockedBy' in json_resp
    assert json_resp['LockedBy'] == email


@pytest.mark.django_db
def test_package_relock_no_auth():
    '''Tests package re-locking - no auth
    '''
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)

    url = reverse('api:package-lock', args=[package_obj.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.put(url, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'credentials' in json_resp['detail']


@pytest.mark.django_db
def test_package_relock_cannot_modify():
    '''Tests package re-locking - cannot modify
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member1,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1, locked_at=timezone.now())

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.put(url, HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'disallowed' in json_resp['detail']


@pytest.mark.django_db
def test_package_relock_can_modify():
    '''Tests package re-locking - can modify
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member2,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1, locked_at=timezone.now())

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.put(url, HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert 'LockedAt' in json_resp
    assert json_resp['LockedAt']
    assert 'LockedBy' in json_resp
    assert json_resp['LockedBy'] == email2


@pytest.mark.django_db
def test_package_unlock_no_auth():
    '''Tests package unlocking - no auth
    '''
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)

    url = reverse('api:package-lock', args=[package_obj.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.delete(url, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'credentials' in json_resp['detail']


@pytest.mark.django_db
def test_package_unlock_not_locked():
    '''Tests package unlocking - not locked
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_obj = Package.objects.create(
        author=member,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.delete(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert 'LockedAt' in json_resp
    assert json_resp['LockedAt'] == ''
    assert 'LockedBy' in json_resp
    assert json_resp['LockedBy'] == ''


@pytest.mark.django_db
def test_package_unlock_cannot_modify():
    '''Tests package unlocking - cannot modify
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member1,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1, locked_at=timezone.now())

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.delete(url, HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'disallowed' in json_resp['detail']


@pytest.mark.django_db
def test_package_unlock_wrong_unlocker():
    '''Tests package unlocking - wrong unlocker
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member2,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1, locked_at=timezone.now())

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.delete(url, HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'Unable' in json_resp['detail']


@pytest.mark.django_db
def test_package_unlock_ok_unlocker():
    '''Tests package unlocking - OK unlocker
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    team = Team.objects.create(name='team_' + str(random.randint(1e5, 1e6)))
    team.add_member(member1)
    team.add_member(member2)

    token1, _ = Token.objects.get_or_create(member=member1)

    package_obj = Package.objects.create(
        author=member2, team=team,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1, locked_at=timezone.now())

    url = reverse('api:package-lock', args=[package_obj.id])

    cli = Client()
    response = cli.delete(url, HTTP_AUTHORIZATION='Token ' + token1.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert 'LockedAt' in json_resp
    assert json_resp['LockedAt'] == ''
    assert 'LockedBy' in json_resp
    assert json_resp['LockedBy'] == ''


@pytest.mark.django_db
def test_package_save_locked_by_someone_else():
    '''Tests package save vs locking - package locked by someone else
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member2,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member1, locked_at=timezone.now())

    url = reverse('api:package', args=[package_obj.id])

    test_data = copy.deepcopy(PACKAGE_DEF)

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'disallowed' in json_resp['detail']


@pytest.mark.django_db
def test_package_save_locked_by_writer():
    '''Tests package save vs locking - package locked by writer
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    team = Team.objects.create(name='team_' + str(random.randint(1e5, 1e6)))
    team.add_member(member1)
    team.add_member(member2)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member1, team=team,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        locked_by=member2, locked_at=timezone.now())

    url = reverse('api:package', args=[package_obj.id])

    test_data = copy.deepcopy(PACKAGE_DEF)

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id'] == package_obj.id


@pytest.mark.django_db
def test_package_save_unlocked():
    '''Tests package save vs locking - package unlocked
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1, is_active=True)
    member2 = Member.objects.create(email=email2, is_active=True)

    team = Team.objects.create(name='team_' + str(random.randint(1e5, 1e6)))
    team.add_member(member1)
    team.add_member(member2)

    token2, _ = Token.objects.get_or_create(member=member2)

    package_obj = Package.objects.create(
        author=member1, team=team,
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)

    url = reverse('api:package', args=[package_obj.id])

    test_data = copy.deepcopy(PACKAGE_DEF)

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token2.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id'] == package_obj.id

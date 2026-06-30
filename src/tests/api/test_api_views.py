# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import json
import random
from datetime import timedelta

import pytest

from rest_framework import status
from rest_framework.response import Response

from django.conf import settings
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from narra_backend.api.models import (
    Node,
    NodeLink,
    NodeType,
    Package,
)
from narra_backend.api.utils.views import JSONResponse
from narra_backend.units.models import (
    Member,
    Organization,
    Team,
    TeamMember,
    Token,
)

from .commons import (
    inc_ver,
    NODE_DEF,
    PACKAGE_DEF,
    TEST_DATA_FNAME,
    TEST_DATA_FPATH,
)


@pytest.mark.django_db
def test_token_auth_bad_params():
    '''Tests token auth - bad params
    '''
    auth_url = reverse('api:token-auth')

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        auth_url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_token_auth_bad_creds():
    '''Tests token auth - bad credentials
    '''
    auth_url = reverse('api:token-auth')

    test_data = {
        'email': 'testsuperuser%s@example.com' % random.randint(1e5, 1e6),
        'passwd': 'superpassword' + str(random.randint(1e5, 1e6)),
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        auth_url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_token_auth_ok_creds():
    '''Tests token auth - OK credentials
    '''
    auth_url = reverse('api:token-auth')

    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(email=email, is_active=True, organization=organization)
    member.set_passwd(passwd)
    member.save()
    token, _ = Token.objects.get_or_create(member=member)

    test_data = {
        'email': email,
        'passwd': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        auth_url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json
    assert 'token' in response.json()
    assert response.json()['token'] == token.key


@pytest.mark.django_db
def test_add_package_view_no_auth():
    '''Tests add package without auth
    '''
    package_add_url = reverse('api:package-add')

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        package_add_url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_add_package_view_bad_auth():
    '''Tests add package with bad auth
    '''
    package_add_url = reverse('api:package-add')

    test_data = {}

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=False)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_add_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_add_package_view_invalid_package():
    '''Tests add package view - invalid package
    '''
    package_add_url = reverse('api:package-add')

    test_data = {}

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_add_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json
    assert 'detail' in response.json()


@pytest.mark.skipif(
    not settings.USE_JSONSCHEMA,
    reason='jsonschema usage disabled')
@pytest.mark.django_db
def test_add_package_view_bad_data():
    '''Tests add package view - bad data
    '''
    package_add_url = reverse('api:package-add')

    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['Nodes'].append({})

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_add_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json
    assert 'detail' in response.json()


@pytest.mark.django_db
def test_add_package_view_ok_data():
    '''Tests add package - OK data
    '''
    package_add_url = reverse('api:package-add')

    test_data = copy.deepcopy(PACKAGE_DEF)
    node = copy.deepcopy(NODE_DEF)
    node['Type'] = NodeType.End.value
    node['Id'] = 'NStoryBlock_End_0'
    test_data['Nodes'].append(node)

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_add_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id']
    assert 'story_name' in json_resp
    assert 'uri' in json_resp
    assert json_resp['uri']


@pytest.mark.django_db
def test_package_view_no_auth():
    '''Tests package fetch without auth
    '''
    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package', args=[package_obj.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(package_url, **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_package_view_bad_auth():
    '''Tests package fetch with bad auth
    '''
    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package', args=[package_obj.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.get(package_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_package_view_ok_auth():
    '''Tests package fetch with auth
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_obj = Package(
        filename=TEST_DATA_FNAME,
        story_name='teststory_' + str(random.randint(1e5, 1e6)),
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        author=member,
        mtime=timezone.now() + timedelta(days=1))
    package_obj.save()
    package_url = reverse(
        'api:package', args=[package_obj.id])

    cli = Client()
    response = cli.get(package_url, HTTP_AUTHORIZATION='Token ' + token.key)

    _package_dc = copy.deepcopy(PACKAGE_DEF)
    _package_dc.update({
        'StoryName': package_obj.story_name,
        'JSONVersion': settings.PACKAGE_JSON_VER,
        'UAssetVersion': settings.PACKAGE_UASSET_VER,
        'StoryVersion': settings.PACKAGE_STORY_VER,
        'ModTime': str(int(package_obj.mtime.timestamp())),
    })

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == _package_dc


@pytest.mark.django_db
def test_package_view_invalid_package():
    '''Tests package view - invalid package
    '''
    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package', args=[package_obj.id])

    test_data = {}

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.patch(
        package_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json
    assert 'detail' in response.json()


@pytest.mark.skipif(
    not settings.USE_JSONSCHEMA,
    reason='jsonschema usage disabled')
@pytest.mark.django_db
def test_package_view_put_bad_data():
    '''Tests package overwrite - bad data
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_obj = Package(
        filename=TEST_DATA_FNAME, author=member,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package', args=[package_obj.id])

    test_data = copy.deepcopy(PACKAGE_DEF)
    del test_data['JSONVersion']
    test_data['Nodes'].append({'Node_0': {}})

    cli = Client()
    response = cli.put(
        package_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json
    assert 'detail' in response.json()


@pytest.mark.django_db
def test_package_view_put_ok_data():
    '''Tests package overwrite - OK data
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_obj = Package(
        filename=TEST_DATA_FNAME, author=member,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package', args=[package_obj.id])

    test_data = copy.deepcopy(PACKAGE_DEF)
    node = copy.deepcopy(NODE_DEF)
    node['Type'] = NodeType.End.value
    node['Id'] = 'NStoryBlock_End_0'
    test_data['Nodes'].append(node)

    cli = Client()
    response = cli.put(
        package_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id'] == package_obj.id
    assert 'story_name' in json_resp
    assert 'uri' in json_resp
    assert json_resp['uri'] == package_url


@pytest.mark.django_db
def test_package_pre_save_identity_test():
    '''Tests package add & fetch - pre-save identity test
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_url = reverse('api:package-add')

    package_dc = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        package_dc = json.load(fd_obj)

    assert isinstance(package_dc, dict)
    assert package_dc

    cli = Client()
    response = cli.post(
        package_url, package_dc, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id']
    assert 'story_name' in json_resp
    assert 'uri' in json_resp
    assert json_resp['uri']

    package_uri = json_resp['uri']

    response = cli.get(package_uri, HTTP_AUTHORIZATION='Token ' + token.key)

    assert package_dc == response.json()


@pytest.mark.django_db
def test_package_post_save_put_identity_test():
    '''Tests package add & fetch - post-save (PUT) identity test
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_url = reverse('api:package-add')

    package_dc = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        package_dc = json.load(fd_obj)

    assert isinstance(package_dc, dict)
    assert package_dc

    cli = Client()
    response = cli.post(
        package_url, package_dc, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id']
    assert 'story_name' in json_resp
    assert 'uri' in json_resp
    assert json_resp['uri']

    package_uri = json_resp['uri']

    response = cli.put(
        package_uri, package_dc, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json

    json_resp = response.json()

    assert 'id' in json_resp
    assert json_resp['id']
    assert 'story_name' in json_resp
    assert 'uri' in json_resp
    assert json_resp['uri']

    response = cli.get(package_uri, HTTP_AUTHORIZATION='Token ' + token.key)

    resp_data = copy.deepcopy(response.json())

    assert package_dc == resp_data


@pytest.mark.django_db
def test_packageslistview_no_packages():
    '''Tests PackagesListView class - no packages
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    packages_url = reverse('api:packages-list')

    cli = Client()
    response = cli.get(packages_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.django_db
def test_packageslistview_own_package():
    '''Tests PackagesListView class - own package
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    packages_url = reverse('api:packages-list')

    story_name = 'Name #' + str(random.randint(1e5, 1e6))
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, story_name=story_name, author=member)

    cli = Client()
    response = cli.get(packages_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{
        'id': package_obj.id,
        'story_name': package_obj.story_name,
        'uri': reverse(
            'api:package', args=[package_obj.id]),
    }]


@pytest.mark.django_db
def test_packageslistview_team_package():
    '''Tests PackagesListView class - team package
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, organization=organization)
    token, _ = Token.objects.get_or_create(member=member2)

    team = Team.objects.create(
        name='Team_' + str(random.randint(1e5, 1e6)),
        organization=organization)
    TeamMember.objects.bulk_create([
        TeamMember(team=team, member=member1),
        TeamMember(team=team, member=member2),
    ])

    story_name = 'Name #' + str(random.randint(1e5, 1e6))
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, story_name=story_name, author=member1,
        team=team)

    packages_url = reverse('api:packages-list')

    cli = Client()
    response = cli.get(packages_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{
        'id': package_obj.id,
        'story_name': package_obj.story_name,
        'uri': reverse(
            'api:package', args=[package_obj.id]),
    }]


@pytest.mark.django_db
def test_packageslistview_inner_team_package():
    '''Tests PackagesListView class - inner team package
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, organization=organization)
    token, _ = Token.objects.get_or_create(member=member2)

    team1 = Team(
        name='Team_' + str(random.randint(1e5, 1e6)),
        organization=organization)
    team2 = Team(
        name=team1.name, organization=organization)
    while team2.name == team1.name:
        team2.name = 'Team_' + str(random.randint(1e5, 1e6))
    team1.save()
    team2.save()

    TeamMember.objects.bulk_create([
        TeamMember(team=team1, member=member1),
        TeamMember(team=team2, member=member2),
    ])

    _ = Package.objects.create(
        filename=TEST_DATA_FNAME, author=member1)
    story_name = 'Name #' + str(random.randint(1e5, 1e6))
    package2 = Package.objects.create(
        filename=TEST_DATA_FNAME, story_name=story_name, author=member2)

    packages_url = reverse('api:packages-list')

    cli = Client()
    response = cli.get(packages_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{
        'id': package2.id,
        'story_name': package2.story_name,
        'uri': reverse(
            'api:package', args=[package2.id]),
    }]


@pytest.mark.django_db
def test_packageslistview_same_team_package():
    '''Tests PackagesListView class - same team package
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email3 = email2
    while email3 in [email1, email2]:
        email3 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)

    member1 = Member.objects.create(
        email=email1, is_active=True, passwd_exp=None,
        organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, passwd_exp=None,
        organization=organization)
    member3 = Member.objects.create(
        email=email3, is_active=True, passwd_exp=None,
        organization=organization)

    token, _ = Token.objects.get_or_create(member=member3)

    team1 = Team(name='Team_' + str(random.randint(1e5, 1e6)))
    team2 = Team(name=team1.name)
    while team2.name == team1.name:
        team2.name = 'Team_' + str(random.randint(1e5, 1e6))
    team1.save()
    team2.save()

    TeamMember.objects.bulk_create([
        TeamMember(team=team1, member=member1),
        TeamMember(team=team2, member=member2),
        TeamMember(team=team1, member=member3),
    ])

    story_name = 'Name #' + str(random.randint(1e5, 1e6))
    package1 = Package.objects.create(
        filename=TEST_DATA_FNAME, story_name=story_name, author=member1,
        team=team1)
    _ = Package.objects.create(
        filename=TEST_DATA_FNAME, author=member2, team=team2)

    packages_url = reverse('api:packages-list')

    cli = Client()
    response = cli.get(packages_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{
        'id': package1.id,
        'story_name': package1.story_name,
        'uri': reverse(
            'api:package', args=[package1.id]),
    }]


@pytest.mark.django_db
def test_package_download_view_no_auth():
    '''Tests package download without auth
    '''
    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package-download', args=[package_obj.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(package_url, **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_package_download_view_bad_auth():
    '''Tests package download with bad auth
    '''
    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER)
    package_obj.save()
    package_url = reverse(
        'api:package-download', args=[package_obj.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.get(package_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_package_download_view_ok_auth():
    '''Tests package download with auth
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    package_obj = Package(
        filename=TEST_DATA_FNAME,
        json_ver=settings.PACKAGE_JSON_VER,
        story_ver=settings.PACKAGE_STORY_VER,
        uasset_ver=settings.PACKAGE_UASSET_VER,
        author=member,
        mtime=timezone.now() + timedelta(days=1))
    package_obj.save()
    package_url = reverse(
        'api:package-download', args=[package_obj.id])

    package_def = copy.deepcopy(PACKAGE_DEF)
    package_def['ModTime'] = str(int(package_obj.mtime.timestamp()))

    cli = Client()
    response = cli.get(package_url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'"Assets"' in response.content
    assert b'"Nodes"' in response.content
    assert b'"JSONVersion"' in response.content
    assert b'"StoryVersion"' in response.content
    assert b'"UAssetVersion"' in response.content
    assert response.json

    assert response.json() == package_def


@pytest.mark.django_db
def test_check_package_no_auth():
    '''Tests package check - no auth
    '''
    package_check_url = reverse('api:package-check')

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_check_package_bad_auth():
    '''Tests package check - bad auth
    '''
    package_check_url = reverse('api:package-check')

    test_data = {}

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=False)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_check_package_ok_auth_no_version():
    '''Tests package check - OK auth, no version
    '''
    package_check_url = reverse('api:package-check')

    test_data = copy.deepcopy(PACKAGE_DEF)
    del test_data['JSONVersion']

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'Version not supported' in json_resp['detail']


@pytest.mark.django_db
def test_check_package_ok_auth_unsupported_ver():
    '''Tests package check - OK auth, unsupported version
    '''
    package_check_url = reverse('api:package-check')

    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = inc_ver(settings.PACKAGE_JSON_VER)

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'Version not supported' in json_resp['detail']


@pytest.mark.django_db
def test_check_package_ok_auth_no_migration():
    '''Tests package check - OK auth, no migration version
    '''
    package_check_url = reverse('api:package-check')

    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = settings.PACKAGE_JSON_VER

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert 'current_json_version' in json_resp
    assert json_resp['current_json_version'] == settings.PACKAGE_JSON_VER
    assert 'posted_json_version' in json_resp
    assert json_resp['posted_json_version'] == test_data['JSONVersion']
    assert 'is_version_supported' in json_resp
    assert json_resp['is_version_supported']
    assert 'migration_required' in json_resp
    assert not json_resp['migration_required']


@pytest.mark.django_db
def test_check_package_ok_auth_migration_unsupported():
    '''Tests package check - OK auth, migration unsupported
    '''
    package_check_url = reverse('api:package-check')

    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = '2.12.0'

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'Version not supported' in json_resp['detail']


@pytest.mark.django_db
def test_validate_package_invalid_package():
    '''Tests package validation - invalid package
    '''
    package_check_url = reverse('api:package-validate')

    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = inc_ver(settings.PACKAGE_JSON_VER)

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'No / bad data' in json_resp['detail']
    assert 'Version not supported' in json_resp['detail']


@pytest.mark.django_db
def test_validate_package_nodes_ids_mismatch():
    '''Tests package validation - nodes' IDs mismatch
    '''
    package_check_url = reverse('api:package-validate')

    test_data = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        test_data = json.load(fd_obj)

    assert isinstance(test_data, dict)
    assert test_data['Nodes']

    test_data['Nodes'][0]['OutLinks'].append(dict(NodeLink(
        linked_node=Node(
            nid='NStoryBlock_Fact_' + str(random.randint(1e5, 1e6))),
        my_pin_index=random.randint(1e2, 1e3),
        other_pin_index=random.randint(1e2, 1e3))))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'Missing IDs' in json_resp['detail']


@pytest.mark.skipif(
    not settings.USE_JSONSCHEMA,
    reason='jsonschema usage disabled')
@pytest.mark.django_db
def test_validate_package_validator_error():
    '''Tests package validation - validator error
    '''
    package_check_url = reverse('api:package-validate')

    test_data = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        test_data = json.load(fd_obj)

    assert isinstance(test_data, dict)
    assert test_data['Nodes']

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    orig_validation_schema = settings.PACKAGE_VALIDATION_SCHEMA
    settings.PACKAGE_VALIDATION_SCHEMA = {
        '$schema': 'http://json-schema.org/draft-07/schema',
        'additionalProperties': False,
        'properties': {
            'token': {
                'type': 'string',
            },
        },
        'required': ['token'],
        'type': 'object',
    }

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    settings.PACKAGE_VALIDATION_SCHEMA = orig_validation_schema

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json

    json_resp = response.json()

    assert 'detail' in json_resp
    assert 'Validator output error' in json_resp['detail']


@pytest.mark.django_db
def test_validate_package_validation_ok():
    '''Tests package validation - validation OK
    '''
    package_check_url = reverse('api:package-validate')

    test_data = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        test_data = json.load(fd_obj)

    assert isinstance(test_data, dict)
    assert test_data['Nodes']

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)
    token, _ = Token.objects.get_or_create(member=member)

    cli = Client()
    response = cli.post(
        package_check_url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert 'Global' in json_resp
    assert 'Nodes' in json_resp

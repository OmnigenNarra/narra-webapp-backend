# -*- coding: utf-8 -*-

'''Tests module
'''

import random
from datetime import timedelta

import pytest

from rest_framework import status, serializers
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone

from narra_backend.units.models import (
    Member,
    MemberCode,
    Organization,
    Team,
    TeamMember,
    Token,
)
from narra_backend.units.serializers import (
    SignInSerializer,
)
from narra_backend.units.views import TeamsViewSet


REQ_FACTORY = None


def setup_module(module):
    '''Module setup method
    '''
    module.REQ_FACTORY = RequestFactory()


@pytest.mark.django_db
def test_organization_session_bad_org():
    '''Tests organization session create - bad organization
    '''
    org_id = random.randint(1e5, 1e6)
    url = reverse('api:units:organization-signin', args=[org_id])

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'may not be null' in response.content


@pytest.mark.django_db
def test_organization_session_no_creds():
    '''Tests organization session create - no credentials
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'may not be null' in response.content


@pytest.mark.django_db
def test_organization_session_empty_creds():
    '''Tests organization session create - empty credentials
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    test_data = {
        'email': '',
        'passwd': '',
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_organization_session_bad_creds():
    '''Tests organization session create - bad credentials
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    test_data = {
        'email': 'user%s@example.com' % random.randint(1e5, 1e6),
        'passwd': 'passwd' + str(random.randint(1e5, 1e6)),
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_session_ok_creds_not_active():
    '''Tests organization session create - OK credentials,
        inactive account
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(email=email, is_active=False)
    member.set_passwd(passwd)
    member.save()

    test_data = {
        'email': email,
        'passwd': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_session_ok_creds_no_org_member():
    '''Tests organization session create - OK credentials,
        no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization1.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=False, organization=organization2)
    member.set_passwd(passwd)
    member.save()

    test_data = {
        'email': email,
        'passwd': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_session_ok_creds_no_org_admin():
    '''Tests organization session create - OK credentials,
        no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=False, org_admin=False,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    test_data = {
        'email': email,
        'passwd': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_session_fail_extra_auth_params_test():
    '''Tests organization session create - fail extra_auth_params test
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization1)
    member.set_passwd(passwd)
    member.save()

    test_data = {
        'email': email,
        'passwd': passwd,
        'extra_auth_params': {
            'organization_id': organization2.id,
            'org_admin': True,
        },
    }

    serializer = SignInSerializer(data=test_data)
    try:
        serializer.is_valid(raise_exception=True)

        assert False
    except serializers.ValidationError as exc:
        assert 'Unable to proceed' in str(exc)


@pytest.mark.django_db
def test_organization_session_ok_passwd_expired():
    '''Tests organization session create - OK credentials,
        password expired
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    passwd_exp = timezone.now() - timedelta(days=1)

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=passwd_exp,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    test_data = {
        'email': email,
        'passwd': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['email'] == email
    assert json_resp['jtime']
    assert json_resp['token'] is None
    assert json_resp['code']
    assert json_resp['passwd_exp'] is True


@pytest.mark.django_db
def test_organization_session_all_ok():
    '''Tests organization session create - all OK (credentials,
        membership, account / passwd statuses etc.)
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:organization-signin', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    test_data = {
        'email': email,
        'passwd': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['email'] == email
    assert json_resp['jtime']
    assert json_resp['token']
    assert json_resp['code'] is None
    assert json_resp['passwd_exp'] is False


@pytest.mark.django_db
def test_organization_teams_list_no_auth():
    '''Tests organization teams listing - no authorization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(url, **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_teams_list_bad_token():
    '''Tests organization teams listing - bad token
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    token = Token.objects.create(member=member)
    token_key = token.key
    token.delete()

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token_key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_teams_list_org_admin_not_active():
    '''Tests organization teams listing - organization admin, not active
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(
        email=email, is_active=False, org_admin=True, passwd_exp=None,
        organization=organization)

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_teams_list_no_org_member():
    '''Tests organization teams listing - no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization1.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_teams_list_no_org_admin():
    '''Tests organization teams listing - no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=False, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_teams_list_ok_org_admin():
    '''Tests organization teams listing - organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert isinstance(json_resp, dict)
    assert isinstance(json_resp['teams'], list)


@pytest.mark.django_db
def test_organization_teams_list_org_admin_superuser():
    '''Tests organization teams listing - organization admin, superuser logged
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    request = REQ_FACTORY.get(url)
    request.user = superuser
    view = TeamsViewSet.as_view({'get': 'list'})

    tresp = view(request, org_id=organization.id)
    response = tresp.render()

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_team_create_no_auth():
    '''Tests organization team create - no authorization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

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
def test_organization_team_create_no_org_member():
    '''Tests organization team create - no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization1.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_create_no_org_admin():
    '''Tests organization team create - no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=False, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_create_ok_org_admin_bad_data():
    '''Tests organization team create - organization admin, bad data
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'may not be null' in response.content


@pytest.mark.django_db
def test_organization_team_create_ok_org_admin_doubled_name_same_org():
    '''Tests organization team create - organization admin, doubled name,
        same organization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    Team.objects.create(organization=organization, name=team_name)

    test_data = {
        'name': team_name,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'name already exists' in response.content


@pytest.mark.django_db
def test_organization_team_create_ok_org_admin_doubled_name_diff_org():
    '''Tests organization team create - organization admin, doubled name,
        different organization
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization1.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization1)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    Team.objects.create(organization=organization2, name=team_name)

    test_data = {
        'name': team_name,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'name already exists' in response.content


@pytest.mark.django_db
def test_organization_team_create_ok_org_admin_ok_name():
    '''Tests organization team create - organization admin, OK name
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    test_data = {
        'name': team_name,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['id']
    assert json_resp['ctime']
    assert json_resp['name'] == team_name


@pytest.mark.django_db
def test_organization_team_remove_no_auth():
    '''Tests organization team remove - no authorization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_team_remove_no_org_member():
    '''Tests organization team remove - no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization1.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_remove_no_org_admin():
    '''Tests organization team remove - no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=False, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_remove_ok_org_admin_no_team():
    '''Tests organization team remove - OK organization admin, no team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    team = Team.objects.create(organization=organization, name=team_name)

    test_data = {
        'id': team.id,
    }

    team.delete()

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_organization_team_remove_ok_org_admin_ok_team():
    '''Tests organization team remove - OK organization admin, OK team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    team = Team.objects.create(organization=organization, name=team_name)

    test_data = {
        'id': team.id,
    }

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['id'] is None
    assert json_resp['name'] == team_name
    assert json_resp['ctime']


@pytest.mark.django_db
def test_organization_team_members_list_no_auth():
    '''Tests organization team members list - no authorization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(url, **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_team_members_list_no_org_member():
    '''Tests organization team members list - no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization1, name=team_name)
    url = reverse('api:units:team-members', args=[organization1.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_members_list_no_org_member_match_orgs():
    '''Tests organization team members list - no organization member,
        matching organizations
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization2, name=team_name)
    url = reverse('api:units:team-members', args=[organization1.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization1)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_organization_team_members_list_no_org_admin():
    '''Tests organization team members list - no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=False, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_members_list_ok_org_admin_bad_team():
    '''Tests organization team members list - OK organization member, bad team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])
    team.delete()

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_organization_team_members_list_ok_org_admin_ok_team():
    '''Tests organization team members list - OK organization member, OK team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    cli = Client()
    response = cli.get(url, HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert isinstance(json_resp, dict)
    assert isinstance(json_resp['members'], list)


@pytest.mark.django_db
def test_organization_team_member_create_no_auth():
    '''Tests organization team member create - no authorization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

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
def test_organization_team_member_create_no_org_member():
    '''Tests organization team member create - no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization1, name=team_name)
    url = reverse('api:units:team-members', args=[organization1.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_member_create_no_org_admin():
    '''Tests organization team member create - no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=False, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_member_create_members_limit_reached():
    '''Tests organization team member create - members limit reached
    '''
    members_limit = 1
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)),
        members_limit=members_limit)
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {
        'email': email2,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'limit reached' in response.content


@pytest.mark.django_db
def test_organization_team_member_create_ok_org_admin_bad_data():
    '''Tests organization team member create - organization admin, bad data
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {
        'email': email2,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'valid email' in response.content


@pytest.mark.django_db
def test_organization_team_member_create_ok_org_admin_doubled_email_same_org():
    '''Tests organization team member create - organization admin,
        doubled email, same organization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {
        'email': email,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['id']
    assert json_resp['jtime']
    assert json_resp['email'] == email

    assert Member.objects.filter(email=email).count() == 1


@pytest.mark.django_db
def test_organization_team_create_ok_org_admin_doubled_email_diff_org():
    '''Tests organization team create - organization admin, doubled email,
        different organization
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name1 = 'Team #' + str(random.randint(1e5, 1e6))
    team_name2 = team_name1
    while team_name2 == team_name1:
        team_name2 = 'testsuperuser%s' % random.randint(1e5, 1e6)
    team1 = Team.objects.create(organization=organization1, name=team_name1)
    Team.objects.create(organization=organization2, name=team_name2)
    url = reverse('api:units:team-members', args=[organization1.id, team1.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member1 = Member(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization1)
    member1.set_passwd(passwd)
    member1.save()
    member2 = Member(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member2.set_passwd(passwd)
    member2.save()

    token = Token.objects.create(member=member1)

    test_data = {
        'email': email2,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'Organization mismatch' in response.content


@pytest.mark.django_db
def test_organization_team_member_create_ok_org_admin_ok_email():
    '''Tests organization team member create - organization admin, OK email
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {
        'email': email2,
    }

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['id']
    assert json_resp['jtime']
    assert json_resp['email'] == email2


@pytest.mark.django_db
def test_organization_team_member_remove_no_auth():
    '''Tests organization team member remove - no authorization
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    test_data = {}

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_organization_team_member_remove_no_org_member():
    '''Tests organization team member remove - no organization member
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization1, name=team_name)
    url = reverse('api:units:team-members', args=[organization1.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization2)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_member_remove_no_org_admin():
    '''Tests organization team member remove - no organization admin
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=False, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    test_data = {}

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organization_team_member_remove_ok_org_admin_bad_team():
    '''Tests organization team member remove - OK organization admin,
        bad team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name1 = 'Team #' + str(random.randint(1e5, 1e6))
    team_name2 = team_name1
    while team_name2 == team_name1:
        team_name2 = 'testsuperuser%s' % random.randint(1e5, 1e6)
    team1 = Team.objects.create(organization=organization, name=team_name1)
    team2 = Team.objects.create(organization=organization, name=team_name2)
    url = reverse('api:units:team-members', args=[organization.id, team2.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    TeamMember.objects.create(team=team2, member=member1)
    team_member2 = TeamMember.objects.create(team=team1, member=member2)

    token = Token.objects.create(member=member1)

    test_data = {
        'id': team_member2.id,
    }

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_organization_team_member_remove_ok_org_admin_bad_team_member():
    '''Tests organization team member remove - OK organization admin,
        bad team member
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name1 = 'Team #' + str(random.randint(1e5, 1e6))
    team_name2 = team_name1
    while team_name2 == team_name1:
        team_name2 = 'testsuperuser%s' % random.randint(1e5, 1e6)
    team1 = Team.objects.create(organization=organization, name=team_name1)
    team2 = Team.objects.create(organization=organization, name=team_name2)
    url = reverse('api:units:team-members', args=[organization.id, team1.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    TeamMember.objects.create(team=team1, member=member1)
    team_member2 = TeamMember.objects.create(team=team2, member=member2)

    token = Token.objects.create(member=member1)

    test_data = {
        'id': team_member2.id,
    }

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_organization_team_member_remove_ok_org_admin_removed_team_member():
    '''Tests organization team member remove - OK organization admin,
        removed team member
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    team_member = TeamMember.objects.create(team=team, member=member)
    team_member_id = team_member.id
    team_member.delete()

    token = Token.objects.create(member=member)

    test_data = {
        'id': team_member_id,
    }

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_organization_team_member_remove_ok_org_admin_all_ok():
    '''Tests organization team member remove - OK organization admin,
        OK team member
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    team_member = TeamMember.objects.create(team=team, member=member)

    token = Token.objects.create(member=member)

    test_data = {
        'id': team_member.id,
    }

    cli = Client()
    response = cli.delete(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['id'] is None
    assert json_resp['jtime']
    assert json_resp['email'] == email


@pytest.mark.django_db
def test_member_passwd_reset_req_bad_data():
    '''Tests member password reset request - bad data
    '''
    url = reverse('api:units:password-reset')

    test_data = {
        'test_' + str(random.randint(1e5, 1e6)): None,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_member_passwd_reset_req_not_existing_member():
    '''Tests member password reset request - not existing member
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(
        email=email, is_active=False, org_admin=False, passwd_exp=None)

    test_data = {
        'email': email,
    }

    member.delete()

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['email'] == email


@pytest.mark.django_db
def test_member_passwd_reset_req_not_active_member():
    '''Tests member password reset request - not active member
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    Member.objects.create(
        email=email, is_active=False, org_admin=False, passwd_exp=None)

    test_data = {
        'email': email,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert b'locked' in response.content


@pytest.mark.django_db
def test_member_passwd_reset_req_ok_member():
    '''Tests member password reset request - OK member
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    Member.objects.create(
        email=email, is_active=True, org_admin=False, passwd_exp=None)

    test_data = {
        'email': email,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.post(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['email'] == email


@pytest.mark.django_db
def test_member_passwd_reset_act_bad_data():
    '''Tests member password reset action - bad data
    '''
    url = reverse('api:units:password-reset')

    test_data = {
        'test_' + str(random.randint(1e5, 1e6)): None,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_member_passwd_reset_act_no_passwd():
    '''Tests member password reset action - no password
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    Member.objects.create(
        email=email, is_active=True, org_admin=False, passwd_exp=None)

    test_data = {
        'email': email,
        'code': 'code' + str(random.randint(1e5, 1e6)),
        'passwd1': '',
        'passwd2': '',
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_member_passwd_reset_act_mismatch_passwds():
    '''Tests member password reset action - mismatched password
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    Member.objects.create(
        email=email, is_active=True, org_admin=False, passwd_exp=None)

    passwd = 'passwd' + str(random.randint(1e5, 1e6))
    test_data = {
        'email': email,
        'code': 'code' + str(random.randint(1e5, 1e6)),
        'passwd1': passwd,
        'passwd2': passwd + '_',
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_member_passwd_reset_act_not_existing_member():
    '''Tests member password reset action - not existing member
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(
        email=email, is_active=False, org_admin=False, passwd_exp=None)

    passwd = 'passwd' + str(random.randint(1e5, 1e6))
    test_data = {
        'email': email,
        'code': 'code' + str(random.randint(1e5, 1e6)),
        'passwd1': passwd,
        'passwd2': passwd,
    }

    member.delete()

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json

    json_resp = response.json()

    assert 'authorized' in json_resp['detail']


@pytest.mark.django_db
def test_member_passwd_reset_act_not_active_member():
    '''Tests member password reset action - not active member
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    Member.objects.create(
        email=email, is_active=False, org_admin=False, passwd_exp=None)

    passwd = 'passwd' + str(random.randint(1e5, 1e6))
    test_data = {
        'email': email,
        'code': 'code' + str(random.randint(1e5, 1e6)),
        'passwd1': passwd,
        'passwd2': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert b'locked' in response.content


@pytest.mark.django_db
def test_member_passwd_reset_act_bad_code():
    '''Tests member password reset action - bad code
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    Member.objects.create(
        email=email, is_active=True, org_admin=False, passwd_exp=None)

    passwd = 'passwd' + str(random.randint(1e5, 1e6))
    test_data = {
        'email': email,
        'code': 'code' + str(random.randint(1e5, 1e6)),
        'passwd1': passwd,
        'passwd2': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_member_passwd_reset_act_ok_data():
    '''Tests member password reset action - OK data
    '''
    url = reverse('api:units:password-reset')

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(
        email=email, is_active=True, org_admin=False, passwd_exp=None)

    member_code = MemberCode.objects.create(
        member=member, type=MemberCode.TYPE_PASSWD_RESET)

    passwd = 'passwd' + str(random.randint(1e5, 1e6))
    test_data = {
        'email': email,
        'code': member_code.code,
        'passwd1': passwd,
        'passwd2': passwd,
    }

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json', **kwargs)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['email'] == email

    _member = Member.objects.get(pk=member.id)

    assert _member.check_passwd(passwd)


@pytest.mark.django_db
def test_team_name_update_no_team():
    '''Tests team name update - no team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    team = Team.objects.create(organization=organization, name=team_name)

    test_data = {
        'id': team.id,
    }

    team.delete()

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_team_name_update_no_team_name():
    '''Tests team name update - no team name
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    team = Team.objects.create(organization=organization, name=team_name)

    test_data = {
        'id': team.id,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_team_name_update_empty_team_name():
    '''Tests team name update - empty team name
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))

    team = Team.objects.create(organization=organization, name=team_name)

    test_data = {
        'id': team.id,
        'name': '',
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_team_name_update_clashing_team_name():
    '''Tests team name update - clashing team name
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name1 = 'Team #' + str(random.randint(1e5, 1e6))
    team_name2 = team_name1
    while team_name2 == team_name1:
        team_name2 = 'Team #' + str(random.randint(1e5, 1e6))
    team1 = Team.objects.create(organization=organization, name=team_name1)
    Team.objects.create(organization=organization, name=team_name2)

    test_data = {
        'id': team1.id,
        'name': team_name2,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_team_name_update_ok_team_name():
    '''Tests team name update - OK team name
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    url = reverse('api:units:teams', args=[organization.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member.set_passwd(passwd)
    member.save()

    token = Token.objects.create(member=member)

    team_name1 = 'Team #' + str(random.randint(1e5, 1e6))
    team1 = Team.objects.create(organization=organization, name=team_name1)

    team_names = Team.objects.all().values_list('name', flat=True)

    team_name2 = team_name1
    while team_name2 in team_names:
        team_name2 = 'Team #' + str(random.randint(1e5, 1e6))

    test_data = {
        'id': team1.id,
        'name': team_name2,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert json_resp['id'] == team1.id
    assert json_resp['name'] == team_name2


@pytest.mark.django_db
def test_team_member_email_update_bad_team():
    '''Tests team member - email update - bad team
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name1 = 'Team #' + str(random.randint(1e5, 1e6))
    team_name2 = team_name1
    while team_name2 == team_name1:
        team_name2 = 'Team #' + str(random.randint(1e5, 1e6))
    team1 = Team.objects.create(organization=organization, name=team_name1)
    team2 = Team.objects.create(organization=organization, name=team_name2)
    url = reverse('api:units:team-members', args=[organization.id, team1.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    team_member2 = TeamMember.objects.create(team=team2, member=member2)

    token = Token.objects.create(member=member1)

    test_data = {
        'id': team_member2.id,
        'email': email1,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_team_member_email_update_no_member():
    '''Tests team member - email update - no member
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    team_member2 = TeamMember.objects.create(team=team, member=member2)

    member2.delete()

    token = Token.objects.create(member=member1)

    test_data = {
        'id': team_member2.id,
        'email': email2,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_team_member_email_update_non_existing_team_member():
    '''Tests team member - email update - non-existing team member
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(
        email=email, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    team_member = TeamMember.objects.create(team=team, member=member)

    token = Token.objects.create(member=member)

    test_data = {
        'id': team_member.id,
        'email': email,
    }

    team_member.delete()

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_team_member_email_update_repeated_email():
    '''Tests team member - email update - repeated email
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    Member.objects.create(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    team_member = TeamMember.objects.create(team=team, member=member1)

    token = Token.objects.create(member=member1)

    test_data = {
        'id': team_member.id,
        'email': email2,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b'Email exists' in response.content


@pytest.mark.django_db
def test_team_member_email_update_ok_email():
    '''Tests team member - email update - OK email
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(organization=organization, name=team_name)
    url = reverse('api:units:team-members', args=[organization.id, team.id])

    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(
        email=email1, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)
    member2 = Member.objects.create(
        email=email2, is_active=True, org_admin=True, passwd_exp=None,
        organization=organization)

    team_member = TeamMember.objects.create(team=team, member=member1)

    member2.delete()

    token = Token.objects.create(member=member1)

    test_data = {
        'id': team_member.id,
        'email': email2,
    }

    cli = Client()
    response = cli.patch(
        url, test_data, content_type='application/json',
        HTTP_AUTHORIZATION='Token ' + token.key)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.json

    json_resp = response.json()

    assert isinstance(json_resp, dict)
    assert json_resp['email'] == email2
    assert json_resp['jtime']
    assert json_resp['id'] == team_member.id

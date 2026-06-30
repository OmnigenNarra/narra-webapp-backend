# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test.client import RequestFactory

from narra_backend.units.authentication import (
    MemberAuthBackend,
    requires_org_admin,
)
from narra_backend.units.models import (
    Member,
    Organization,
)


DRF_REQ_FACTORY = None
REQ_FACTORY = None


def setup_module(module):
    '''Module setup method
    '''
    module.DRF_REQ_FACTORY = APIRequestFactory()
    module.REQ_FACTORY = RequestFactory()


def test_memberauthbackend_no_required_params():
    '''Tests MemberAuthBackend class - no required params
    '''
    request = REQ_FACTORY.get('/')
    kwargs = {}
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) is None


@pytest.mark.django_db
def test_memberauthbackend_no_member():
    '''Tests MemberAuthBackend class - no member
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    member.delete()

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': '',
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) is None


@pytest.mark.django_db
def test_memberauthbackend_member_cannot_authenticate_bad_passwd():
    '''Tests MemberAuthBackend class - member cannot authenticate (not active),
        bad passwd
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    Member.objects.create(email=email, is_active=False)

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': passwd,
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) is None


@pytest.mark.django_db
def test_memberauthbackend_member_cannot_authenticate_ok_passwd():
    '''Tests MemberAuthBackend class - member cannot authenticate (not active),
        OK passwd
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(email=email, is_active=False)
    member.set_passwd(passwd)
    member.save()

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': passwd,
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) is None


@pytest.mark.django_db
def test_memberauthbackend_member_can_authenticate_bad_passwd():
    '''Tests MemberAuthBackend class - member can authenticate, bad password
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    Member.objects.create(email=email, is_active=True)

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': passwd,
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) is None


@pytest.mark.django_db
def test_memberauthbackend_member_can_authenticate_ok_passwd():
    '''Tests MemberAuthBackend class - member can authenticate, OK password
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(email=email, is_active=True)
    member.set_passwd(passwd)
    member.save()

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': passwd,
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) == member


@pytest.mark.django_db
def test_memberauthbackend_member_extra_params_unfulfilled():
    '''Tests MemberAuthBackend class - extra params unfulfilled
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, organization=organization,
        org_admin=False)
    member.set_passwd(passwd)
    member.save()

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': passwd,
        'organization_id': organization.id,
        'org_admin': True,
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) is None


@pytest.mark.django_db
def test_memberauthbackend_member_extra_params_fulfilled():
    '''Tests MemberAuthBackend class - extra params fulfilled
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member(
        email=email, is_active=True, organization=organization,
        org_admin=True)
    member.set_passwd(passwd)
    member.save()

    request = REQ_FACTORY.get('/')
    kwargs = {
        'email': email,
        'passwd': passwd,
        'organization_id': organization.id,
        'org_admin': True,
    }
    backend = MemberAuthBackend()

    assert backend.authenticate(request, **kwargs) == member


class SomeViewClass:
    '''Some test NON-ViewSet-based class
    '''
    @requires_org_admin
    def some_method(self, request, org_id=None, ret_val=None):
        '''Some method
        '''
        return Response({'ret_val': ret_val})


class SomeViewsetClass(viewsets.ModelViewSet):
    '''Some test viewset-based class
    '''
    @requires_org_admin
    def some_method(self, request, org_id=None, ret_val=None):
        '''Some viewset method
        '''
        return Response({'ret_val': ret_val})


def test_requires_org_admin_bad_args_no_viewset():
    '''Tests requires_org_admin decorator - bad args: no viewset
    '''
    view = SomeViewClass()
    request = DRF_REQ_FACTORY.get('/', {})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    try:
        _ = view.some_method(request, org_id=0, ret_val=ret_val)

        assert False
    except AssertionError as exc:
        assert 'no DRF ViewSetMixin' in str(exc)


def test_requires_org_admin_bad_args_no_org_id():
    '''Tests requires_org_admin decorator - bad args: no org_id
    '''
    view = SomeViewsetClass.as_view({'get': 'some_method'})
    request = DRF_REQ_FACTORY.get('/', {})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    try:
        _ = view(request, ret_val=ret_val)

        assert False
    except AssertionError as exc:
        assert 'no org_id' in str(exc)


def test_requires_org_admin_bad_args_bad_org_id():
    '''Tests requires_org_admin decorator - bad args: bad org_id
    '''
    view = SomeViewsetClass.as_view({'get': 'some_method'})
    request = DRF_REQ_FACTORY.get('/', {})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    try:
        _ = view(request, org_id='', ret_val=ret_val)

        assert False
    except AssertionError as exc:
        assert 'org_id is not an integer' in str(exc)


def test_requires_org_admin_user_is_not_a_member_instance():
    '''Tests requires_org_admin decorator - user is not a Member instance
    '''
    view = SomeViewsetClass.as_view({'get': 'some_method'})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    user_class = get_user_model()
    user = user_class()

    request = DRF_REQ_FACTORY.get('/', {})
    force_authenticate(request, user=user)

    response = view(request, org_id=0, ret_val=ret_val)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data
    assert 'ret_val' not in response.data


def test_requires_org_admin_not_authenticated():
    '''Tests requires_org_admin decorator - not authenticated
    '''
    view = SomeViewsetClass.as_view({'get': 'some_method'})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    user = AnonymousUser()

    request = DRF_REQ_FACTORY.get('/', {})
    force_authenticate(request, user=user)

    response = view(request, org_id=0, ret_val=ret_val)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data
    assert 'ret_val' not in response.data


def test_requires_org_admin_not_org_admin():
    '''Tests requires_org_admin decorator - not organization admin
    '''
    view = SomeViewsetClass.as_view({'get': 'some_method'})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    member = Member(org_admin=False)

    request = DRF_REQ_FACTORY.get('/', {})
    force_authenticate(request, user=member)

    response = view(request, org_id=0, ret_val=ret_val)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data
    assert 'ret_val' not in response.data


@pytest.mark.django_db
def test_requires_org_admin_bad_org_admin():
    '''Tests requires_org_admin decorator - bad organization admin
    '''
    organization1 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))
    organization2 = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    view = SomeViewsetClass.as_view({'get': 'some_method'})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    member = Member(org_admin=False, organization=organization1)

    request = DRF_REQ_FACTORY.get('/', {})
    force_authenticate(request, user=member)

    response = view(request, org_id=organization2.id, ret_val=ret_val)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data
    assert 'ret_val' not in response.data


@pytest.mark.django_db
def test_requires_org_admin_all_tests_passed():
    '''Tests requires_org_admin decorator - all tests passwd
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    view = SomeViewsetClass.as_view({'get': 'some_method'})
    ret_val = 'Return value: ' + str(random.randint(1e5, 1e6))

    member = Member(org_admin=True, organization=organization)

    request = DRF_REQ_FACTORY.get('/', {})
    force_authenticate(request, user=member)

    response = view(request, org_id=organization.id, ret_val=ret_val)

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_200_OK
    assert response.data
    assert 'ret_val' in response.data
    assert response.data['ret_val'] == ret_val

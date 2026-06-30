# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest

from narra_backend.units.models import (
    Member,
    Organization,
)
from narra_backend.units.serializers import (
    OrganizationSerializer,
    PasswordResetActionSerializer,
    PasswordResetRequestSerializer,
    SignInSerializer,
)


@pytest.mark.django_db
def test_signinserializer_create_stub():
    '''Tests SignInSerializer class - create() stub call
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

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

    serializer = SignInSerializer(data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.instance is False


@pytest.mark.django_db
def test_signinserializer_update_stub():
    '''Tests SignInSerializer class - update() stub call
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

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

    class SomeClass:
        '''Some test class
        '''
        email = None
        passwd = None

    serializer = SignInSerializer(instance=SomeClass(), data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.data == {'email': None}


@pytest.mark.django_db
def test_organizationserializer_create_stub():
    '''Tests OrganizationSerializer class - create() stub call
    '''
    test_data = {
        'name': 'Organization #' + str(random.randint(1e5, 1e6)),
    }

    serializer = OrganizationSerializer(data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.instance is False


@pytest.mark.django_db
def test_organizationserializer_update_stub():
    '''Tests OrganizationSerializer class - update() stub call
    '''
    org_name1 = 'Organization #' + str(random.randint(1e5, 1e6))
    org_name2 = org_name1
    while org_name2 == org_name1:
        org_name2 = 'Organization #' + str(random.randint(1e5, 1e6))

    organization = Organization.objects.create(name=org_name1)

    test_data = {
        'name': org_name2,
    }

    serializer = OrganizationSerializer(instance=organization, data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.data == {'id': organization.id, 'name': org_name1}


def test_passwordresetrequestserializer_create_stub():
    '''Tests PasswordResetRequestSerializer class - create() stub call
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)

    test_data = {
        'email': email,
    }

    serializer = PasswordResetRequestSerializer(data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.instance is False


def test_passwordresetrequestserializer_update_stub():
    '''Tests PasswordResetRequestSerializer class - update() stub call
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    test_data = {
        'email': email,
    }

    class SomeClass:
        '''Some test class
        '''
        email = None

    serializer = PasswordResetRequestSerializer(
        instance=SomeClass(), data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.data == {'email': None}


def test_passwordresetactionserializer_create_stub():
    '''Tests PasswordResetActionSerializer class - create() stub call
    '''
    passwd = str(random.randint(1e5, 1e6))
    test_data = {
        'email': 'testsuperuser%s@example.com' % random.randint(1e5, 1e6),
        'code': str(random.randint(1e5, 1e6)),
        'passwd1': passwd,
        'passwd2': passwd,
    }

    serializer = PasswordResetActionSerializer(data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.instance is False


def test_passwordresetactionserializer_update_stub():
    '''Tests PasswordResetActionSerializer class - update() stub call
    '''
    passwd = str(random.randint(1e5, 1e6))
    test_data = {
        'email': 'testsuperuser%s@example.com' % random.randint(1e5, 1e6),
        'code': str(random.randint(1e5, 1e6)),
        'passwd1': passwd,
        'passwd2': passwd,
    }

    class SomeClass:
        '''Some test class
        '''
        email = None
        code = None

    serializer = PasswordResetActionSerializer(
        instance=SomeClass(), data=test_data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    assert serializer.data == {'email': None, 'code': None}

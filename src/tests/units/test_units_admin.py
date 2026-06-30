# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest
from rest_framework import status

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.test import Client
from django.test.client import RequestFactory
from django.urls import reverse

from narra_backend.units.admin import (
    MemberAdmin,
)
from narra_backend.units.models import (
    Member,
)


REQ_FACTORY = None


def setup_module(module):
    '''Module setup method
    '''
    module.REQ_FACTORY = RequestFactory()


def test_memberadmin_form_basic():
    '''Tests MemberAdmin form (basic)
    '''
    mod_adm = MemberAdmin(Member, AdminSite())
    request = REQ_FACTORY.get('/')

    assert list(mod_adm.get_form(request).base_fields) == [
        'email',
        'is_active',
        'passwd_exp',
        'organization',
        'org_admin',
    ]


@pytest.mark.django_db
def test_memberadmin_add_view_no_auth():
    '''Tests MemberAdmin class - add view, no auth
    '''
    cli = Client()
    response = cli.get(reverse('admin:units_member_add'))

    if settings.HTTP_AUTHZ:
        assert isinstance(response, HttpResponse)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    else:
        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.url.startswith(reverse('admin:login'))


@pytest.mark.django_db
def test_memberadmin_add_view_ok_auth():
    '''Tests MemberAdmin class - add view, OK auth
    '''
    mod_adm = MemberAdmin(Member, AdminSite())
    request = REQ_FACTORY.get('/')
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.add_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Add Member'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_organization"' in response.content


@pytest.mark.django_db
def test_memberadmin_add_view_ok_auth_bad_req():
    '''Tests MemberAdmin class - add view, OK auth, bad request
    '''
    mod_adm = MemberAdmin(Member, AdminSite())
    request = REQ_FACTORY.get('/')
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    request.user = get_user_model().objects.create_superuser(
        username, '', username)

    tresp = mod_adm.add_view(request)
    response = tresp.render()

    assert tresp.context_data['title'] == 'Add Member'
    assert tresp.status_code == status.HTTP_200_OK
    assert b'id="id_organization"' in response.content


@pytest.mark.django_db
def test_memberadmin_add_view_no_email():
    '''Tests MemberAdmin class - add view, OK auth, no email
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
        reverse('admin:units_member_add'), {field_name: field_value}, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'field is required' in response.content


@pytest.mark.django_db
def test_memberadmin_add_view_empty_email():
    '''Tests MemberAdmin class - add view, OK auth, empty email
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
        reverse('admin:units_member_add'), {'email': ''}, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'field is required' in response.content


@pytest.mark.django_db
def test_memberadmin_add_view_bad_email():
    '''Tests MemberAdmin class - add view, OK auth, bad email
    '''
    email = 'testuser%s_example.com' % random.randint(1e5, 1e6)
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:units_member_add'), {'email': email}, **kwargs)

    assert isinstance(response, TemplateResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'valid email address' in response.content


@pytest.mark.django_db
def test_memberadmin_add_view_ok_email():
    '''Tests MemberAdmin class - add view, OK auth, OK email
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:units_member_add'), {'email': email}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:units_member_changelist')


@pytest.mark.django_db
def test_memberadmin_change_view_save():
    '''Tests MemberAdmin class - change view, save
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:units_member_change', args=[member.id]),
        {'email': email}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:units_member_changelist')


@pytest.mark.django_db
def test_memberadmin_passwd_change_no_auth():
    '''Tests MemberAdmin class - password change view, no auth
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    response = cli.get(
        reverse('admin:units_member_passwd_change', args=[member.id]),
        **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url.startswith(reverse('admin:login'))


@pytest.mark.django_db
def test_memberadmin_passwd_change_no_perms():
    '''Tests MemberAdmin class - password change view, no perms
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    username = 'teststaffuser_' + str(random.randint(1e5, 1e6))
    staffuser = get_user_model().objects.create(
        username=username, is_active=True, is_staff=True, is_superuser=False)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(staffuser)
    response = cli.get(
        reverse('admin:units_member_passwd_change', args=[member.id]),
        **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_memberadmin_passwd_change_no_member():
    '''Tests MemberAdmin class - password change view, no member
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    member_id = member.id
    member.delete()

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.get(
        reverse('admin:units_member_passwd_change', args=[member_id]),
        **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_memberadmin_passwd_change_form_open():
    '''Tests MemberAdmin class - password change view, form open
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.get(
        reverse('admin:units_member_passwd_change', args=[member.id]),
        **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' not in response.content
    assert bytes(email, encoding='utf-8') in response.content


@pytest.mark.django_db
def test_memberadmin_passwd_change_empty_passwd():
    '''Tests MemberAdmin class - password change view, empty password
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:units_member_passwd_change', args=[member.id]), {
            'password1': '',
            'password2': ''}, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'field is required' in response.content


@pytest.mark.django_db
def test_memberadmin_passwd_change_bad_passwd():
    '''Tests MemberAdmin class - password change view, bad password
    '''
    membername = 'testsuperuser' + str(random.randint(1e5, 1e6))
    email = membername + '@example.com'
    member = Member.objects.create(email=email)

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:units_member_passwd_change', args=[member.id]), {
            'password1': membername,
            'password2': membername}, **kwargs)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK
    assert b'class="errorlist"' in response.content
    assert b'password is too similar' in response.content


@pytest.mark.django_db
def test_memberadmin_passwd_change_ok_passwd():
    '''Tests MemberAdmin class - password change view, bad password
    '''
    email = 'testuser%s@example.com' % random.randint(1e5, 1e6)
    passwd = Member.objects.make_random_password()
    member = Member.objects.create(email=email)

    username = 'testsuperuser_' + str(random.randint(1e5, 1e6))
    superuser = get_user_model().objects.create_superuser(
        username, '', username)

    kwargs = {}
    if settings.HTTP_AUTHZ:
        kwargs['HTTP_AUTHORIZATION'] = 'Basic ' + settings.HTTP_AUTHZ

    cli = Client()
    cli.force_login(superuser)
    response = cli.post(
        reverse('admin:units_member_passwd_change', args=[member.id]), {
            'password1': passwd,
            'password2': passwd}, **kwargs)

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.url == reverse('admin:units_member_changelist')

    member = Member.objects.get(pk=member.id)

    assert member.check_passwd(passwd)

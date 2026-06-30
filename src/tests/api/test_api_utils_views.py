# -*- coding: utf-8 -*-

'''Tests module
'''

import json
import random

import pytest

from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test.client import RequestFactory

from narra_backend.api.models import (
    Package,
)
from narra_backend.api.utils.views import (
    can_user_get_package,
    csrf_failure_view,
    ForceJSONClientContentNegotiation,
    JSONResponse,
    StaticAuthMiddleware,
)
from narra_backend.units.models import (
    Member,
    Team,
    TeamMember,
)


REQ_FACTORY = None

# admin:admin
TEST_HTTP_AUTHZ = 'YWRtaW46YWRtaW4='


def setup_module(module):
    '''Module setup method
    '''
    module.REQ_FACTORY = RequestFactory()


def test_fjccn_select_parser():
    '''Tests ForceJSONClientContentNegotiation parser selection
    '''
    fjccn = ForceJSONClientContentNegotiation()
    request = REQ_FACTORY.get('/')
    parsers = [JSONParser()]
    parser = fjccn.select_parser(request, parsers)
    assert isinstance(parser, JSONParser)


def test_fjccn_select_renderer():
    '''Tests ForceJSONClientContentNegotiation renderer
        and media (MIME) type selection
    '''
    fjccn = ForceJSONClientContentNegotiation()
    request = REQ_FACTORY.get('/')
    renderers = [JSONRenderer()]
    renderer, media_type = fjccn.select_renderer(request, renderers)
    assert isinstance(renderer, JSONRenderer)
    assert media_type == JSONRenderer.media_type


def test_jsonresponse_empty_input():
    '''Tests JSONResponse class - empty input
    '''
    resp = JSONResponse(None)
    assert resp.content == b'null'


def test_jsonresponse_ok_input():
    '''Tests JSONResponse class - OK input
    '''
    resp = JSONResponse({})
    assert resp.content == b'{}'


def test_csrf_failure_view():
    '''Tests csrf_failure_view
    '''
    request = REQ_FACTORY.get('/')
    reason = 'reason #' + str(random.randint(1e5, 1e6))
    response = csrf_failure_view(request, reason)

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert json.loads(
        str(response.content, encoding='utf-8')) == {'detail': reason}


def test_staticauth_middleware_no_auth_set():
    '''Tests StaticAuthMiddleware - no auth
    '''
    request = REQ_FACTORY.get('/')
    middleware = StaticAuthMiddleware(
        lambda _: HttpResponse(''), can_auth=False)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK


def test_staticauth_middleware_no_header():
    '''Tests StaticAuthMiddleware - no header
    '''
    request = REQ_FACTORY.get('/')
    middleware = StaticAuthMiddleware(
        lambda _: HttpResponse(''), can_auth=True, forced_auth=TEST_HTTP_AUTHZ)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_staticauth_middleware_malformed_header():
    '''Tests StaticAuthMiddleware - malformed header
    '''
    request = REQ_FACTORY.get('/')
    request.META['HTTP_AUTHORIZATION'] = 'Tic Tac Toe'
    middleware = StaticAuthMiddleware(
        lambda _: HttpResponse(''), can_auth=True, forced_auth=TEST_HTTP_AUTHZ)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_staticauth_middleware_bad_auth_type():
    '''Tests StaticAuthMiddleware - bad auth type
    '''
    request = REQ_FACTORY.get('/')
    request.META['HTTP_AUTHORIZATION'] = 'cisaB xyz'
    middleware = StaticAuthMiddleware(
        lambda _: HttpResponse(''), can_auth=True, forced_auth=TEST_HTTP_AUTHZ)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_staticauth_middleware_bad_creds():
    '''Tests StaticAuthMiddleware - bad credentials
    '''
    request = REQ_FACTORY.get('/')
    request.META['HTTP_AUTHORIZATION'] = 'Basic ' + TEST_HTTP_AUTHZ * 2
    middleware = StaticAuthMiddleware(
        lambda _: HttpResponse(''), can_auth=True, forced_auth=TEST_HTTP_AUTHZ)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_staticauth_middleware_ok_auth():
    '''Tests StaticAuthMiddleware - OK auth
    '''
    request = REQ_FACTORY.get('/')
    request.META['HTTP_AUTHORIZATION'] = 'Basic ' + TEST_HTTP_AUTHZ
    middleware = StaticAuthMiddleware(
        lambda _: HttpResponse(''), can_auth=True, forced_auth=TEST_HTTP_AUTHZ)
    response = middleware(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == status.HTTP_200_OK


def test_can_user_get_package_no_user():
    '''Tests can_user_get_package method - no user
    '''
    user = None
    package_obj = Package()

    assert not can_user_get_package(user, package_obj)


def test_can_user_get_package_not_active_user():
    '''Tests can_user_get_package method - not active user
    '''
    user = AnonymousUser()
    user.is_active = False
    package_obj = Package()

    assert not can_user_get_package(user, package_obj)


def test_can_user_get_package_not_authenticated_user():
    '''Tests can_user_get_package method - not authenticated user
    '''
    user = AnonymousUser()
    user.is_active = True
    package_obj = Package()

    assert not can_user_get_package(user, package_obj)


def test_can_user_get_package_user_is_staff():
    '''Tests can_user_get_package method - user is staff
    '''
    user_class = get_user_model()
    user = user_class()
    user.is_active = True
    user.is_staff = True
    package_obj = Package()

    assert can_user_get_package(user, package_obj)


@pytest.mark.django_db
def test_can_user_get_package_user_is_author():
    '''Tests can_user_get_package method - user is author
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)

    package_obj = Package.objects.create(author=member)

    assert can_user_get_package(member, package_obj)


@pytest.mark.django_db
def test_can_user_get_package_user_is_not_team_member():
    '''Tests can_user_get_package method - user is NOT a team member
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)

    package_obj = Package.objects.create()

    assert not can_user_get_package(member, package_obj)


@pytest.mark.django_db
def test_can_user_get_package_user_is_team_member():
    '''Tests can_user_get_package method - user IS a team member
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email, is_active=True)

    team_name = 'Team #' + str(random.randint(1e5, 1e6))
    team = Team.objects.create(name=team_name)
    TeamMember.objects.create(team=team, member=member)

    package_obj = Package.objects.create(team=team)

    assert can_user_get_package(member, package_obj)

# -*- coding: utf-8 -*-

'''Views utils module
'''

from rest_framework import status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import JSONParser

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from ..models import (
    Package,
)
from ...units.models import (
    Member,
    TeamMember,
)


class ForceJSONClientContentNegotiation(BaseContentNegotiation):
    '''Force JSON I/O for client content-negotiation class
    '''
    def select_parser(self, request, parsers):
        _parsers = [
            par for par in parsers if par.media_type == JSONParser.media_type]
        return _parsers[0] if _parsers else JSONParser()

    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)


class JSONResponse(JsonResponse):
    '''Pre-configured JSON response class
    '''
    def __init__(self, data, **kwargs):
        kwargs.setdefault('content_type', 'application/json; charset=utf-8')
        super().__init__(
            data, safe=False, json_dumps_params=dict(
                ensure_ascii=False, indent=None, separators=(',', ':')),
            **kwargs)


def csrf_failure_view(_, reason=''):
    '''CSRF fail view
    '''
    return JSONResponse({'detail': reason}, status=status.HTTP_403_FORBIDDEN)


def can_user_get_package(user, package_obj):
    '''Tests if user can get package
    '''
    if not user or not user.is_active or not user.is_authenticated:
        return False

    if isinstance(user, get_user_model()) and user.is_staff:
        return True

    team_ids = TeamMember.objects.filter(member=user).values_list(
        'team_id', flat=True)

    return isinstance(user, Member) and (
        user.id == package_obj.author_id or package_obj.team_id in team_ids)


def package_download_view(request, package_id):
    '''Package download view
    '''
    package_obj = get_object_or_404(Package, pk=package_id)
    if can_user_get_package(request.user, package_obj):
        response = JSONResponse(dict(package_obj))
        response['Content-Disposition'] = 'attachment; filename="%s"' % (
            package_obj.filename.replace('"', ''),)

        return response

    return HttpResponse('', status=status.HTTP_401_UNAUTHORIZED)


class StaticAuthMiddleware:
    '''Static authentication middleware
    '''
    def __init__(self, get_response, can_auth=True, forced_auth=None):
        self.get_response = get_response
        self.http_authz = None
        if forced_auth:
            self.http_authz = forced_auth
        elif can_auth:
            self.http_authz = settings.HTTP_AUTHZ

    def __call__(self, request):
        if self.http_authz:
            noauth_resp = HttpResponse('', status=status.HTTP_401_UNAUTHORIZED)
            noauth_resp['WWW-Authenticate'] = \
                'Basic realm="Narra", charset="utf-8"'

            if 'HTTP_AUTHORIZATION' not in request.META:
                return noauth_resp

            authz = request.META['HTTP_AUTHORIZATION'].split()
            if len(authz) != 2:
                return noauth_resp
            if authz[0] not in ['Basic', 'Token']:
                return noauth_resp
            if authz[0] == 'Basic' and authz[1] != self.http_authz:
                return noauth_resp

        return self.get_response(request)

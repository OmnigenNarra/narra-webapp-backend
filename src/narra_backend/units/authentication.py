# -*- coding: utf-8 -*-

'''Authentication module
'''

from rest_framework.authentication import (
    TokenAuthentication as DRFTokenAuthentication,
)
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.viewsets import ViewSetMixin

from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _u

from .models import (
    Member,
    Token,
)


class TokenAuthentication(DRFTokenAuthentication):
    '''ProjectMember-based authentication
    '''
    model = Token

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('member').get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed(_u('Invalid token.'))

        if not token.member.is_active:
            raise AuthenticationFailed(_u('User inactive or deleted.'))

        return (token.member, token)


class MemberAuthBackend:
    '''Project member authentication backend class
    '''
    def authenticate(self, request, **kwargs):
        '''Authenticate project member
        '''
        if 'email' not in kwargs or 'passwd' not in kwargs:
            return None

        email = kwargs.pop('email')
        passwd = kwargs.pop('passwd')
        try:
            member = Member.objects.get(email=email, **kwargs)
        except Member.DoesNotExist:
            Member().set_passwd(passwd)
        else:
            if self.user_can_authenticate(member) and \
                    member.check_passwd(passwd):
                return member

        return None

    @classmethod
    def user_can_authenticate(cls, member):
        '''Reject members with is_active=False
        '''
        return member.is_active


def requires_org_admin(func):
    '''Member as organization admin authorization decorator function
    '''
    def authorize_and_call(*args, **kwargs):
        assert isinstance(args[0], ViewSetMixin), 'no DRF ViewSetMixin'
        assert isinstance(args[1], Request), 'no DRF Request'
        assert 'org_id' in kwargs, 'no org_id in kwargs'
        assert isinstance(kwargs['org_id'], int), 'org_id is not an integer'

        request = args[1]
        org_id = kwargs['org_id']

        if not isinstance(request.user, Member):
            raise PermissionDenied({'detail': _u('Not logged')})

        if not request.user.is_authenticated or not request.user.org_admin \
                or request.user.organization_id != org_id:
            raise PermissionDenied({'detail': _u('Permission denied')})

        return func(*args, **kwargs)

    return authorize_and_call


class IsOrgMember(BasePermission):
    '''Allows access only to organization members
    '''
    message = _u('Not an organization member')

    def has_permission(self, request, _):
        return bool(
            request.user and
            isinstance(request.user, Member) and
            request.user.is_active)


class IsReleaseUIDsMaintainer(BasePermission):
    '''Allows access only to release UIDs maintainers
    '''
    message = _u('Not an active release UIDs maintainer')

    def has_permission(self, request, _):
        return bool(
            request.user and
            isinstance(request.user, get_user_model()) and
            request.user.is_active and
            request.user.is_staff and
            (
                request.user.is_superuser or
                request.user.has_perms(
                    (
                        'api.view_releaseuid',
                        'api.add_releaseuid',
                        'api.change_releaseuid'))))

# -*- coding: utf-8 -*-

'''Views module
'''

from urllib.parse import quote_plus

from rest_framework import status, viewsets
from rest_framework.exceptions import (
    ErrorDetail,
    PermissionDenied,
    ValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.conf import settings
from django.contrib.sites.models import Site
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _u

from .authentication import (
    requires_org_admin,
    TokenAuthentication,
)
from .models import (
    Organization,
    Member,
    MemberCode,
    Team,
    TeamMember,
)
from .serializers import (
    OrganizationSerializer,
    PasswordResetActionSerializer,
    PasswordResetRequestSerializer,
    SignInSerializer,
    TeamMemberSerializer,
    TeamSerializer,
)
from .utils.mailing import Mailer


class OrganizationSignInViewSet(viewsets.ViewSet):
    '''SignIn viewset class
    '''
    authentication_classes = ()
    permission_classes = ()

    @classmethod
    def create(cls, request, org_id=None):
        '''Create method
        '''
        data = {
            'email': request.data.get('email'),
            'passwd': request.data.get('passwd'),
            'extra_auth_params': {
                'organization_id': org_id,
                'org_admin': True,
            },
        }
        serializer = SignInSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            for _, errs in exc.detail.items():
                for err in errs:
                    if isinstance(err, ErrorDetail) and \
                            err.code == 'authorization':
                        return Response(
                            exc.detail,
                            status=status.HTTP_403_FORBIDDEN)
            raise

        Member.objects.filter(email=serializer.data['email']).update(
            last_login=timezone.now())

        return Response({
            'email': serializer.data['email'],
            'jtime': serializer.data['jtime'],
            'token': serializer.data['token'],
            'code': serializer.data['code'],
            'passwd_exp': serializer.data['passwd_exp'],
        })


class TeamsViewSet(viewsets.ModelViewSet):
    '''Teams viewset class
    '''
    queryset = Team.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = TeamSerializer

    @requires_org_admin
    def list(self, request, org_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        queryset = self.queryset.filter(
            organization=organization).order_by('ctime')
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'organization': OrganizationSerializer().to_representation(
                organization),
            'teams': serializer.data,
        })

    @requires_org_admin
    def create(self, request, org_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        data = {
            'name': request.data.get('name'),
            'organization': organization.id,
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data)

    @requires_org_admin
    def update(self, request, org_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        data = {
            'name': request.data.get('name'),
            'organization': organization.id,
        }
        instance = get_object_or_404(
            Team, organization=organization, pk=request.data.get('id'))
        serializer = self.get_serializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @requires_org_admin
    def destroy(self, request, org_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        instance = get_object_or_404(
            Team, organization=organization, pk=request.data.get('id'))
        serializer = self.get_serializer(instance)
        self.perform_destroy(instance)

        return Response(serializer.data)


class TeamMembersViewSet(viewsets.ModelViewSet):
    '''Team members viewset class
    '''
    queryset = TeamMember.objects.select_related('member').all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = TeamMemberSerializer

    @requires_org_admin
    def list(self, request, org_id=None, team_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        team = get_object_or_404(Team, organization=organization, pk=team_id)
        queryset = self.queryset.filter(team=team).order_by('jtime')
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'organization': OrganizationSerializer().to_representation(
                organization),
            'team': TeamSerializer().to_representation(team),
            'members': serializer.data,
        })

    @requires_org_admin
    def create(self, request, org_id=None, team_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        team = get_object_or_404(Team, organization=organization, pk=team_id)
        data = {
            'organization': organization.id,
            'team': team.id,
            'email': request.data.get('email'),
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        member = Member.objects.get(
            email=serializer.data['email'], organization=organization)
        member_code, _ = MemberCode.objects.get_or_create(
            member=member, type=MemberCode.TYPE_PASSWD_RESET)
        url = 'https://%s%s' % (
            Site.objects.get_current().domain,
            settings.MEMBER_PASSWD_RESET_URL_FMT % {
                'email': quote_plus(member.email),
                'code': member_code.code,
            })
        Mailer.send_generic_email(
            'new_account_passwd_setup_mail', member.email, member.email,
            substs_dc={
                'user_name': member.email,
                'passwd_reset_url': url,
            })

        return Response(serializer.data)

    @requires_org_admin
    def update(self, request, org_id=None, team_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        team = get_object_or_404(Team, organization=organization, pk=team_id)
        instance = get_object_or_404(
            TeamMember, team=team, pk=request.data.get('id'))
        data = {
            'organization': organization.id,
            'team': team.id,
            'id': instance.id,
            'member_id': instance.member_id,
            'email': request.data.get('email'),
        }
        serializer = self.get_serializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @requires_org_admin
    def destroy(self, request, org_id=None, team_id=None):
        organization = get_object_or_404(Organization, pk=org_id)
        team = get_object_or_404(Team, organization=organization, pk=team_id)
        instance = get_object_or_404(
            TeamMember, team=team, pk=request.data.get('id'))
        serializer = self.get_serializer(instance)
        self.perform_destroy(instance)

        return Response(serializer.data)


class PasswordResetViewSet(viewsets.ViewSet):
    '''Password reset viewset class
    '''
    authentication_classes = ()
    permission_classes = ()

    @classmethod
    def create(cls, request):
        '''Create method
        '''
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.data['email']

        members = Member.objects.filter(email=email)
        if not members:
            return Response(serializer.data)

        member = members[0]
        if not member.is_active:
            raise PermissionDenied({'detail': _u('Account locked')})

        member_code, _ = MemberCode.objects.get_or_create(
            member=member, type=MemberCode.TYPE_PASSWD_RESET)
        url = 'https://%s%s' % (
            Site.objects.get_current().domain,
            settings.MEMBER_PASSWD_RESET_URL_FMT % {
                'email': quote_plus(member.email),
                'code': member_code.code,
            })
        Mailer.send_passwd_reset_email(member.email, member.email, url)

        return Response(serializer.data)

    @classmethod
    def update(cls, request):
        '''Update method
        '''
        serializer = PasswordResetActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.data['email']

        members = Member.objects.filter(email=email)
        if not members:
            raise PermissionDenied({'detail': _u('Not authorized')})

        member = members[0]
        if not member.is_active:
            raise PermissionDenied({'detail': _u('Account locked')})

        member_code, _ = MemberCode.objects.get_or_create(
            member=member, type=MemberCode.TYPE_PASSWD_RESET)
        if member_code.code != serializer.data['code']:
            raise PermissionDenied({'detail': _u('Not authorized')})

        member.passwd_exp = None
        member.set_passwd(serializer.initial_data['passwd1'])
        member.save(update_fields=['passwd', 'passwd_exp'])

        member_code.delete()

        return Response({
            'email': serializer.data['email'],
            'organization': {'id': member.organization_id},
        })

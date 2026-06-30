# -*- coding: utf-8 -*-

'''Views module
'''

from functools import partial

from rest_framework import status, viewsets
from rest_framework.exceptions import (
    ErrorDetail,
    PermissionDenied,
    ValidationError,
)
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _u
from django.shortcuts import get_object_or_404

from ..units.authentication import (
    DRFTokenAuthentication,
    IsOrgMember,
    IsReleaseUIDsMaintainer,
    TokenAuthentication,
)
from ..units.models import (
    Member,
    Organization,
    TeamMember,
)
from ..units.serializers import (
    SignInSerializer,
)
from ..units.utils.mailing import Mailer

from .models import (
    Package,
    Release,
    ReleaseUID,
)
from .serializers import (
    PackageSerializer,
    PackagesListSerializer,
    ReleaseUIDSerializer,
    ReleaseUIDSerializerForUpdate,
)
from .utils.packages import (
    is_package_invalid,
    perform_story_validation,
    process_and_store_package,
    store_package,
    transform_validate_package,
    versions_check,
)
from .utils.views import (
    can_user_get_package,
    ForceJSONClientContentNegotiation,
    package_download_view,
)


class ObtainAuthToken(APIView):
    '''Obtain auth token view class
    '''
    throttle_classes = ()
    permission_classes = ()
    content_negotiation_class = ForceJSONClientContentNegotiation

    def post(self, request, *args, **kwargs):
        '''POST method
        '''
        serializer = SignInSerializer(data=request.data)
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


class AddPackageView(APIView):
    '''Package add view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    content_negotiation_class = ForceJSONClientContentNegotiation

    def post(self, request):
        '''POST method
        '''
        package_dc, error = transform_validate_package(request.data)
        if error:
            return Response(
                {'detail': _u('No / bad data - %s') % error},
                status=status.HTTP_400_BAD_REQUEST)

        package_obj, _, _ = process_and_store_package(
            package_dc, 'via_api_' + str(timezone.now().timestamp()) + '.json',
            request.user)

        return Response({
            'id': package_obj.id,
            'story_name': package_obj.story_name,
            'uri': reverse(
                'api:package', args=[package_obj.id]),
        }, status=status.HTTP_201_CREATED)


class CheckPackageView(APIView):
    '''Package check view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    content_negotiation_class = ForceJSONClientContentNegotiation

    def post(self, request):
        '''POST method
        '''
        is_invalid, op_msg = is_package_invalid(request.data)
        if is_invalid:
            return Response(
                {'detail': _u('No / bad data - %s') % op_msg},
                status=status.HTTP_400_BAD_REQUEST)

        posted_json_version, is_version_supported, migration_required = \
            versions_check(request.data)

        return Response({
            'current_json_version': settings.PACKAGE_JSON_VER,
            'posted_json_version': posted_json_version,
            'is_version_supported': is_version_supported,
            'migration_required': migration_required,
        }, status=status.HTTP_200_OK)


class ValidatePackageView(APIView):
    '''Package validation view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    content_negotiation_class = ForceJSONClientContentNegotiation

    def post(self, request):
        '''POST method
        '''
        package_dc, error = transform_validate_package(request.data)
        if error:
            return Response(
                {'detail': _u('No / bad data - %s') % error},
                status=status.HTTP_400_BAD_REQUEST)

        errors, op_msg, output_dc = perform_story_validation(package_dc)
        if errors:
            return Response(
                {'detail': _u('Validator output error: %s') % op_msg},
                status=status.HTTP_400_BAD_REQUEST)

        return Response(output_dc, status=status.HTTP_200_OK)


class PackageLockView(APIView):
    '''Package locking view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    content_negotiation_class = ForceJSONClientContentNegotiation

    @classmethod
    def _lock_response(cls, package_obj):
        '''Returns successful locking status response
        '''
        output_dc = {
            'LockedBy':
                package_obj.locked_by.email if package_obj.locked_by else '',
            'LockedAt':
                str(package_obj.locked_at.timestamp())
                if package_obj.locked_at else '',
        }

        return Response(output_dc, status=status.HTTP_200_OK)

    @classmethod
    def get(cls, request, package_id=None):
        '''GET method
        '''
        package_obj = get_object_or_404(Package, pk=package_id)
        if not can_user_get_package(request.user, package_obj):
            raise PermissionDenied({'detail': _u('Access denied')})

        return cls._lock_response(package_obj)

    @classmethod
    def put(cls, request, package_id=None):
        '''PUT method
        '''
        package_obj = get_object_or_404(Package, pk=package_id)
        if not package_obj.can_modify(request.user):
            raise PermissionDenied({'detail': _u('Locking disallowed')})

        package_obj.locked_at = timezone.now()
        package_obj.locked_by = request.user
        package_obj.save(update_fields=['locked_at', 'locked_by'])

        return cls._lock_response(package_obj)

    @classmethod
    def delete(cls, request, package_id=None):
        '''DELETE method
        '''
        package_obj = get_object_or_404(Package, pk=package_id)
        if not package_obj.locked_by:
            return cls._lock_response(package_obj)

        if not package_obj.can_modify(request.user):
            raise PermissionDenied({'detail': _u('Unlocking disallowed')})

        if package_obj.locked_by != request.user:
            raise PermissionDenied({'detail': _u('Unable to unlock')})

        package_obj.locked_at = None
        package_obj.locked_by = None
        package_obj.save(update_fields=['locked_at', 'locked_by'])

        return cls._lock_response(package_obj)


class PackageView(RetrieveUpdateAPIView):
    '''Package update view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    serializer_class = PackageSerializer
    content_negotiation_class = ForceJSONClientContentNegotiation

    def get_serializer(self, *args, **kwargs):
        package_obj = args[0]
        if self.request.method in ['PUT', 'PATCH'] and (
                (
                    package_obj.locked_by and
                    package_obj.locked_by != self.request.user) or
                not package_obj.can_modify(self.request.user)):
            raise PermissionDenied({'detail': _u('Modyfing disallowed')})

        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()

        return serializer_class(*args, **kwargs)

    def get_object(self):
        package_id = self.kwargs['package_id']
        get_part_fn = partial(get_object_or_404, Package, pk=package_id)

        return cache.get_or_set(
            'package_' + str(package_id), get_part_fn, 3600)

    def retrieve(self, request, *args, **kwargs):
        package_obj = self.get_object()
        if can_user_get_package(request.user, package_obj):
            return Response(dict(package_obj))

        raise PermissionDenied({'detail': _u('Access forbidden')})

    def update(self, request, *args, **kwargs):
        package_obj = self.get_object()
        serializer = self.get_serializer(package_obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        store_package(package_obj, request.data)

        return Response({
            'id': package_obj.id,
            'story_name': package_obj.story_name,
            'uri': reverse(
                'api:package', args=[package_obj.id]),
        }, status=status.HTTP_202_ACCEPTED)


class PackageDownloadView(APIView):
    '''Package download view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    content_negotiation_class = ForceJSONClientContentNegotiation

    def get(self, request, package_id=None):
        '''GET method
        '''
        return package_download_view(request, package_id)


class PackagesListView(APIView):
    '''Packages list view class
    '''
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsOrgMember,)
    content_negotiation_class = ForceJSONClientContentNegotiation

    def get(self, request):
        '''GET method
        '''
        team_ids = TeamMember.objects.filter(
            member=request.user).values_list('team', flat=True)
        packages = Package.objects.filter(
            Q(author=request.user) | Q(team_id__in=team_ids)).order_by(
                '-mtime')

        return Response(
            PackagesListSerializer(packages).data, status=status.HTTP_200_OK)


class ReleaseUIDsViewSet(viewsets.ModelViewSet):
    '''Release UIDs viewset class
    '''
    queryset = ReleaseUID.objects.all()
    authentication_classes = (DRFTokenAuthentication,)
    permission_classes = (IsAuthenticated, IsReleaseUIDsMaintainer)
    serializer_class = ReleaseUIDSerializer

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.request.method == 'PATCH':
            serializer_class = ReleaseUIDSerializerForUpdate

        return serializer_class

    def list(self, _):
        queryset = self.queryset.order_by('ctime')
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    def create(self, request):
        organization_id = request.data.get('organization')
        release_id = request.data.get('release')
        organization = get_object_or_404(Organization, pk=organization_id)
        release = get_object_or_404(Release, pk=release_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization, release=release)

        return Response(serializer.data)

    def update(self, request):
        releaseuid_id = request.data.get('id')
        instance = get_object_or_404(ReleaseUID, pk=releaseuid_id)
        prev_url = instance.url
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(url=request.data.get('url'))

        if not prev_url and instance.url and instance.release:
            for member in Member.objects.filter(
                    organization=instance.organization, org_admin=True,
                    is_active=True):
                release = instance.release
                Mailer.send_generic_email(
                    'new_plugin_release', member.email, member.email,
                    substs_dc={
                        'user_name': member.email,
                        'organization_name': instance.organization.name,
                        'unreal_ver': release.unreal_ver,
                        'release_ver': release.release_ver,
                        'new_release_url': instance.url,
                        'changes': release.changes.replace(
                            '\r\n', '\n').replace('\r', '\n').replace(
                                '\n', '<br>'),
                    })

        return Response(serializer.data)

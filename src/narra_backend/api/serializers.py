# -*- coding: utf-8 -*-

'''Serializers module
'''

from rest_framework import fields, serializers
from rest_framework.exceptions import ValidationError

from django.urls import reverse
from django.utils.translation import ugettext_lazy as _u

from .models import (
    Package,
    Release,
    ReleaseUID,
)
from .utils.packages import transform_validate_package, update_package_obj
from ..units.serializers import OrganizationSerializer


class PackageSerializer(serializers.Serializer):
    '''Package serializer class
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._errors = []
        self._validated_data = []

    def to_representation(self, instance):
        return dict(instance)

    def is_valid(self, raise_exception=False):
        package_dc, error = transform_validate_package(self.initial_data)
        if error and raise_exception:
            raise ValidationError(
                {'detail': _u('No / bad data - %s') % error})

        self._validated_data = package_dc

        return not error

    def create(self, _):
        return Package()

    def update(self, instance, validated_data):
        update_package_obj(
            instance, instance.filename, instance.author, validated_data)
        instance.save()

        return instance


class PackagesListSerializer(serializers.ListSerializer):
    '''Packages list serializer class
    '''
    child = fields.Field()

    def to_representation(self, data):
        return [{
            'id': instance.id,
            'story_name': instance.story_name,
            'uri': reverse(
                'api:package', args=[instance.id]),
        } for instance in data]

    def to_internal_value(self, _):
        return []

    def update(self, instance, _):
        return []


class ReleaseSerializer(serializers.ModelSerializer):
    '''Release serializer class
    '''
    unreal_ver = fields.CharField(read_only=True)
    release_ver = fields.CharField(read_only=True)
    changes = fields.CharField(read_only=True)

    class Meta:
        model = Release
        fields = ['id', 'unreal_ver', 'release_ver', 'changes']


class ReleaseUIDSerializer(serializers.ModelSerializer):
    '''Release UID serializer class
    '''
    organization = serializers.SerializerMethodField(required=False)
    release = serializers.SerializerMethodField()
    uid = fields.CharField(read_only=True)
    url = fields.CharField(read_only=True)

    class Meta:
        model = ReleaseUID
        fields = ['id', 'organization', 'release', 'uid', 'url', 'ctime']

    @classmethod
    def get_organization(cls, instance):
        '''Returns Organization instance
        '''
        return OrganizationSerializer().to_representation(
            instance.organization
        ) if instance and instance.organization else None

    @classmethod
    def get_release(cls, instance):
        '''Returns Organization instance
        '''
        return ReleaseSerializer().to_representation(
            instance.release
        ) if instance and instance.release else None

    def create(self, validated_data):
        uid = ReleaseUID.gen_uid(
            validated_data['release'], validated_data['organization'])
        releaseuid, _ = ReleaseUID.objects.get_or_create(
            organization=validated_data['organization'],
            release=validated_data['release'],
            defaults={'uid': uid})

        return releaseuid

    def update(self, instance, _):
        return instance


class ReleaseUIDSerializerForUpdate(ReleaseUIDSerializer):
    '''Release UID serializer class for update
    '''
    url = fields.URLField()

    class Meta:
        model = ReleaseUID
        fields = ['id', 'organization', 'release', 'uid', 'url', 'ctime']

    def update(self, instance, validated_data):
        if not instance.url:
            instance.url = validated_data.get('url', instance.url)
            instance.save(update_fields=['url'])

        return instance

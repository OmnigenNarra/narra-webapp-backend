# -*- coding: utf-8 -*-

'''Tests module
'''

import json
import random

from rest_framework.exceptions import ValidationError

from django.urls import reverse

from narra_backend.api.models import Package
from narra_backend.api.serializers import (
    PackageSerializer,
    PackagesListSerializer,
)

from .commons import TEST_DATA_FPATH


def test_packageserializer_invalid():
    '''Tests PackageSerializer validaton - bad data
    '''
    package_dc = {}
    serializer = PackageSerializer(data=package_dc)

    assert not serializer.is_valid(raise_exception=False)
    try:
        serializer.is_valid(raise_exception=True)
        assert False
    except ValidationError:
        pass


def test_packageserializer_valid_ok():
    '''Tests PackageSerializer validaton - OK data
    '''
    package_dc = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        package_dc = json.load(fd_obj)

    serializer = PackageSerializer(data=package_dc)

    assert serializer.is_valid(raise_exception=False)
    assert serializer.data == package_dc
    assert serializer.is_valid(raise_exception=True)


def test_packageserializer_save():
    '''Tests PackageSerializer saving - OK data
    '''
    package_dc = None
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        package_dc = json.load(fd_obj)

    serializer = PackageSerializer(data=package_dc)

    assert serializer.is_valid(raise_exception=True)
    assert serializer.validated_data == package_dc

    instance = serializer.save()

    assert isinstance(instance, Package)


def test_packageslistserializer_empty():
    '''Tests PackagesListSerializer usage - empty data
    '''
    serializer = PackagesListSerializer([])

    assert serializer.data == []


def test_packageslistserializer_some():
    '''Tests PackagesListSerializer usage - empty data
    '''
    packages = [
        Package(
            id=random.randint(1e5, 1e6),
            story_name='Name #' + str(random.randint(1e5, 1e6))),
        Package(
            id=random.randint(1e5, 1e6),
            story_name='Name #' + str(random.randint(1e5, 1e6))),
    ]
    out_data = [{
        'id': obj.id,
        'story_name': obj.story_name,
        'uri': reverse(
            'api:package', args=[obj.id]),
    } for obj in packages]

    serializer = PackagesListSerializer(packages)

    assert serializer.data == out_data


def test_packageslistserializer_any_save():
    '''Tests PackagesListSerializer usage - saving without saving
    '''
    packages = [
        Package(
            id=random.randint(1e5, 1e6),
            story_name='Name #' + str(random.randint(1e5, 1e6))),
        Package(
            id=random.randint(1e5, 1e6),
            story_name='Name #' + str(random.randint(1e5, 1e6))),
    ]
    out_data = [{
        'id': obj.id,
        'story_name': obj.story_name,
        'uri': reverse(
            'api:package', args=[obj.id]),
    } for obj in packages]

    serializer = PackagesListSerializer(packages, data=out_data)
    serializer.is_valid()
    serializer.save()

    assert serializer.validated_data == []

# -*- coding: utf-8 -*-

'''Tests module
'''

import random

import pytest

from narra_backend.api.models import (
    ReleaseUID,
)
from narra_backend.units.models import (
    Organization,
)
from narra_backend.api.serializers import (
    ReleaseUIDSerializer,
)


@pytest.mark.django_db
def test_releaseuidserializer_update_stub():
    '''Tests ReleaseUIDSerializer class - update() stub call
    '''
    organization = Organization.objects.create(
        name='Organization #' + str(random.randint(1e5, 1e6)))

    url1 = 'https://' + str(random.random())
    url2 = url1
    while url2 == url1:
        url2 = 'https://' + str(random.random())

    release1 = 'R#' + str(random.randint(1e5, 1e6))
    release2 = release1
    while release2 == release1:
        release2 = 'R#' + str(random.randint(1e5, 1e6))

    releaseuid = ReleaseUID.objects.create(organization=organization, url=url1)

    serializer = ReleaseUIDSerializer(instance=releaseuid, data={})
    serializer.is_valid(raise_exception=True)
    serializer.save(organization=organization, url=url2)

    assert serializer.data
    assert 'uid' in serializer.data
    assert serializer.data['ctime']
    assert serializer.data['id'] == releaseuid.id
    assert serializer.data['url'] == url1

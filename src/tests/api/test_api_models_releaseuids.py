# -*- coding: utf-8 -*-

'''Tests module
'''

import random
import string

import pytest

from narra_backend.api.models import (
    Release,
    ReleaseUID,
)
from narra_backend.units.models import (
    Organization,
)
from narra_backend.api.utils.strings import (
    make_random_text,
)


def test_release_class_repr():
    '''Tests Release model - repr
    '''
    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    obj = Release(unreal_ver=unreal_ver, release_ver=release_ver)

    assert str(obj) == '%s / %s' % (unreal_ver, release_ver)


def test_release_class_iter():
    '''Tests Release model - iterator
    '''
    release_id = random.randint(1e5, 1e6)
    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    changes = 'CH#' + str(random.randint(1e5, 1e6))

    obj = Release(
        id=release_id, unreal_ver=unreal_ver, release_ver=release_ver,
        changes=changes)

    assert dict(obj) == {
        'id': release_id,
        'unreal_ver': unreal_ver,
        'release_ver': release_ver,
        'changes': changes,
    }


def test_releaseuid_class_repr():
    '''Tests ReleaseUID model - repr
    '''
    release_id = random.randint(1e5, 1e6)
    length = random.randint(1e1, 1e2)
    chars_sets = string.ascii_letters + string.digits
    uid = make_random_text(length, chars_sets)

    release = Release(id=release_id)
    obj = ReleaseUID(release=release, uid=uid)

    assert str(obj) == '[%s] %s...' % (obj.release_id, obj.uid[:32])


@pytest.mark.django_db
def test_releaseuid_gen_uid_too_long_prefix():
    '''Tests ReleaseUID model - gen_uid method, too long prefix
    '''
    org = Organization.objects.create(
        name='Org #' + str(random.randint(1e5, 1e6)))

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    uids = []
    for _ in range(random.randint(1e1, 1e2)):
        release.release_ver = ''.join(
            random.choice(ReleaseUID.UID_CHARS)
            for _ in range(ReleaseUID.UID_MAX_LEN))
        try:
            uid = ReleaseUID.gen_uid(release, org)
            ReleaseUID.objects.create(
                organization=org, release=release, uid=uid)
            uids.append(uid)
            assert False
        except AssertionError:
            pass

    assert not uids
    assert not ReleaseUID.objects.filter(
        organization=org).values_list('uid', flat=True)


@pytest.mark.django_db
def test_releaseuid_gen_uid_ok_prefix():
    '''Tests ReleaseUID model - gen_uid method, OK prefix
    '''
    org = Organization.objects.create(
        name='Org #' + str(random.randint(1e5, 1e6)))

    unreal_ver = str(random.random())
    release_ver = 'R#' + str(random.randint(1e5, 1e6))
    release = Release.objects.create(
        unreal_ver=unreal_ver, release_ver=release_ver, changes='')

    uids = []
    for _ in range(random.randint(1e1, 1e2)):
        uid = ''
        while not uid or uid in uids:
            uid = ReleaseUID.gen_uid(release, org)
        ReleaseUID.objects.create(organization=org, release=release, uid=uid)
        uids.append(uid)

    assert len(uids) == len(set(uids))
    assert set(uids) == set(ReleaseUID.objects.filter(
        organization=org).values_list('uid', flat=True))

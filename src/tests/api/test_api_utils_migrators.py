# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import json
import random

from semver import (
    parse_version_info as pvi,
)

from django.conf import settings

from narra_backend.api.utils.packages import (
    try_package_migrate,
)
from narra_backend.api.utils.migrators import (
    VersionMigrator,
)

from .commons import (
    PACKAGE_DEF,
    TEST_DATA_TO_MIGRATE_FMT,
)


def test_get_next_version_no_newer_version():
    '''Tests VersionMigrator.get_next_version - no newer version
    '''
    old_ver = '1.0.0'
    new_ver = '1.0.1'
    vermig = VersionMigrator({}, new_ver, new_ver, [old_ver, new_ver])

    try:
        _ = vermig.get_next_version()
        assert False
    except StopIteration:
        pass


def test_get_next_version_have_newer_version():
    '''Tests VersionMigrator.get_next_version - have newer version
    '''
    old_ver = '1.0.0'
    new_ver = '1.0.1'
    vermig = VersionMigrator({}, old_ver, new_ver, [old_ver, new_ver])

    assert vermig.get_next_version() == pvi(new_ver)


def test_get_next_version_out_of_lower_bound_version():
    '''Tests VersionMigrator.get_next_version - out of lower bound version
    '''
    oob_ver = '1.0.0'
    old_ver = '1.0.1'
    new_ver = '1.0.2'
    vermig = VersionMigrator({}, oob_ver, new_ver, [old_ver, new_ver])

    assert vermig.get_next_version() == pvi(old_ver)


def test_get_next_version_out_of_upper_bound_version():
    '''Tests VersionMigrator.get_next_version - out of upper bound version
    '''
    old_ver = '1.0.0'
    new_ver = '1.0.1'
    oob_ver = '1.0.2'
    vermig = VersionMigrator({}, oob_ver, new_ver, [old_ver, new_ver])

    try:
        _ = vermig.get_next_version()
        assert False
    except StopIteration:
        pass


def test_get_next_version_non_exist_version():
    '''Tests VersionMigrator.get_next_version - no existing version
    '''
    old_ver = '1.0.0'
    nex_ver = '1.0.1'
    new_ver = '1.0.2'
    vermig = VersionMigrator({}, nex_ver, new_ver, [old_ver, new_ver])

    assert vermig.get_next_version() == pvi(new_ver)


def test_versionmigrator_no_next_version_error():
    '''Tests VersionMigrator - no next version error
    '''
    rand_str = 'rand_str_' + str(random.randint(1e5, 1e6))
    package_dc = {rand_str: rand_str}
    old_ver = '1.0.0'
    nex_ver = '1.0.1'
    new_ver = '1.0.2'
    vermig = VersionMigrator(package_dc, nex_ver, new_ver, [old_ver, nex_ver])

    assert vermig.migrate() == package_dc


def test_versionmigrator_no_versions_migrator_error():
    '''Tests VersionMigrator - no versions migrator error
    '''
    rand_str = 'rand_str_' + str(random.randint(1e5, 1e6))
    package_dc = {rand_str: rand_str}
    old_ver = '0.0.9000'
    new_ver = '0.0.9001'
    vermig = VersionMigrator(package_dc, old_ver, new_ver, [old_ver, new_ver])

    assert vermig.migrate() == package_dc


def test_try_package_migrate_no_migration():
    '''Tests try_package_migrate method - no migration
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)

    assert try_package_migrate(test_data) == PACKAGE_DEF


def test_try_package_migrate_do_migration_from_oldest_to_latest_stepped():
    '''Tests try_package_migrate method - do migration from oldest
        to latest version (stepped migration)
    '''
    versions = sorted(set([pvi(settings.PACKAGE_JSON_VER_MIN)] + [
        pvi(ver) for ver in settings.PACKAGE_VERSIONS]))

    ver_index = 0
    while ver_index < len(versions) - 1:
        from_ver = str(versions[ver_index])
        to_ver = str(versions[ver_index + 1])

        with open(
                TEST_DATA_TO_MIGRATE_FMT % {'ver': from_ver}, 'rb') as fd_obj:
            old_package_dc = json.load(fd_obj)
        with open(
                TEST_DATA_TO_MIGRATE_FMT % {'ver': to_ver}, 'rb') as fd_obj:
            new_package_dc = json.load(fd_obj)

        assert try_package_migrate(
            old_package_dc, to_version=to_ver) == new_package_dc

        ver_index += 1


def test_try_package_migrate_do_migration_from_oldest_to_latest_oneshot():
    '''Tests try_package_migrate method - do migration from oldest
        to latest version (one-shot migration)
    '''
    versions = sorted(set([pvi(settings.PACKAGE_JSON_VER_MIN)] + [
        pvi(ver) for ver in settings.PACKAGE_VERSIONS]))

    from_ver = str(versions[0])
    to_ver = str(versions[-1])

    with open(TEST_DATA_TO_MIGRATE_FMT % {'ver': from_ver}, 'rb') as fd_obj:
        old_package_dc = json.load(fd_obj)
    with open(TEST_DATA_TO_MIGRATE_FMT % {'ver': to_ver}, 'rb') as fd_obj:
        new_package_dc = json.load(fd_obj)

    assert try_package_migrate(old_package_dc) == new_package_dc

# -*- coding: utf-8 -*-

'''Tests module
'''

import copy

from django.conf import settings

from narra_backend.api.utils.packages import (
    try_package_migrate,
)

from .commons import (
    PACKAGE_DEF,
    PACKAGE_HELPER_DEF,
)


def test_try_package_migrate_do_migration_from_4_5_0_to_4_6_0():
    '''Tests try_package_migrate method - do migration 4.5.0 -> 4.6.0
    '''
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.5.0'
    old_package_dc['JSONVersion'] = ver
    old_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    old_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    phelp_def = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_def['Type'] = 'Comment'
    old_package_dc['Helpers'].append(phelp_def)

    new_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.6.0'
    new_package_dc['JSONVersion'] = ver
    new_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    new_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    phelp_def = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_def['Type'] = 'Comment'
    phelp_def['Id'] = ''
    new_package_dc['Helpers'].append(phelp_def)

    _new_package_dc = try_package_migrate(old_package_dc, to_version='4.6.0')

    assert new_package_dc == _new_package_dc

# -*- coding: utf-8 -*-

'''Tests module
'''

import copy

from django.conf import settings

from narra_backend.api.utils.packages import (
    try_package_migrate,
)

from .commons import (
    NODE_DEF,
    PACKAGE_DEF,
)


def test_try_package_migrate_do_migration_from_4_3_0_to_4_4_0():
    '''Tests try_package_migrate method - do migration 4.3.0 -> 4.4.0
    '''
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.3.0'
    old_package_dc['JSONVersion'] = ver
    old_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    old_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Type'] = 'End'
    old_package_dc['Nodes'].append(node_def)

    new_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.4.0'
    new_package_dc['JSONVersion'] = ver
    new_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    new_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Type'] = 'End'
    node_def['InPins'] = 1
    new_package_dc['Nodes'].append(node_def)

    _new_package_dc = try_package_migrate(old_package_dc, to_version='4.4.0')

    assert new_package_dc == _new_package_dc


def test_try_package_migrate_do_migration_from_4_3_0_to_4_4_0_bad_conditon():
    '''Tests try_package_migrate method - do migration 4.3.0 -> 4.4.0,
        bad Condition mode
    '''
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.3.0'
    old_package_dc['JSONVersion'] = ver
    old_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    old_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Type'] = 'Condition'
    node_def['Meta']['Mode'] = 'Foo'
    old_package_dc['Nodes'].append(node_def)

    try:
        try_package_migrate(old_package_dc, to_version='4.4.0')

        assert False
    except ValueError:
        pass


def test_try_package_migrate_do_migration_from_4_3_0_to_4_4_0_bad_node_type():
    '''Tests try_package_migrate method - do migration 4.3.0 -> 4.4.0,
        bad node type
    '''
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.3.0'
    old_package_dc['JSONVersion'] = ver
    old_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    old_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Type'] = 'Foo'
    old_package_dc['Nodes'].append(node_def)

    try:
        try_package_migrate(old_package_dc, to_version='4.4.0')

        assert False
    except ValueError:
        pass

# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import random

from django.conf import settings

from narra_backend.api.utils.packages import (
    try_package_migrate,
)

from .commons import (
    NODE_DEF,
    PACKAGE_ASSET_DEF,
    PACKAGE_DEF,
)


def test_try_package_migrate_do_migration_from_4_4_0_to_4_5_0():
    '''Tests try_package_migrate method - do migration 4.4.0 -> 4.5.0
    '''
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.4.0'
    old_package_dc['JSONVersion'] = ver
    old_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    old_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    asset_types = [
        'NEntityTypeLocation',
        'NEntityTypeObject',
    ]
    uri1 = 'uri' + str(random.randint(1e5, 1e6))
    uri2 = uri1
    while uri2 == uri1:
        uri2 = 'uri' + str(random.randint(1e5, 1e6))

    asset_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    asset_def['Class'] = 'NEntity'
    asset_def['Meta'] = {
        'Types': asset_types,
    }
    asset_def['Uri'] = uri1
    old_package_dc['Assets'].append(asset_def)

    asset_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    asset_def['Class'] = 'NEntity'
    asset_def['Uri'] = uri2
    old_package_dc['Assets'].append(asset_def)

    cases = []
    for _ in range(random.randint(1e1, 1e2)):
        case = ''
        while not case or case in cases:
            case = 'Val' + str(random.randint(1e5, 1e6))
        cases.append(case)
    iter_outpins = random.randint(1e1, 1e2)
    rand_outpins = random.randint(1e1, 1e2)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Type'] = 'Condition'
    node_def['Meta']['Mode'] = 'Switch'
    node_def['Meta']['Cases'] = cases

    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Type'] = 'Condition'
    _node_def['Meta']['Mode'] = 'Random'
    _node_def['OutPins'] = rand_outpins
    node_def['Components'].append(_node_def)

    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Type'] = 'Condition'
    _node_def['Meta']['Mode'] = 'Iterate'
    _node_def['OutPins'] = iter_outpins
    node_def['Components'].append(_node_def)

    old_package_dc['Nodes'].append(node_def)

    new_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '4.5.0'
    new_package_dc['JSONVersion'] = ver
    new_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    new_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    asset_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    asset_def['Class'] = 'NEntity'
    asset_def['Meta'] = {
        'Types': asset_types,
        'IsEnabled': True,
    }
    asset_def['Uri'] = uri1
    new_package_dc['Assets'].append(asset_def)

    asset_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    asset_def['Class'] = 'NEntity'
    asset_def['Meta'] = {
        'Types': [],
        'IsEnabled': True,
    }
    asset_def['Uri'] = uri2
    new_package_dc['Assets'].append(asset_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Type'] = 'Condition'
    node_def['Weight'] = 0
    node_def['Meta']['Mode'] = 'Switch'
    node_def['Meta']['Cases'] = [{
        'Name': 'Case #' + str(idx + 1),
        'Value': case_str,
    } for idx, case_str in enumerate(cases)]

    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Type'] = 'Condition'
    _node_def['Weight'] = 0
    _node_def['Meta']['Mode'] = 'Random'
    _node_def['OutPins'] = rand_outpins
    _node_def['Meta']['Cases'] = [{
        'Name': 'Case #' + str(idx + 1),
    } for idx in range(rand_outpins)]
    node_def['Components'].append(_node_def)

    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Type'] = 'Condition'
    _node_def['Weight'] = 0
    _node_def['Meta']['Mode'] = 'Iterate'
    _node_def['OutPins'] = iter_outpins
    _node_def['Meta']['Cases'] = [{
        'Name': 'Case #' + str(idx + 1),
    } for idx in range(iter_outpins)]
    node_def['Components'].append(_node_def)

    new_package_dc['Nodes'].append(node_def)

    _new_package_dc = try_package_migrate(old_package_dc, to_version='4.5.0')

    assert new_package_dc == _new_package_dc

# -*- coding: utf-8 -*-

'''Tests module
'''

import copy

from narra_backend.api.utils.packages import (
    try_package_migrate,
)

from .commons import (
    PACKAGE_DEF,
)


def test_try_package_migrate_do_migration_from_3_6_1_to_4_3_0():
    '''Tests try_package_migrate method - do migration 3.6.1 -> 4.3.0
        No migration available
    '''
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    old_package_dc['JSONVersion'] = '3.6.1'

    new_package_dc = try_package_migrate(old_package_dc, to_version='4.3.0')

    assert new_package_dc == old_package_dc

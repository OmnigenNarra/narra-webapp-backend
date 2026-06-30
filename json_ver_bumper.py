#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''JSON version bumping script
'''

import json
import os

from semver import parse_version_info as pvi


JSON_PARAMS = dict(sort_keys=True, indent=2, ensure_ascii=False)
SCHEMA_PATH = 'src/narra_backend/static/schemas/%(ver)s.json'

MIGRATOR_PATH_FMT = \
    'src/narra_backend/api/utils/migrators/from_%(old_ver)s_to_%(new_ver)s.py'
MIGRATOR_BODY = '''# -*- coding: utf-8 -*-

\'\'\'Migration module
\'\'\'

from django.conf import settings


def migrate(package_dc):
    \'\'\'Migration method
    \'\'\'
    ver = '%(new_json_ver)s'
    package_dc['JSONVersion'] = ver
    package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver]['StoryVersion']
    package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']



    return package_dc'''

TEST_MIGRATOR_PATH_FMT = \
    'src/tests/api/test_api_utils_migrator_%(old_ver)s__%(new_ver)s.py'
TEST_MIGRATOR_BODY = '''# -*- coding: utf-8 -*-

\'\'\'Tests module
\'\'\'

import copy

from django.conf import settings

from narra_backend.api.utils.packages import (
    try_package_migrate,
)

from .commons import (
    PACKAGE_DEF,
)


def test_try_package_migrate_do_migration_from_%(old_ver)s_to_%(new_ver)s():
    \'\'\'Tests try_package_migrate method - do migration %(old_json_ver)s -> %(new_json_ver)s
    \'\'\'
    old_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '%(old_json_ver)s'
    old_package_dc['JSONVersion'] = ver
    old_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    old_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']



    new_package_dc = copy.deepcopy(PACKAGE_DEF)
    ver = '%(new_json_ver)s'
    new_package_dc['JSONVersion'] = ver
    new_package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver][
        'StoryVersion']
    new_package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']



    _new_package_dc = try_package_migrate(old_package_dc, to_version='%(new_json_ver)s')

    assert new_package_dc == _new_package_dc'''


def pre_phase(old_json_ver, new_json_ver):
    '''Pre- phase
    '''
    with open(SCHEMA_PATH % {'ver': old_json_ver}, 'r') as rf_obj, \
            open(SCHEMA_PATH % {'ver': new_json_ver}, 'w') as wf_obj:
        schema_dc = json.load(rf_obj)
        schema_dc['properties']['JSONVersion']['const'] = str(new_json_ver)
        json.dump(schema_dc, wf_obj, **JSON_PARAMS)

    path = 'src/doc/API/examples/package-check-resp.json'
    with open(path, 'r+') as fd_obj:
        json_dc = json.load(fd_obj)
        fd_obj.truncate(0)
        fd_obj.seek(0, os.SEEK_SET)
        json_dc['current_json_version'] = str(new_json_ver)
        json.dump(json_dc, fd_obj, **JSON_PARAMS)

    symlinks = [
        ('src/doc/API/examples', 'package-%(ver)s.json', 'package.json'),
        ('src/narra_backend/static/schemas', '%(ver)s.json', 'current.json'),
        ('src/tests/_data', 'package-%(ver)s.json', 'package.json'),
    ]
    for dpath, src_fmt, dst in symlinks:
        cwd = os.getcwd()
        os.chdir(dpath)
        os.remove(dst)
        os.symlink(src_fmt % {'ver': new_json_ver}, dst)
        os.chdir(cwd)

    substs_dc = {
        'old_json_ver': str(old_json_ver),
        'old_ver': str(old_json_ver).replace('.', '_'),
        'new_json_ver': str(new_json_ver),
        'new_ver': str(new_json_ver).replace('.', '_'),
    }

    with open(MIGRATOR_PATH_FMT % substs_dc, 'w') as fd_obj:
        fd_obj.write(MIGRATOR_BODY % substs_dc)
    with open(TEST_MIGRATOR_PATH_FMT % substs_dc, 'w') as fd_obj:
        fd_obj.write(TEST_MIGRATOR_BODY % substs_dc)


def post_phase(old_json_ver, new_json_ver):
    '''Post- phase
    '''
    import django
    django.setup()

    from narra_backend.api.utils.packages import try_package_migrate

    packages = [
        'src/doc/API/examples/package-%(ver)s.json',
        'src/tests/_data/migrations/package-%(ver)s.json',
        'src/tests/_data/package-%(ver)s.json',
    ]
    for path_fmt in packages:
        with open(path_fmt % {'ver': old_json_ver}, 'r') as rf_obj, \
                open(path_fmt % {'ver': new_json_ver}, 'w') as wf_obj:
            package_dc = try_package_migrate(
                json.load(rf_obj), to_version=str(new_json_ver))
            json.dump(package_dc, wf_obj, **JSON_PARAMS)


def main():
    '''Main method
    '''
    phase = os.sys.argv[1]
    old_json_ver = pvi(os.sys.argv[2])
    new_json_ver = pvi(os.sys.argv[3])

    if phase == 'pre':
        pre_phase(old_json_ver, new_json_ver)
    elif phase == 'post':
        post_phase(old_json_ver, new_json_ver)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-

'''Tests common module
'''

import os

from hypothesis import strategies as st
from semver import (
    format_version,
    VersionInfo,
)

from django.conf import settings


NODE_DEF = {
    'Assets': [],
    'Components': [],
    'Description': '',
    'Id': '',
    'InLinks': [],
    'InPins': 0,
    'Meta': {},
    'Name': '',
    'OutLinks': [],
    'OutPins': 0,
    'PosX': 0,
    'PosY': 0,
    'Tags': [],
    'TriggerTags': [],
    'Type': '',
    'Weight': 0,
}
PACKAGE_ASSET_DEF = {
    'Class': '',
    'Meta': {},
    'Uri': '',
}
PACKAGE_HELPER_DEF = {
    'Id': '',
    'Meta': {},
    'Name': '',
    'PosX': 0,
    'PosY': 0,
    'SizeX': 0,
    'SizeY': 0,
    'Type': '',
}
NODE_ASSET_DEF = {
    'Class': '',
    'Uris': [],
}
PACKAGE_ACTION_DEF = {
    'Name': '',
    'Params': [
        {
            'AssetClass': '',
            'EntityTypes': [],
            'Label': '',
            'Mandatory': False,
        },
    ],
}
PACKAGE_DEF = {
    'JSONVersion': settings.PACKAGE_JSON_VER,
    'UAssetVersion': settings.PACKAGE_UASSET_VER,
    'StoryVersion': settings.PACKAGE_STORY_VER,
    'Actions': [],
    'Assets': [],
    'EntityTypes': [
        {
            'Name': 'NEntityTypeCharacter',
            'Children': [],
        },
        {
            'Name': 'NEntityTypeLocation',
            'Children': [],
        },
        {
            'Name': 'NEntityTypeObject',
            'Children': [],
        },
    ],
    'Helpers': [],
    'ModTime': '0',
    'Nodes': [],
    'StoryName': '',
}

TEST_DATA_DIR = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), '..', '_data')
TEST_DATA_FNAME = 'package.json'
TEST_DATA_FPATH = os.path.join(TEST_DATA_DIR, TEST_DATA_FNAME)
TEST_DATA_TO_MIGRATE_FMT = os.path.join(
    TEST_DATA_DIR, 'migrations', 'package-%(ver)s.json')


def dec_ver(version, max_ver=99):
    '''Decrement (de-bump) version
    '''
    verinfo = VersionInfo.parse(version)
    if verinfo == VersionInfo.parse('0.0.0'):
        raise ValueError('Version too low')

    borrow_minor = False
    patch = verinfo.patch
    if patch == 0:
        patch = max_ver
        borrow_minor = True
    else:
        patch -= 1

    borrow_major = False
    minor = verinfo.minor
    if borrow_minor:
        if minor == 0:
            minor = max_ver
            borrow_major = True
        else:
            minor -= 1

    major = verinfo.major - 1 if borrow_major else verinfo.major

    return format_version(major, minor, patch)


def inc_ver(version, max_ver=99):
    '''Increment (bump) version
    '''
    verinfo = VersionInfo.parse(version)
    if verinfo == VersionInfo.parse('.'.join(
            [str(max_ver) for _ in range(3)])):
        raise ValueError('Version too high')

    carry_minor = False
    patch = verinfo.patch
    if patch == max_ver:
        patch = 0
        carry_minor = True
    else:
        patch += 1

    carry_major = False
    minor = verinfo.minor
    if carry_minor:
        if minor == max_ver:
            minor = 0
            carry_major = True
        else:
            minor += 1

    major = verinfo.major + 1 if carry_major else verinfo.major

    return format_version(major, minor, patch)


def valid_json_ver():
    '''Returns valid JSONVersion value strategy
    '''
    return st.sampled_from(settings.PACKAGE_VERSIONS)


def valid_story_ver(data_st, json_ver_st):
    '''Returns valid StoryVersion value strategy
    '''
    return st.just(
        settings.PACKAGE_VERSIONS[data_st.draw(json_ver_st)]['StoryVersion'])


def valid_uasset_ver(data_st, json_ver_st):
    '''Returns valid UAssetVersion value strategy
    '''
    return st.just(
        settings.PACKAGE_VERSIONS[data_st.draw(json_ver_st)]['UAssetVersion'])


def valid_text(**extra):
    '''Returns valid text value strategy
    '''
    if 'alphabet' not in extra:
        extra['alphabet'] = st.characters(blacklist_categories=('Cc', 'Cs'))

    return st.text(**extra)

# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import json
import random
from datetime import timedelta
from uuid import uuid4

import emoji
import pytest

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from narra_backend.api.models import (
    Node,
    NodeAsset,
    NodeType,
    Package,
    PackageAction,
    PackageAsset,
    PackageHelper,
    PackageHelperType,
)
from narra_backend.units.models import (
    Member,
)
from narra_backend.api.utils.packages import (
    assets_mismatch,
    entity_types_mismatch,
    fetch_entity_types,
    is_package_invalid,
    nodes_ids_mismatch,
    parse_package_upload,
    store_package,
    transform_validate_package,
    versions_check,
)

from .commons import (
    dec_ver,
    inc_ver,
    NODE_ASSET_DEF,
    NODE_DEF,
    PACKAGE_ASSET_DEF,
    PACKAGE_HELPER_DEF,
    PACKAGE_DEF,
    TEST_DATA_FNAME,
    TEST_DATA_FPATH,
)


# admin:admin
TEST_HTTP_AUTHZ = 'YWRtaW46YWRtaW4='


@pytest.mark.django_db
def test_store_package_empty_json():
    '''Tests store_package method - bad JSON
    '''
    package_dc = {}
    package_obj = Package()
    package_obj.filename = TEST_DATA_FNAME
    package_obj.save()
    assert package_obj.id is not None
    assert Node.objects.filter(package=package_obj).count() == 0
    try:
        store_package(package_obj, package_dc)
        assert False
    except KeyError:
        pass

    assert Node.objects.filter(package=package_obj).count() == 0
    package_obj.delete()
    assert Package.objects.filter(pk=package_obj.id).count() == 0


@pytest.mark.django_db
def test_store_package_ok_json():
    '''Tests store_package method - bad JSON
    '''
    with open(TEST_DATA_FPATH, 'rb') as fd_obj:
        package_dc = json.load(fd_obj)
        package_obj = Package()
        package_obj.filename = TEST_DATA_FNAME
        package_obj.save()
        assert package_obj.id is not None
        assert Node.objects.filter(package=package_obj).count() == 0
        store_package(package_obj, package_dc)
        assert Node.objects.filter(package=package_obj).count() > 0
        package_obj.delete()
        assert Node.objects.filter(package=package_obj).count() == 0
        assert Package.objects.filter(pk=package_obj.id).count() == 0


def test_versions_check_bad_package():
    '''Tests versions_check - bad package
    '''
    assert versions_check('foo') == ('', False, False)


def test_versions_check_no_versions():
    '''Tests versions_check - no versions
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    del test_data['JSONVersion']

    assert versions_check(test_data) == ('', False, False)


def test_versions_check_post_2_1_0_invalid():
    '''Tests versions_check - invalid post-2.1.0 version
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = '2.1.0.0.0.0'

    assert versions_check(test_data) == ('', False, False)


def test_versions_check_post_2_1_0_valid():
    '''Tests versions_check - valid post-2.1.0 version
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = '2.1.1'

    assert versions_check(test_data) == (
        test_data['JSONVersion'], False, False)


def test_versions_check_not_supported_lower():
    '''Tests versions_check - not supported version, lower range
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = dec_ver(settings.PACKAGE_JSON_VER_MIN)

    assert versions_check(test_data) == (
        test_data['JSONVersion'], False, False)


def test_versions_check_not_supported_upper():
    '''Tests versions_check - not supported version, upper range
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = inc_ver(settings.PACKAGE_JSON_VER)

    assert versions_check(test_data) == (
        test_data['JSONVersion'], False, False)


def test_versions_check_no_migration_required_obsolete():
    '''Tests versions_check - no version migration required (obsolete version)
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = '2.12.0'

    json_ver, is_version_supported, migration_required = versions_check(
        test_data)

    assert json_ver == test_data['JSONVersion']
    assert not is_version_supported
    assert not migration_required


def test_versions_check_no_migration_required_latest():
    '''Tests versions_check - no version migration required (latest version)
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = settings.PACKAGE_JSON_VER

    json_ver, is_version_supported, migration_required = versions_check(
        test_data)

    assert json_ver == test_data['JSONVersion']
    assert is_version_supported
    assert not migration_required


def test_versions_check_migration_not_required():
    '''Tests versions_check - version migration not required
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    test_data['JSONVersion'] = settings.PACKAGE_JSON_VER

    json_ver, is_version_supported, migration_required = versions_check(
        test_data)

    assert json_ver == test_data['JSONVersion']
    assert is_version_supported
    assert not migration_required


def test_assets_mismatch_missing_asset_class():
    '''Tests assets_mismatch - missing asset class
    '''
    asset_def = copy.deepcopy(NODE_ASSET_DEF)
    asset_def['Class'] = PackageAsset.TYPE_FACT
    asset_def['Uris'].append('DerFact')

    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['Type'] = NodeType.End.value
    _node_def['Assets'].append(asset_def)
    test_data['Nodes'].append(_node_def)

    errors, op_msg = assets_mismatch(test_data)

    assert errors
    assert op_msg.startswith('Missing class: ')


def test_assets_mismatch_missing_asset_name():
    '''Tests assets_mismatch - missing asset name
    '''
    asset_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    asset_def['Class'] = PackageAsset.TYPE_FACT
    asset_def['Uri'] = 'DerFact1'

    _asset_def = copy.deepcopy(NODE_ASSET_DEF)
    _asset_def['Class'] = asset_def['Class']
    _asset_def['Uris'].extend([asset_def['Uri']] + ['DerFact2'])

    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['Type'] = NodeType.End.value
    _node_def['Assets'].append(_asset_def)
    test_data['Nodes'].append(_node_def)
    test_data['Assets'].append(asset_def)

    errors, op_msg = assets_mismatch(test_data)

    assert errors
    assert op_msg.startswith('Extra URIs: ')


def test_assets_mismatch_ok_assets():
    '''Tests assets_mismatch - OK asset
    '''
    asset_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    asset_def['Class'] = PackageAsset.TYPE_FACT
    asset_def['Uri'] = 'DerFact'

    _asset_def = copy.deepcopy(NODE_ASSET_DEF)
    _asset_def['Class'] = asset_def['Class']
    _asset_def['Uris'].append(asset_def['Uri'])

    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['Type'] = NodeType.End.value
    _node_def['Assets'].append(_asset_def)
    test_data['Nodes'].append(_node_def)
    test_data['Assets'].append(asset_def)

    errors, _ = assets_mismatch(test_data)

    assert not errors


def test_nodes_ids_mismatch_duplicate_nids():
    '''Tests nodes_ids_mismatch - duplicate nodes' IDs
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    test_data['Nodes'].append(_node_def)
    test_data['Nodes'].append(_node_def)

    errors, op_msg = nodes_ids_mismatch(test_data)

    assert errors
    assert str(op_msg).startswith('Duplicated')


def test_nodes_ids_mismatch_missing_nids_by_inlinks():
    '''Tests nodes_ids_mismatch - missing nodes' IDs (by InLinks)
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['InLinks'].append({
        'LinkedNodeId': 'NStoryBlock_End_1',
    })
    test_data['Nodes'].append(_node_def)

    errors, op_msg = nodes_ids_mismatch(test_data)

    assert errors
    assert str(op_msg).startswith('Missing')


def test_nodes_ids_mismatch_missing_nids_by_outlinks():
    '''Tests nodes_ids_mismatch - missing nodes' IDs (by OutLinks)
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['OutLinks'].append({
        'LinkedNodeId': 'NStoryBlock_End_1',
    })
    test_data['Nodes'].append(_node_def)

    errors, op_msg = nodes_ids_mismatch(test_data)

    assert errors
    assert str(op_msg).startswith('Missing')


def test_nodes_ids_mismatch_mm_links():
    '''Tests nodes_ids_mismatch - mismatched links
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node0_def = copy.deepcopy(NODE_DEF)
    _node0_def['Id'] = 'NStoryBlock_Start_0'
    _node0_def['OutLinks'].append({
        'LinkedNodeId': 'NStoryBlock_End_1',
    })
    test_data['Nodes'].append(_node0_def)
    _node1_def = copy.deepcopy(NODE_DEF)
    _node1_def['Id'] = 'NStoryBlock_End_1'
    test_data['Nodes'].append(_node1_def)

    errors, op_msg = nodes_ids_mismatch(test_data)

    assert errors
    assert str(op_msg).startswith('Mismatched')


def test_nodes_ids_mismatch_ok_nids():
    '''Tests nodes_ids_mismatch - OK nodes' IDs
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    test_data['Nodes'].append(_node_def)

    errors, op_msg = nodes_ids_mismatch(test_data)

    assert not errors
    assert 'OK' in str(op_msg)


def test_is_package_invalid_no_dict():
    '''Tests is_package_invalid - no dict
    '''
    is_invalid, _ = is_package_invalid('')
    assert is_invalid


def test_is_package_invalid_empty():
    '''Tests is_package_invalid - empty dict
    '''
    is_invalid, _ = is_package_invalid({})
    assert is_invalid


@pytest.mark.skipif(
    not settings.USE_JSONSCHEMA,
    reason='jsonschema usage disabled')
def test_is_package_invalid_invalid_package():
    '''Tests is_package_invalid - invalid package
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    del test_data['Nodes']

    is_invalid, _ = is_package_invalid(test_data)
    assert is_invalid


def test_is_package_invalid_assets_mismatch():
    '''Tests is_package_invalid - assets mismatch
    '''
    asset_def = copy.deepcopy(NODE_ASSET_DEF)
    asset_def['Class'] = PackageAsset.TYPE_FACT
    asset_def['Uris'].append('DerFact')
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['Type'] = NodeType.End.value
    _node_def['Assets'].append(asset_def)
    test_data['Nodes'].append(_node_def)

    is_invalid, _ = is_package_invalid(test_data)
    assert is_invalid


def test_is_package_invalid_valid_package():
    '''Tests is_package_invalid - valid package
    '''
    test_data = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['Type'] = NodeType.End.value
    test_data['Nodes'].append(_node_def)

    is_invalid, _ = is_package_invalid(test_data)
    assert not is_invalid


@pytest.mark.django_db
def test_parse_package_upload_no_json():
    '''Tests parse_package_upload method - no JSON
    '''
    prev_cnt = Package.objects.all().count()
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, b'', content_type='application/json'), author)
    assert package_obj is None
    assert str(op_msg).startswith('Bad JSON')
    assert Package.objects.all().count() == prev_cnt


@pytest.mark.django_db
def test_parse_package_upload_bad_json():
    '''Tests parse_package_upload method - bad JSON
    '''
    prev_cnt = Package.objects.all().count()
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, b'{}', content_type='application/json'), author)
    assert package_obj is None
    assert str(op_msg).startswith('Invalid package')
    assert Package.objects.all().count() == prev_cnt


@pytest.mark.django_db
def test_parse_package_upload_empty_json():
    '''Tests parse_package_upload method - "empty" JSON
    '''
    prev_cnt = Package.objects.all().count()
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(PACKAGE_DEF), encoding='utf-8'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert Package.objects.all().count() == prev_cnt + 1
    assert Node.objects.filter(package=package_obj).count() == 0
    assert PackageAsset.objects.filter(package=package_obj).count() == 0


@pytest.mark.django_db
def test_parse_package_upload_bad_nids():
    '''Tests parse_package_upload - bad nodes' IDs
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)
    _node_def = copy.deepcopy(NODE_DEF)
    _node_def['Id'] = 'NStoryBlock_End_0'
    _node_def['Type'] = NodeType.End.value
    package_dc['Nodes'].append(_node_def)
    package_dc['Nodes'].append(_node_def)

    prev_cnt = Package.objects.all().count()
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg).startswith('Invalid package')
    assert package_obj is None
    assert Package.objects.all().count() == prev_cnt


@pytest.mark.django_db
def test_parse_package_upload_ok_json():
    '''Tests parse_package_upload method - OK JSON
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, open(TEST_DATA_FPATH, 'rb').read(),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert Node.objects.filter(package=package_obj).count() > 0
    assert PackageAsset.objects.filter(package=package_obj).count() > 0


@pytest.mark.django_db
def test_parse_package_upload_ok_json_doubled_fact():
    '''Tests parse_package_upload method - OK JSON, doubled fact
    '''
    fact_name = 'Fact_' + str(random.randint(1e5, 1e6))
    package_dc = copy.deepcopy(PACKAGE_DEF)

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name
    package_dc['Assets'].append(passet_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_Condition_' + str(random.randint(1e5, 1e6))
    node_def['Description'] = emoji.emojize(':video_game:')
    node_def['Meta'].update({
        'Mode': 'Branch',
        'Cases': [
            {
                'Name': '',
                'Junction': [
                    'NOR',
                ],
                'Rules': [
                    {
                        'Fact': 0,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 1,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
        ],
    })
    node_def['Type'] = NodeType.Condition.value

    nasset_def = copy.deepcopy(NODE_ASSET_DEF)
    nasset_def['Class'] = PackageAsset.TYPE_FACT
    nasset_def['Uris'].extend([fact_name, fact_name])

    node_def['Assets'].append(nasset_def)

    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)

    nodes_qs = Node.objects.filter(package=package_obj)

    assert nodes_qs.count() == 1

    node_obj = nodes_qs[0]
    nassets_qs = NodeAsset.objects.order_by(
        'class_index', 'name_index').filter(node=node_obj)

    assert nassets_qs.count() == 2

    nassets = list(nassets_qs)

    assert nassets[0].package_asset.type == nassets[1].package_asset.type \
        == PackageAsset.TYPE_FACT
    assert nassets[0].class_index == nassets[1].class_index == 0
    assert nassets[0].name_index == 0
    assert nassets[1].name_index == 1

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_parse_package_upload_ok_json_two_facts():
    '''Tests parse_package_upload method - OK JSON, two facts
    '''
    fact_name_1 = 'Fact_' + str(random.randint(1e5, 1e6))
    fact_name_2 = fact_name_1
    while fact_name_2 == fact_name_1:
        fact_name_2 = 'Fact_' + str(random.randint(1e5, 1e6))

    fact_index_1 = random.randint(1e1, 1e2)
    fact_index_2 = fact_index_1
    while fact_index_2 < fact_index_1:
        fact_index_2 = random.randint(1e2, 1e3)

    package_dc = copy.deepcopy(PACKAGE_DEF)

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name_1
    package_dc['Assets'].append(passet_def)
    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name_2
    package_dc['Assets'].append(passet_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_Condition_' + str(random.randint(1e5, 1e6))
    node_def['Description'] = emoji.emojize(':video_game:')
    node_def['Meta'].update({
        'Mode': 'Branch',
        'Cases': [
            {
                'Name': '',
                'Junction': [
                    'NOR',
                ],
                'Rules': [
                    {
                        'Fact': 0,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 1,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
        ],
    })
    node_def['Type'] = NodeType.Condition.value

    nasset_def = copy.deepcopy(NODE_ASSET_DEF)
    nasset_def['Class'] = PackageAsset.TYPE_FACT
    nasset_def['Uris'].extend([fact_name_1, fact_name_2])
    node_def['Assets'].append(nasset_def)

    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)

    nodes_qs = Node.objects.filter(package=package_obj)

    assert nodes_qs.count() == 1

    node_obj = nodes_qs[0]
    nassets_qs = NodeAsset.objects.order_by(
        'class_index', 'name_index').filter(node=node_obj)

    assert nassets_qs.count() == 2

    nassets = list(nassets_qs)

    assert nassets[0].package_asset.type == nassets[1].package_asset.type \
        == PackageAsset.TYPE_FACT
    assert nassets[0].class_index == nassets[1].class_index == 0
    assert nassets[0].name_index == 0
    assert nassets[1].name_index == 1

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_parse_package_upload_ok_json_mixed_facts():
    '''Tests parse_package_upload method - OK JSON, mixed facts
    '''
    fact_name_1 = 'Fact_' + str(random.randint(1e5, 1e6))
    fact_name_2 = fact_name_1
    while fact_name_2 == fact_name_1:
        fact_name_2 = 'Fact_' + str(random.randint(1e5, 1e6))

    fact_index_1 = random.randint(1e1, 1e2)
    fact_index_2 = fact_index_1
    while fact_index_2 < fact_index_1:
        fact_index_2 = random.randint(1e2, 1e3)

    package_dc = copy.deepcopy(PACKAGE_DEF)

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name_1
    package_dc['Assets'].append(passet_def)
    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name_2
    package_dc['Assets'].append(passet_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_Condition_' + str(random.randint(1e5, 1e6))
    node_def['Description'] = emoji.emojize(':video_game:')
    node_def['Meta'].update({
        'Mode': 'Branch',
        'Cases': [
            {
                'Name': '',
                'Junction': [
                    'NOR',
                ],
                'Rules': [
                    {
                        'Fact': 0,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 1,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
            {
                'Name': '',
                'Junction': [
                    'NAND',
                ],
                'Rules': [
                    {
                        'Fact': 2,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 3,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
        ],
    })
    node_def['Type'] = NodeType.Condition.value

    nasset_def = copy.deepcopy(NODE_ASSET_DEF)
    nasset_def['Class'] = PackageAsset.TYPE_FACT
    nasset_def['Uris'].extend([
        fact_name_1,
        fact_name_2,
        fact_name_1,
        fact_name_2,
    ])
    node_def['Assets'].append(nasset_def)

    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_parse_package_upload_ok_json_unset_fact():
    '''Tests parse_package_upload method - OK JSON, unset fact
    '''
    fact_name_1 = 'Fact_' + str(random.randint(1e5, 1e6))
    fact_name_2 = fact_name_1
    while fact_name_2 == fact_name_1:
        fact_name_2 = 'Fact_' + str(random.randint(1e5, 1e6))

    fact_index_1 = random.randint(1e1, 1e2)
    fact_index_2 = fact_index_1
    while fact_index_2 < fact_index_1:
        fact_index_2 = random.randint(1e2, 1e3)

    package_dc = copy.deepcopy(PACKAGE_DEF)

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name_1
    package_dc['Assets'].append(passet_def)
    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = fact_name_2
    package_dc['Assets'].append(passet_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_Condition_' + str(random.randint(1e5, 1e6))
    node_def['Description'] = emoji.emojize(':video_game:')
    node_def['Meta'].update({
        'Mode': 'Branch',
        'Cases': [
            {
                'Name': '',
                'Junction': [
                    'NOR',
                ],
                'Rules': [
                    {
                        'Fact': 0,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 1,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
            {
                'Name': '',
                'Junction': [
                    'NAND',
                ],
                'Rules': [
                    {
                        'Fact': 2,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 3,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
        ],
    })
    node_def['Type'] = NodeType.Condition.value

    nasset_def = copy.deepcopy(NODE_ASSET_DEF)
    nasset_def['Class'] = PackageAsset.TYPE_FACT
    nasset_def['Uris'].extend([
        fact_name_1,
        fact_name_2,
        '',
        fact_name_2,
    ])
    node_def['Assets'].append(nasset_def)

    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_parse_package_upload_ok_json_mixed_assets():
    '''Tests parse_package_upload method - OK JSON, mixed assets
    '''
    asset_name_1 = 'Asset_' + str(random.randint(1e5, 1e6))
    asset_name_2 = asset_name_1
    while asset_name_2 == asset_name_1:
        asset_name_2 = 'Asset_' + str(random.randint(1e5, 1e6))

    package_dc = copy.deepcopy(PACKAGE_DEF)

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_STORY
    passet_def['Uri'] = asset_name_1
    package_dc['Assets'].append(passet_def)
    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_FACT
    passet_def['Uri'] = asset_name_2
    package_dc['Assets'].append(passet_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_Condition_' + str(random.randint(1e5, 1e6))
    node_def['Description'] = emoji.emojize(':video_game:')
    node_def['Meta'].update({
        'Mode': 'Branch',
        'Cases': [
            {
                'Name': '',
                'Junction': [
                    'NOR',
                ],
                'Rules': [
                    {
                        'Fact': 0,
                        'Compare': 'Exists',
                        'Value': 'Yup!',
                    },
                    {
                        'Fact': 1,
                        'Compare': 'Contains',
                        'Value': 'Some',
                    },
                ],
            },
        ],
    })
    node_def['Type'] = NodeType.Condition.value

    nasset_def = copy.deepcopy(NODE_ASSET_DEF)
    nasset_def['Class'] = PackageAsset.TYPE_STORY
    nasset_def['Uris'].extend([
        asset_name_1,
    ])
    node_def['Assets'].append(nasset_def)
    nasset_def = copy.deepcopy(NODE_ASSET_DEF)
    nasset_def['Class'] = PackageAsset.TYPE_FACT
    nasset_def['Uris'].extend([
        asset_name_2,
        asset_name_2,
    ])
    node_def['Assets'].append(nasset_def)

    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)

    nodes_qs = Node.objects.filter(package=package_obj)

    assert nodes_qs.count() == 1

    node_obj = nodes_qs[0]
    nassets_qs = NodeAsset.objects.order_by(
        'class_index', 'name_index').filter(node=node_obj)

    assert nassets_qs.count() == 3

    nassets = list(nassets_qs)

    assert nassets[0].package_asset.type == PackageAsset.TYPE_STORY
    assert nassets[1].package_asset.type == nassets[2].package_asset.type \
        == PackageAsset.TYPE_FACT
    assert nassets[0].class_index == 0
    assert nassets[1].class_index == nassets[2].class_index == 1
    assert nassets[0].name_index == 0
    assert nassets[1].name_index == 0
    assert nassets[2].name_index == 1

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_nodetype_custom_storage_retrieve():
    '''Tests NodeType.Custom storage & retrieve
    '''
    custom_params_values = [
        # (param, value)
        ('Enum', 'A'),
        ('String', ''),
        ('Struct', '0'),
    ]

    package_dc = copy.deepcopy(PACKAGE_DEF)
    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NCustomStoryBlock_Test_' + str(
        random.randint(1e5, 1e6))
    node_def['Name'] = 'H.M. Customs #' + str(random.randint(1e5, 1e6))
    node_def['Meta'].update(custom_params_values)
    node_def['Type'] = NodeType.Custom.value
    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    node_objs = Node.objects.filter(package=package_obj)
    assert node_objs.count() == len(package_dc['Nodes'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_nodetype_timeoutoption_storage_retrieve():
    '''Tests NodeType.TimeoutOption storage & retrieve
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)
    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_TimeoutOption_' + str(
        random.randint(1e5, 1e6))
    node_def['Name'] = 'TimeoutOption #' + str(random.randint(1e5, 1e6))
    node_def['Meta'].update({'Timeout': random.randint(1e2, 1e3)})
    node_def['Type'] = NodeType.ChoiceTimeout.value
    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    node_objs = Node.objects.filter(package=package_obj)
    assert node_objs.count() == len(package_dc['Nodes'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_packageaction_storage_retrieve():
    '''Tests PackageAction storage & retrieve
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)
    package_dc['Actions'].extend([
        {
            'Name': 'WaitTillNightfall',
            'Params': [],
        },
        {
            'Name': 'Reach',
            'Params': [
                {
                    'Label': 'Destination',
                    'AssetClass': PackageAsset.TYPE_ENTITY,
                    'EntityTypes': [
                        'NEntityTypeLocation',
                    ],
                    'Mandatory': True,
                },
            ],
        },
        {
            'Name': 'Receive',
            'Params': [
                {
                    'Label': 'Giver',
                    'AssetClass': PackageAsset.TYPE_ENTITY,
                    'EntityTypes': [
                        'NEntityTypeCharacter',
                    ],
                    'Mandatory': True,
                },
                {
                    'Label': 'Object',
                    'AssetClass': PackageAsset.TYPE_ENTITY,
                    'EntityTypes': [
                        'NEntityTypeObject',
                    ],
                    'Mandatory': True,
                },
            ],
        },
    ])
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    pact_objs = PackageAction.objects.filter(package=package_obj)
    assert pact_objs.count() == len(package_dc['Actions'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_packagehelper_comment_storage_retrieve():
    '''Tests PackageHelper, type Comment storage & retrieve
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)

    for _ in range(2):
        phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
        phelp_dc.update({
            'Id': str(uuid4()),
            'Type': PackageHelperType.Comment.value,
            'Name': 'Comment #' + str(random.randint(1e5, 1e6)),
            'PosX': random.randint(1e5, 1e6),
            'PosY': random.randint(1e5, 1e6),
            'SizeX': random.randint(1e5, 1e6),
            'SizeY': random.randint(1e5, 1e6),
            'Meta': {},
        })
        package_dc['Helpers'].append(phelp_dc)

    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    phelp_objs = PackageHelper.objects.filter(package=package_obj)
    assert phelp_objs.count() == len(package_dc['Helpers'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_packagehelper_sequence_storage_retrieve():
    '''Tests PackageHelper, type Sequence storage & retrieve
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)

    for _ in range(2):
        phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
        phelp_dc.update({
            'Id': str(uuid4()),
            'Type': PackageHelperType.Sequence.value,
            'Name': 'Sequence #' + str(random.randint(1e5, 1e6)),
            'PosX': random.randint(1e5, 1e6),
            'PosY': random.randint(1e5, 1e6),
            'SizeX': random.randint(1e5, 1e6),
            'SizeY': random.randint(1e5, 1e6),
            'Meta': {
                'Sequence': '',
                'ContainedNodes': [],
            },
        })
        package_dc['Helpers'].append(phelp_dc)

    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    phelp_objs = PackageHelper.objects.filter(package=package_obj)
    assert phelp_objs.count() == len(package_dc['Helpers'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_packagehelper_stickynote_storage_retrieve():
    '''Tests PackageHelper, type StickyNote storage & retrieve
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)

    for _ in range(2):
        phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
        phelp_dc.update({
            'Id': str(uuid4()),
            'Type': PackageHelperType.StickyNote.value,
            'Name': 'Sequence #' + str(random.randint(1e5, 1e6)),
            'PosX': random.randint(1e5, 1e6),
            'PosY': random.randint(1e5, 1e6),
            'SizeX': random.randint(1e5, 1e6),
            'SizeY': random.randint(1e5, 1e6),
            'Meta': {
                'Text':
                    'A well defined note... With \u1f4a9 #' +
                    str(random.randint(1e5, 1e6)),
            },
        })
        package_dc['Helpers'].append(phelp_dc)

    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    phelp_objs = PackageHelper.objects.filter(package=package_obj)
    assert phelp_objs.count() == len(package_dc['Helpers'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_packagehelper_nodes_storage_retrieve():
    '''Tests PackageHelper / PackageHelperNode storage & retrieve
    '''
    node_nid_1 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
    node_nid_2 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
    package_dc = copy.deepcopy(PACKAGE_DEF)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Union.value,
        'Name': 'Union #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Color': '(R=%0.4f,G=%0.4f,B=%0.4f,A=%0.4f)' % (
                random.random(),
                random.random(),
                random.random(),
                random.random(),
            ),
            'ContainedNodes': [node_nid_1, node_nid_2],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Union.value,
        'Name': 'Union #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Color': '(R=%0.4f,G=%0.4f,B=%0.4f,A=%0.4f)' % (
                random.random(),
                random.random(),
                random.random(),
                random.random(),
            ),
            'ContainedNodes': [node_nid_2, node_nid_1],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Sequence.value,
        'Name': 'Sequence #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Sequence': 'Seq #' + str(random.randint(1e5, 1e6)),
            'ContainedNodes': [node_nid_2, node_nid_1],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    for node_nid in [node_nid_2, node_nid_1]:
        node_def = copy.deepcopy(NODE_DEF)
        node_def['Id'] = node_nid
        node_def['Name'] = 'End #' + str(random.randint(1e5, 1e6))
        node_def['Type'] = NodeType.End.value
        package_dc['Nodes'].append(node_def)

    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    phelp_objs = PackageHelper.objects.filter(package=package_obj)
    assert phelp_objs.count() == len(package_dc['Helpers'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_package_helpers_storage_retrieve():
    '''Tests Package helpers storage & retrieve
    '''
    node_nid_1 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
    node_nid_2 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
    package_dc = copy.deepcopy(PACKAGE_DEF)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Union.value,
        'Name': 'Union #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Color': '(R=%0.4f,G=%0.4f,B=%0.4f,A=%0.4f)' % (
                random.random(),
                random.random(),
                random.random(),
                random.random(),
            ),
            'ContainedNodes': [node_nid_1, node_nid_2],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Comment.value,
        'Name': 'Comment #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {},
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Sequence.value,
        'Name': 'Sequence #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Sequence': 'Seq #' + str(random.randint(1e5, 1e6)),
            'ContainedNodes': [node_nid_2, node_nid_1],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Union.value,
        'Name': 'Union #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Color': '(R=%0.4f,G=%0.4f,B=%0.4f,A=%0.4f)' % (
                random.random(),
                random.random(),
                random.random(),
                random.random(),
            ),
            'ContainedNodes': [node_nid_2, node_nid_1],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Comment.value,
        'Name': 'Comment #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {},
    })
    package_dc['Helpers'].append(phelp_dc)

    phelp_dc = copy.deepcopy(PACKAGE_HELPER_DEF)
    phelp_dc.update({
        'Id': str(uuid4()),
        'Type': PackageHelperType.Sequence.value,
        'Name': 'Sequence #' + str(random.randint(1e5, 1e6)),
        'PosX': random.randint(1e5, 1e6),
        'PosY': random.randint(1e5, 1e6),
        'SizeX': random.randint(1e5, 1e6),
        'SizeY': random.randint(1e5, 1e6),
        'Meta': {
            'Sequence': '',
            'ContainedNodes': [],
        },
    })
    package_dc['Helpers'].append(phelp_dc)

    for node_nid in [node_nid_2, node_nid_1]:
        node_def = copy.deepcopy(NODE_DEF)
        node_def['Id'] = node_nid
        node_def['Name'] = 'End #' + str(random.randint(1e5, 1e6))
        node_def['Type'] = NodeType.End.value
        package_dc['Nodes'].append(node_def)

    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    phelp_objs = PackageHelper.objects.filter(
        package=package_obj, type=PackageHelperType.Comment.value).order_by(
            'index')
    assert phelp_objs.count() == len([
        entry for entry in package_dc['Helpers']
        if entry['Type'] == PackageHelperType.Comment.value])

    phelp_objs = PackageHelper.objects.filter(
        package=package_obj, type=PackageHelperType.Sequence.value).order_by(
            'index')
    assert phelp_objs.count() == len([
        entry for entry in package_dc['Helpers']
        if entry['Type'] == PackageHelperType.Sequence.value])

    phelp_objs = PackageHelper.objects.filter(
        package=package_obj, type=PackageHelperType.Union.value).order_by(
            'index')
    assert phelp_objs.count() == len([
        entry for entry in package_dc['Helpers']
        if entry['Type'] == PackageHelperType.Union.value])

    phelp_objs = PackageHelper.objects.filter(
        package=package_obj, type=PackageHelperType.Sequence.value).order_by(
            'index')
    assert phelp_objs.count() == len([
        entry for entry in package_dc['Helpers']
        if entry['Type'] == PackageHelperType.Sequence.value])

    assert Node.objects.filter(package=package_obj).count() == len(
        package_dc['Nodes'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_node_condition_sequence_storage_retrieve():
    '''Tests Node Type=Condition Mode=Iterate storage & retrieve
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)
    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = 'NStoryBlock_Condition_' + str(random.randint(1e5, 1e6))
    node_def['Name'] = 'Condition #' + str(random.randint(1e5, 1e6))
    node_def['Meta'].update({
        'Mode': 'Iterate',
        'Cases': [{
            'Name': 'Case #' + str(idx + 1),
        } for idx in range(random.randint(1e1, 1e2))],
    })
    node_def['Type'] = NodeType.Condition.value
    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    node_objs = Node.objects.filter(package=package_obj)
    assert node_objs.count() == len(package_dc['Nodes'])

    assert package_dc == dict(package_obj)


@pytest.mark.django_db
def test_nodes_doubled_links():
    '''Tests Node - doubled links
    '''
    package_dc = copy.deepcopy(PACKAGE_DEF)

    node_nid_1 = 'NStoryBlock_Start_' + str(random.randint(1e5, 1e6))
    node_nid_2 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = node_nid_1
    node_def['Name'] = 'Start #' + str(random.randint(1e5, 1e6))
    node_def['Type'] = NodeType.Start.value
    node_def['OutLinks'].extend([
        {
            'LinkedNodeId': node_nid_2,
            'MyPinIndex': 0,
            'OtherPinIndex': 0,
        },
        {
            'LinkedNodeId': node_nid_2,
            'MyPinIndex': 0,
            'OtherPinIndex': 1,
        },
    ])
    package_dc['Nodes'].append(node_def)

    node_def = copy.deepcopy(NODE_DEF)
    node_def['Id'] = node_nid_2
    node_def['Name'] = 'End #' + str(random.randint(1e5, 1e6))
    node_def['Type'] = NodeType.End.value
    node_def['OutLinks'].extend([
        {
            'LinkedNodeId': node_nid_1,
            'MyPinIndex': 0,
            'OtherPinIndex': 0,
        },
        {
            'LinkedNodeId': node_nid_1,
            'MyPinIndex': 1,
            'OtherPinIndex': 0,
        },
    ])
    package_dc['Nodes'].append(node_def)
    package_dc['ModTime'] = str(int(
        (timezone.now() + timedelta(days=1)).timestamp()))

    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    author = Member.objects.create(email=email)
    package_obj, _, op_msg = parse_package_upload(SimpleUploadedFile(
        TEST_DATA_FNAME, bytes(json.dumps(package_dc), encoding='latin-1'),
        content_type='application/json'), author)

    assert str(op_msg) == 'JSON accepted'
    assert package_obj is not None
    assert package_obj.id
    assert Package.objects.get(pk=package_obj.id)
    assert PackageAsset.objects.filter(package=package_obj).count() == len(
        package_dc['Assets'])

    node_objs = Node.objects.filter(package=package_obj)
    assert node_objs.count() == len(package_dc['Nodes'])

    assert package_dc == dict(package_obj)


def _add_recursive_entitytype_child(children_lst, names, level, max_level):
    '''Adds recursive entity type child
    '''
    if level > max_level:
        return

    name = ''
    while not name or name in names:
        name = 'NEntityTypeSomething' + str(random.randint(1e5, 1e6))

    names.add(name)
    sub_struct = {
        'Name': name,
        'Children': [],
    }
    _add_recursive_entitytype_child(
        sub_struct['Children'], names, level + 1, max_level)
    children_lst.append(sub_struct)


def test_fetch_entity_types_too_recursive():
    '''Tests fetch_entity_types - too recursive structure
    '''
    entity_types_lst = []
    names = set()
    _add_recursive_entitytype_child(entity_types_lst, names, 0, 64)

    try:
        fetch_entity_types(set(), entity_types_lst)
        assert False
    except RecursionError:
        pass


def test_fetch_entity_types_enough_recursive():
    '''Tests fetch_entity_types - OK recursive structure
    '''
    entity_types_lst = []
    names = set()
    _add_recursive_entitytype_child(entity_types_lst, names, 0, 63)

    fetched_names = set()
    fetch_entity_types(fetched_names, entity_types_lst)

    assert fetched_names == names


def test_entity_types_mismatch_too_recursive():
    '''Tests entity_types_mismatch method - too recursive
    '''
    entity_types_lst = []
    _add_recursive_entitytype_child(entity_types_lst, set(), 0, 64)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    package_dc['EntityTypes'].extend(entity_types_lst)

    errors, op_msg = entity_types_mismatch(package_dc)
    assert errors
    assert 'recursion exceeded' in op_msg


def test_entity_types_mismatch_unknown_assets_types():
    '''Tests entity_types_mismatch method - unknown assets types
    '''
    entity_types_lst = []
    names = set()
    _add_recursive_entitytype_child(entity_types_lst, names, 0, 63)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    package_dc['EntityTypes'].extend(entity_types_lst)

    entity_type_name = ''
    while not entity_type_name or entity_type_name in names:
        entity_type_name = 'NEntityTypeSomething' + str(
            random.randint(1e5, 1e6))

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_ENTITY
    passet_def['Meta'].update({'Types': [entity_type_name]})
    package_dc['Assets'].append(passet_def)

    errors, op_msg = entity_types_mismatch(package_dc)
    assert errors
    assert 'assets types' in op_msg


def test_entity_types_mismatch_unknown_actions_types():
    '''Tests entity_types_mismatch method - unknown actions types
    '''
    entity_types_lst = []
    names = set()
    _add_recursive_entitytype_child(entity_types_lst, names, 0, 63)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    package_dc['EntityTypes'].extend(entity_types_lst)

    entity_type_name = ''
    while not entity_type_name or entity_type_name in names:
        entity_type_name = 'NEntityTypeSomething' + str(
            random.randint(1e5, 1e6))

    package_dc['Actions'].append({
        'Name': 'Action ' + str(random.randint(1e5, 1e6)),
        'Params': [
            {
                'Label': 'Label ' + str(random.randint(1e5, 1e6)),
                'AssetClass': PackageAsset.TYPE_ENTITY,
                'EntityTypes': [
                    entity_type_name,
                ],
                'Mandatory': False,
            },
        ],
    })

    errors, op_msg = entity_types_mismatch(package_dc)
    assert errors
    assert 'actions types' in op_msg


def test_entity_types_mismatch_ok_entity_types():
    '''Tests entity_types_mismatch method - OK entity types
    '''
    entity_types_lst = []
    names = set()
    _add_recursive_entitytype_child(entity_types_lst, names, 0, 63)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    package_dc['EntityTypes'].extend(entity_types_lst)

    passet_def = copy.deepcopy(PACKAGE_ASSET_DEF)
    passet_def['Class'] = PackageAsset.TYPE_ENTITY
    passet_def['Meta'].update({
        'Types': random.sample(names, random.randint(1, 3)),
    })
    package_dc['Assets'].append(passet_def)

    package_dc['Actions'].append({
        'Name': 'Action ' + str(random.randint(1e5, 1e6)),
        'Params': [
            {
                'Label': 'Label ' + str(random.randint(1e5, 1e6)),
                'AssetClass': PackageAsset.TYPE_ENTITY,
                'EntityTypes': random.sample(names, random.randint(1, 3)),
                'Mandatory': False,
            },
        ],
    })

    errors, op_msg = entity_types_mismatch(package_dc)
    assert not errors
    assert 'OK' in op_msg


def test_transform_validate_package_entity_types_mismatch():
    '''Tests transform_validate_package method - entity types mismatch
    '''
    entity_types_lst = []
    names = set()
    _add_recursive_entitytype_child(entity_types_lst, names, 0, 63)

    package_dc = copy.deepcopy(PACKAGE_DEF)
    package_dc['EntityTypes'].extend(entity_types_lst)

    entity_type_name = ''
    while not entity_type_name or entity_type_name in names:
        entity_type_name = 'NEntityTypeSomething' + str(
            random.randint(1e5, 1e6))

    package_dc['Actions'].append({
        'Name': 'Action ' + str(random.randint(1e5, 1e6)),
        'Params': [
            {
                'Label': 'Label ' + str(random.randint(1e5, 1e6)),
                'AssetClass': PackageAsset.TYPE_ENTITY,
                'EntityTypes': [
                    entity_type_name,
                ],
                'Mandatory': False,
            },
        ],
    })

    package_dc, error = transform_validate_package(package_dc)

    assert error
    assert 'Invalid package' in error
    assert 'actions types' in error

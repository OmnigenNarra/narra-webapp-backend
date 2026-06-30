# -*- coding: utf-8 -*-

'''Packages utils module
'''

import json
import logging
from collections import defaultdict
from ctypes import (
    c_char_p,
    CDLL,
    c_int,
    RTLD_GLOBAL,
)
from ctypes.util import find_library
from datetime import datetime
from tempfile import NamedTemporaryFile

from jsonschema import (
    FormatError,
    RefResolutionError,
    SchemaError,
    ValidationError,
    validate as jsonschema_validate,
)
import pytz
from semver import (
    parse_version_info as pvi,
)

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _u

from .migrators import VersionMigrator
from ..models import (
    Node,
    NodeAsset,
    NodeLink,
    Package,
    PackageAction,
    PackageAsset,
    PackageAssetType,
    PackageEntityType,
    PackageHelper,
    PackageHelperNode,
    PackageHelperType,
)


LOG = logging.getLogger(__name__)

USE_NARRA_VALIDATORS = False
try:
    _LIBFND = find_library('narra_validators')
    assert _LIBFND, 'no narra_validators library'

    LIBNARRA_VALIDATORS = CDLL(_LIBFND, mode=RTLD_GLOBAL)
    assert LIBNARRA_VALIDATORS.validate_graph, \
        'no validate_graph method in library'
    assert LIBNARRA_VALIDATORS.validate_json, \
        'no validate_json method in library'

    LIBNARRA_VALIDATORS.validate_json.restype = c_int
    LIBNARRA_VALIDATORS.validate_graph.restype = c_char_p

    USE_NARRA_VALIDATORS = True
except (OSError, AttributeError, AssertionError) as exc:
    LOG.warning(repr(exc))


def _store_package_actions(package, actions):
    '''Stores package actions
    '''
    pacts = []
    for idx, action_entry in enumerate(actions):
        pact = PackageAction()
        pact.package = package
        pact.index = idx
        pact.name = action_entry['Name']
        pact.params = action_entry['Params']
        pacts.append(pact)

    if pacts:
        PackageAction.objects.bulk_create(pacts)
        for pact in pacts:
            models.signals.post_save.send(
                PackageAction, instance=pact, created=True)


def _store_package_entity_types(
        package_obj, entity_types_struct_lst, entity_types_flatmap,
        entity_type_parent=None, index=0):
    '''Stores package entity types
    '''
    for entity_type_data in entity_types_struct_lst:
        entity_type_obj = PackageEntityType()
        entity_type_obj.package = package_obj
        entity_type_obj.parent = entity_type_parent
        entity_type_obj.index = index
        entity_type_obj.name = entity_type_data['Name']
        entity_type_obj.save()
        entity_types_flatmap[entity_type_obj.name] = entity_type_obj
        index += 1
        index = _store_package_entity_types(
            package_obj, entity_type_data['Children'], entity_types_flatmap,
            entity_type_parent=entity_type_obj, index=index)

    if entity_type_parent is None:
        models.signals.post_save.send(
            PackageEntityType,
            instance=PackageEntityType(package=package_obj), created=True)

    return index


def _store_package_assets(package, assets, entity_types_flatmap):
    '''Stores package assets
    '''
    package_assets_ids = {}
    passet_types = []
    for aidx, asset_entry in enumerate(assets):
        asset_class = asset_entry['Class']
        passet = PackageAsset()
        passet.package = package
        passet.type = asset_class
        passet.name = asset_entry['Uri']
        passet.index = aidx
        passet.is_enabled = asset_entry['Meta'].get('IsEnabled', False)
        passet.save()

        package_assets_ids[asset_entry['Uri']] = passet.id

        if asset_class == PackageAsset.TYPE_ENTITY:
            for tidx, ptype in enumerate(asset_entry['Meta'].get('Types', [])):
                passet_type = PackageAssetType()
                passet_type.package = package
                passet_type.package_asset = passet
                passet_type.package_entity_type = entity_types_flatmap.get(
                    ptype)
                passet_type.index = tidx
                passet_types.append(passet_type)

    if passet_types:
        PackageAssetType.objects.bulk_create(passet_types)
        for passet_type in passet_types:
            models.signals.post_save.send(
                PackageAsset, instance=passet_type.package_asset, created=True)

    return package_assets_ids


def _store_package_helpers(package, helpers, nodes_dc):
    '''Stores package helpers (comments, sequences, ...)
    '''
    phelps = []
    phelp_nodes = []
    idx = 0
    for _idx, helper_entry in enumerate(helpers):
        phelp = PackageHelper()
        phelp.index = _idx
        phelp.hid = helper_entry['Id']
        phelp.name = helper_entry['Name']
        phelp.package = package
        phelp.pos_x = helper_entry['PosX']
        phelp.pos_y = helper_entry['PosY']
        phelp.size_x = helper_entry['SizeX']
        phelp.size_y = helper_entry['SizeY']
        phelp.type = helper_entry['Type']
        phelp.meta = helper_entry['Meta']

        if phelp.type in [
                PackageHelperType.Sequence.value,
                PackageHelperType.Union.value]:
            phelp.save()
            for node_nid in phelp.meta.pop('ContainedNodes'):
                phelp_node = PackageHelperNode()
                phelp_node.package_helper = phelp
                phelp_node.node = nodes_dc[node_nid]
                phelp_node.index = idx
                phelp_nodes.append(phelp_node)
                idx += 1
        else:
            phelps.append(phelp)

    if phelp_nodes:
        PackageHelperNode.objects.bulk_create(phelp_nodes)
        for phelp_node in phelp_nodes:
            models.signals.post_save.send(
                PackageHelperNode, instance=phelp_node,
                created=True)

    if phelps:
        PackageHelper.objects.bulk_create(phelps)
        for phelp in phelps:
            models.signals.post_save.send(
                PackageHelper, instance=phelp, created=True)


def _store_node_assets(node, package_assets_ids, node_assets):
    '''Stores node assets
    '''
    nassets = []
    for class_index, asset_entry in enumerate(node_assets):
        for name_index, asset_uri in enumerate(asset_entry['Uris']):
            nasset = NodeAsset()
            nasset.node = node
            nasset.package_asset_id = package_assets_ids[asset_uri] \
                if asset_uri in package_assets_ids else None
            nasset.class_index = class_index
            nasset.name_index = name_index
            nassets.append(nasset)

    if nassets:
        NodeAsset.objects.bulk_create(nassets)
        for nasset in nassets:
            models.signals.post_save.send(
                NodeAsset, instance=nasset, created=True)


def _store_node_links(node, node_data):
    '''Stores node links
    '''
    links = []
    idx = 0
    for links_field, link_type in [
            ('InLinks', NodeLink.TYPE_INPUT),
            ('OutLinks', NodeLink.TYPE_OUTPUT)]:
        _links = node_data.get(links_field) or []
        for _link in _links:
            link = NodeLink()
            link.node = node
            link.type = link_type
            link.linked_node = Node.objects.get(
                package=node.package, nid=_link['LinkedNodeId'])
            link.index = idx
            link.other_pin_index = _link['OtherPinIndex']
            link.my_pin_index = _link['MyPinIndex']
            links.append(link)
            idx += 1

    if links:
        NodeLink.objects.bulk_create(links)
        for link in links:
            models.signals.post_save.send(
                NodeLink, instance=link, created=True)


def _store_package_nodes(package, package_assets_ids, nodes, container=None):
    '''Stores package nodes
    '''
    nodes_dc = {}
    for idx, node_data in enumerate(nodes):
        node = Node()
        node.package = package
        node.container = container

        node.description = node_data['Description'] or ''
        node.nid = node_data['Id']
        node.index = idx

        node.meta = node_data['Meta'] or {}
        node.name = node_data['Name'] or ''
        node.pos_x = node_data['PosX']
        node.pos_y = node_data['PosY']
        node.tags = node_data['Tags']
        node.trigger_tags = node_data['TriggerTags']
        node.type = node_data['Type']
        node.weight = node_data['Weight']
        node.input_pins = node_data['InPins']
        node.output_pins = node_data['OutPins']
        node.save()

        nodes_dc[node.nid] = node
        _store_node_assets(node, package_assets_ids, node_data['Assets'])

    for node_data in nodes:
        node = nodes_dc[node_data['Id']]
        _store_node_links(node, node_data)

    for node_data in nodes:
        node = nodes_dc[node_data['Id']]
        if node_data['Components']:
            _nodes_dc = _store_package_nodes(
                package, package_assets_ids, node_data['Components'],
                container=node)
            nodes_dc.update(_nodes_dc)

    models.signals.post_save.send(Package, instance=package, created=True)

    return nodes_dc


def store_package(package_obj, package_dc):
    '''Stores Narra exported data
    '''
    package_obj.remove_actions()
    package_obj.remove_helpers()
    package_obj.remove_nodes()
    package_obj.remove_assets()
    package_obj.remove_entity_types()

    entity_types_flatmap = {}
    _store_package_entity_types(
        package_obj, package_dc.get('EntityTypes', []), entity_types_flatmap)
    package_assets_ids = _store_package_assets(
        package_obj, package_dc['Assets'], entity_types_flatmap)
    nodes_dc = _store_package_nodes(
        package_obj, package_assets_ids, package_dc['Nodes'])
    _store_package_actions(
        package_obj, package_dc.get('Actions', []))
    _store_package_helpers(
        package_obj, package_dc.get('Helpers', []), nodes_dc)


def nodes_ids_mismatch(package_dc):
    '''Tests if nodes' IDs mismatch
    '''
    nodes_nids = defaultdict(int)
    for node_data in package_dc['Nodes']:
        nodes_nids[node_data['Id']] += 1
        for comp in node_data['Components']:
            nodes_nids[comp['Id']] += 1

    dup_nids = [nid for nid, cnt in nodes_nids.items() if cnt > 1]
    if dup_nids:
        return (True, _u('Duplicated IDs: %s') % ', '.join(dup_nids))

    missing_nids = set()
    links = defaultdict(int)
    for node_data in package_dc['Nodes']:
        for link_dc in node_data['InLinks']:
            nid = link_dc['LinkedNodeId']
            if nid not in nodes_nids:
                missing_nids.add(nid)
            links[(nid, node_data['Id'])] += 1
        for link_dc in node_data['OutLinks']:
            nid = link_dc['LinkedNodeId']
            if nid not in nodes_nids:
                missing_nids.add(nid)
            links[(node_data['Id'], nid)] += 1

    if missing_nids:
        return (True, _u('Missing IDs: %s') % ', '.join(missing_nids))
    mm_links = [
        src + ' - ' + dst for (src, dst), cnt in links.items() if cnt % 2 != 0]
    if mm_links:
        return (True, _u('Mismatched links: %s') % ', '.join(mm_links))

    return (False, _u('Nodes\' IDs OK'))


def is_package_invalid(package_dc):
    '''Tests if package is invalid
    '''
    exc_msg = ''
    try:
        posted_json_version, is_version_supported, _ = \
            versions_check(package_dc)
        if not is_version_supported:
            return (True, _u(
                'Version not supported: ' + str(posted_json_version)))

        if settings.USE_JSONSCHEMA:
            if USE_NARRA_VALIDATORS:
                json_valid_res = LIBNARRA_VALIDATORS.validate_json(
                    get_narra_validators_buf(package_dc),
                    get_narra_validators_buf(
                        settings.PACKAGE_SCHEMAS[posted_json_version]))
                if json_valid_res != 1:
                    raise ValidationError('generic error')
            else:
                jsonschema_validate(
                    instance=package_dc,
                    schema=settings.PACKAGE_SCHEMAS[posted_json_version])

        return assets_mismatch(package_dc)
    except (
            FormatError, RefResolutionError,
            SchemaError, ValidationError) as exc:
        LOG.warning('Package validaton failed: %s', repr(exc))
        exc_msg = exc.message

    return (True, exc_msg)


def fetch_entity_types(entity_types, entypes_children, level=0):
    '''Fetches entity types
    '''
    if level > 64:
        raise RecursionError(level)

    for child in entypes_children:
        entity_types.add(child['Name'])
        fetch_entity_types(
            entity_types, child['Children'], level=level + 1)


def entity_types_mismatch(package_dc):
    '''Tests if entity types mismatch
    '''
    pkg_entity_types = set()
    try:
        fetch_entity_types(pkg_entity_types, package_dc['EntityTypes'])
    except RecursionError as exc:
        return (
            True, _u('Entity types recursion exceeded: %s') % exc.args[0])

    assets_entity_types = set()
    for asset_entry in package_dc['Assets']:
        if asset_entry['Class'] == PackageAsset.TYPE_ENTITY:
            assets_entity_types.update(
                asset_entry['Meta'].get('Types', []))

    rest_entity_types = assets_entity_types.difference(pkg_entity_types)
    if rest_entity_types:
        return (True, _u('Unknown assets types: %s') % repr(
            rest_entity_types))

    actions_entity_types = set()
    for action_entry in package_dc['Actions']:
        for param_entry in action_entry['Params']:
            if param_entry['AssetClass'] == PackageAsset.TYPE_ENTITY:
                actions_entity_types.update(param_entry['EntityTypes'])

    rest_entity_types = actions_entity_types.difference(pkg_entity_types)
    if rest_entity_types:
        return (True, _u('Unknown actions types: %s') % repr(
            rest_entity_types))

    return (False, _u('Entity types OK'))


def assets_mismatch(package_dc):
    '''Tests if assets mismatch
    '''
    assets_dc = {}
    for asset_entry in package_dc['Assets']:
        asset_cls = asset_entry['Class']
        if asset_cls not in assets_dc:
            assets_dc[asset_cls] = set()
        assets_dc[asset_cls].add(asset_entry['Uri'])

    for node_data in package_dc['Nodes']:
        for asset_entry in node_data['Assets']:
            asset_cls = asset_entry['Class']
            if asset_cls not in assets_dc:
                return (True, _u('Missing class: %s') % repr(asset_cls))
            rest_uris = set(
                uri for uri in asset_entry['Uris'] if uri).difference(
                    assets_dc[asset_cls])
            if rest_uris:
                return (True, _u('Extra URIs: %s') % repr(rest_uris))

    return (False, _u('Assets OK'))


def versions_check(package_dc):
    '''Checks JSON versions
    '''
    if not isinstance(package_dc, dict):
        return ('', False, False)

    try:
        posted_json_version = pvi(package_dc['JSONVersion'])
    except (KeyError, ValueError):
        return ('', False, False)

    current_json_version = pvi(settings.PACKAGE_JSON_VER)
    is_version_supported = pvi(settings.PACKAGE_JSON_VER_MIN) <= \
        posted_json_version <= current_json_version and \
        posted_json_version.major == current_json_version.major and \
        str(posted_json_version) in settings.PACKAGE_SCHEMAS
    migration_required = posted_json_version < current_json_version \
        if is_version_supported else False

    return (str(posted_json_version), is_version_supported, migration_required)


def transform_validate_package(package_dc):
    '''Transforms / validates (or validates / transforms) the package
    '''
    is_invalid, op_msg = is_package_invalid(package_dc)
    if is_invalid:
        return (None, _u('Invalid package - %s') % op_msg)

    errors, op_msg = nodes_ids_mismatch(package_dc)
    if errors:
        return (None, _u('Invalid package - %s') % op_msg)

    errors, op_msg = entity_types_mismatch(package_dc)
    if errors:
        return (None, _u('Invalid package - %s') % op_msg)

    # NOTE: move transformation below any validation
    # if there are no structural changes to validate
    package_dc = try_package_migrate(package_dc)

    return (package_dc, '')


def update_package_obj(package_obj, filename, author, package_dc):
    '''Updates package object
    '''
    package_obj.filename = filename
    package_obj.author = author
    package_obj.story_name = package_dc['StoryName']
    package_obj.json_ver = package_dc['JSONVersion']
    package_obj.story_ver = package_dc['StoryVersion']
    package_obj.uasset_ver = package_dc['UAssetVersion']
    package_obj.ctime = package_obj.ctime or timezone.now()
    package_obj.mtime = datetime.utcfromtimestamp(
        int(package_dc['ModTime'])).replace(tzinfo=pytz.utc)


def process_and_store_package(package_dc, filename, author):
    '''Processes package
    '''
    package_dc, error = transform_validate_package(package_dc)
    if error:
        return (None, None, error)

    package_obj = Package()
    update_package_obj(package_obj, filename, author, package_dc)
    package_obj.locked_by = author
    package_obj.save()
    store_package(package_obj, package_dc)

    return (package_obj, package_dc, _u('JSON accepted'))


def parse_package_upload(ufile, author):
    '''Parses package upload
    '''
    with NamedTemporaryFile(
            suffix='.json', prefix='package', delete=True) as tmpfile:
        for chunk in ufile.chunks():
            tmpfile.write(chunk)
        tmpfile.seek(0)

        try:
            package_dc = json.loads(tmpfile.read())
        except (
                AttributeError, LookupError, TypeError, ValueError,
                json.JSONDecodeError) as exc:
            LOG.exception(exc)
            return (None, None, _u('Bad JSON: %s - %s') % (
                exc.__class__.__name__, str(exc)))

        return process_and_store_package(package_dc, ufile.name, author)


def try_package_migrate(package_dc, to_version=None):
    '''Tries to migrate package
    '''
    posted_json_version, is_version_supported, migration_required = \
        versions_check(package_dc)

    if is_version_supported and migration_required:
        return VersionMigrator(
            package_dc, posted_json_version,
            to_version or settings.PACKAGE_JSON_VER,
            settings.PACKAGE_SCHEMAS.keys()).migrate()

    return package_dc


def _gen_fake_validation_output():
    '''Generates fake validation output
    '''
    return {
        'Global': [
            {
                'Messages': [
                    str(_u('WARNING! Validator turned off!')),
                ],
                'Verdict': 3,  # =error
            },
        ],
        'Links': [],
        'Nodes': [],
        'Variants': [],
    }


def get_narra_validators_buf(obj):
    '''Dumps object instance to libnarra_validators-compatible byte buffer
    '''
    return bytes(
        json.dumps(
            obj, ensure_ascii=False, indent=None, separators=(',', ':')),
        encoding='utf-8')


def perform_story_validation(package_dc):
    '''Performs story validation
    '''
    if USE_NARRA_VALIDATORS:
        output_dc = json.loads(LIBNARRA_VALIDATORS.validate_graph(
            get_narra_validators_buf(package_dc)))
    else:
        output_dc = _gen_fake_validation_output()

    exc_msg = ''
    try:
        if settings.USE_JSONSCHEMA:
            if USE_NARRA_VALIDATORS:
                json_valid_res = LIBNARRA_VALIDATORS.validate_json(
                    get_narra_validators_buf(output_dc),
                    get_narra_validators_buf(
                        settings.PACKAGE_VALIDATION_SCHEMA))
                if json_valid_res != 1:
                    raise ValidationError('generic error')
            else:
                jsonschema_validate(
                    instance=output_dc,
                    schema=settings.PACKAGE_VALIDATION_SCHEMA)

        return (False, None, output_dc)
    except (
            FormatError, RefResolutionError,
            SchemaError, ValidationError) as exc:
        LOG.warning('Validaton output error: %s', repr(exc))
        exc_msg = exc.message

    return (True, exc_msg, None)

# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import random
from collections.abc import Iterable
from uuid import uuid4

import pytest

from django.db import models

from narra_backend.api.models import (
    Node,
    NodeAsset,
    NodeLink,
    NodeType,
    Package,
    PackageAction,
    PackageAsset,
    PackageAssetType,
    PackageEntityType,
    PackageHelper,
    PackageHelperNode,
    PackageHelperType,
)
from narra_backend.units.models import (
    Member,
    Team,
)

from .commons import TEST_DATA_FNAME, PACKAGE_HELPER_DEF


def test_package_class_repr():
    '''Tests Package model - repr
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)

    assert str(package_obj) == TEST_DATA_FNAME


@pytest.mark.django_db
def test_package_class_iter():
    '''Tests Package model - iterator
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    try:
        assert isinstance(iter(package_obj), Iterable)
    except TypeError:
        assert False

    assert dict(package_obj)


@pytest.mark.django_db
def test_package_class_to_json():
    '''Tests Package model - to_json
    '''
    package_obj = Package(filename=TEST_DATA_FNAME)
    package_json = package_obj.to_json()

    assert 'Assets' in package_json
    assert 'Nodes' in package_json
    assert 'JSONVersion' in package_json
    assert 'UAssetVersion' in package_json
    assert 'StoryVersion' in package_json


@pytest.mark.django_db
def test_package_author_nullify():
    '''Tests Package model - author nullify
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, author=member)

    assert package_obj.author is not None

    member.delete()

    models.signals.post_save.send(Package, instance=package_obj)

    _package_obj = Package.objects.get(pk=package_obj.id)

    assert _package_obj.author is None


@pytest.mark.django_db
def test_package_author_cannot_modify():
    '''Tests Package model - author cannot modify test
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1)
    member2 = Member.objects.create(email=email2)

    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, author=member1)

    assert not package_obj.can_modify(member2)


@pytest.mark.django_db
def test_package_author_can_modify():
    '''Tests Package model - author can modify test
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, author=member)

    assert package_obj.can_modify(member)


@pytest.mark.django_db
def test_package_team_member_cannot_modify():
    '''Tests Package model - team member cannot modify test
    '''
    email1 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    email2 = email1
    while email2 == email1:
        email2 = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member1 = Member.objects.create(email=email1)
    member2 = Member.objects.create(email=email2)

    team1 = Team.objects.create(name='team_' + str(random.randint(1e5, 1e6)))
    team2 = Team.objects.create(name='team_' + str(random.randint(1e5, 1e6)))
    team1.add_member(member1)
    team2.add_member(member2)

    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, author=member1, team=team1)

    assert not package_obj.can_modify(member2)


@pytest.mark.django_db
def test_package_team_member_can_modify():
    '''Tests Package model - team member can modify test
    '''
    email = 'testsuperuser%s@example.com' % random.randint(1e5, 1e6)
    member = Member.objects.create(email=email)
    team = Team.objects.create(name='team_' + str(random.randint(1e5, 1e6)))
    team.add_member(member)

    package_obj = Package.objects.create(
        filename=TEST_DATA_FNAME, team=team)

    assert package_obj.author is None
    assert package_obj.team is not None
    assert package_obj.can_modify(member)


@pytest.mark.django_db
def test_package_class_packageasset():
    '''Tests Package model - PackageAsset serialization bound
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    passet_name = 'Fact_' + str(random.randint(1e5, 1e6))
    PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT, name=passet_name,
        index=0)
    package_dc = dict(package_obj)

    assert len(package_dc['Assets']) == 1
    assert package_dc['Assets'][0]['Class'] == PackageAsset.TYPE_FACT
    assert package_dc['Assets'][0]['Uri'] == passet_name
    assert package_dc['Assets'][0]['Meta'] == {}


@pytest.mark.django_db
def test_packagehelper_iter():
    '''Tests PackageHelper model - serialization
    '''
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

    phelp = PackageHelper(
        type=PackageHelperType.Comment.value, hid=phelp_dc['Id'],
        name=phelp_dc['Name'], meta=phelp_dc['Meta'],
        pos_x=phelp_dc['PosX'], pos_y=phelp_dc['PosY'],
        size_x=phelp_dc['SizeX'], size_y=phelp_dc['SizeY'])

    assert dict(phelp) == phelp_dc


@pytest.mark.django_db
def test_packagehelper_union_node_iter():
    '''Tests PackageHelper model, Union type - serialization
    '''
    node_nid_1 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
    node_nid_2 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
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

    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    node_obj_1 = Node.objects.create(
        package=package_obj, nid=node_nid_1, type=NodeType.Fact.value, name='',
        pos_x=0, pos_y=0, index=0, meta={})
    node_obj_2 = Node.objects.create(
        package=package_obj, nid=node_nid_2, type=NodeType.Fact.value, name='',
        pos_x=0, pos_y=0, index=0, meta={})
    phelp = PackageHelper(
        package=package_obj, hid=phelp_dc['Id'], name=phelp_dc['Name'],
        type=PackageHelperType.Union.value, index=random.randint(1e3, 1e4),
        pos_x=phelp_dc['PosX'], pos_y=phelp_dc['PosY'],
        size_x=phelp_dc['SizeX'], size_y=phelp_dc['SizeY'],
        meta={'Color': phelp_dc['Meta']['Color']})
    phelp.save()

    PackageHelperNode.objects.bulk_create([
        PackageHelperNode(
            package_helper=phelp, node=node_obj_2, index=1),
        PackageHelperNode(
            package_helper=phelp, node=node_obj_1, index=0),
    ])

    models.signals.post_save.send(
        PackageHelper, instance=phelp, created=True)

    assert dict(phelp) == phelp_dc


@pytest.mark.django_db
def test_packagehelper_sequence_node_iter():
    '''Tests PackageHelper model, Sequence type - serialization
    '''
    node_nid_1 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
    node_nid_2 = 'NStoryBlock_End_' + str(random.randint(1e5, 1e6))
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
            'Sequence': 'Tiz seq #' + str(random.randint(1e5, 1e6)),
            'ContainedNodes': [node_nid_1, node_nid_2],
        },
    })

    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    node_obj_1 = Node.objects.create(
        package=package_obj, nid=node_nid_1, type=NodeType.Fact.value, name='',
        pos_x=0, pos_y=0, index=0, meta={})
    node_obj_2 = Node.objects.create(
        package=package_obj, nid=node_nid_2, type=NodeType.Fact.value, name='',
        pos_x=0, pos_y=0, index=0, meta={})
    phelp = PackageHelper(
        package=package_obj, hid=phelp_dc['Id'], name=phelp_dc['Name'],
        type=PackageHelperType.Sequence.value, index=random.randint(1e3, 1e4),
        pos_x=phelp_dc['PosX'], pos_y=phelp_dc['PosY'],
        size_x=phelp_dc['SizeX'], size_y=phelp_dc['SizeY'],
        meta={'Sequence': phelp_dc['Meta']['Sequence']})
    phelp.save()

    PackageHelperNode.objects.bulk_create([
        PackageHelperNode(
            package_helper=phelp, node=node_obj_2, index=1),
        PackageHelperNode(
            package_helper=phelp, node=node_obj_1, index=0),
    ])

    models.signals.post_save.send(
        PackageHelper, instance=phelp, created=True)

    assert dict(phelp) == phelp_dc


@pytest.mark.django_db
def test_package_class_remove_assets():
    '''Tests Package model - remove assets
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)

    passet_name1 = 'NFact_' + str(random.randint(1e5, 1e6))
    passet_name2 = passet_name1
    while passet_name2 == passet_name1:
        passet_name2 = 'NFact_' + str(random.randint(1e5, 1e6))

    PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT, name=passet_name1,
        index=0)

    PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT, name=passet_name2,
        index=1)

    passets_bef = list(PackageAsset.objects.filter(
        package=package_obj).order_by('index'))

    assert len(passets_bef) == 2
    assert passets_bef[0].name == passet_name1
    assert passets_bef[1].name == passet_name2

    package_obj.remove_assets()
    passets_aft = PackageAsset.objects.filter(package=package_obj).count()

    assert passets_aft == 0


@pytest.mark.django_db
def test_package_class_remove_nodes():
    '''Tests Package model - remove nodes
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    node_name = 'Factor_' + str(random.randint(1e5, 1e6))
    Node.objects.create(
        package=package_obj, type=NodeType.Fact.value, name=node_name, pos_x=0,
        pos_y=0, index=0, meta={})

    nodes_bef = list(Node.objects.filter(
        package=package_obj).order_by('index'))
    assert nodes_bef[0].name == node_name
    package_obj.remove_nodes()
    nodes_aft = Node.objects.filter(package=package_obj).count()

    assert len(nodes_bef) == 1
    assert nodes_aft == 0


def test_packageaction_repr():
    '''Tests PackageAction model - repr
    '''
    package_id = random.randint(1e5, 1e6)
    package_obj = Package(id=package_id)

    pact_name = 'Action_' + str(random.randint(1e5, 1e6))
    pact_index = random.randint(1e2, 1e3)
    pact = PackageAction(
        package=package_obj, index=pact_index, name=pact_name)

    assert str(pact) == '[' + str(package_id) + '][' + str(
        pact_index) + '] ' + pact_name


def test_packageentitytype_repr():
    '''Tests PackageEntityType model - repr
    '''
    package_id = random.randint(1e5, 1e6)
    package_obj = Package(id=package_id)

    package_entity_type_id = random.randint(1e5, 1e6)
    package_entity_type = PackageEntityType(id=package_entity_type_id)

    index = random.randint(1e2, 1e3)
    name = 'Class_' + str(random.randint(1e5, 1e6))

    pkg_entity_type = PackageEntityType(
        package=package_obj, parent=None, index=index, name=name)

    assert str(pkg_entity_type) == '[PID=' + str(package_id) + '][PAR=' + str(
        0) + '][IDX=' + str(index) + '] ' + name

    pkg_entity_type = PackageEntityType(
        package=package_obj, parent=package_entity_type, index=index,
        name=name)

    assert str(pkg_entity_type) == '[PID=' + str(package_id) + '][PAR=' + str(
        package_entity_type_id) + '][IDX=' + str(index) + '] ' + name


def test_packageentitytype_iter():
    '''Tests PackageEntityType model - iterator
    '''
    name = 'Class_' + str(random.randint(1e5, 1e6))

    pkg_entity_type = PackageEntityType(name=name)

    assert dict(pkg_entity_type) == {'Name': name}


def test_packageasset_repr():
    '''Tests PackageAsset model - repr
    '''
    passet_name = 'Fact_' + str(random.randint(1e5, 1e6))
    index = random.randint(1e2, 1e3)
    passet = PackageAsset(
        type=PackageAsset.TYPE_FACT, index=index, name=passet_name)

    assert str(passet) == '[' + PackageAsset.TYPE_FACT + '][' + \
        str(index) + '] ' + passet_name


def test_packageassettype_repr():
    '''Tests PackageAssetType model - repr
    '''
    index = random.randint(1e2, 1e3)
    package_entity_type_id = random.randint(1e5, 1e6)
    package_entity_type = PackageEntityType(id=package_entity_type_id)

    patype = PackageAssetType(
        index=index, package_entity_type=package_entity_type)

    assert str(patype) == '[' + str(index) + '] ' + str(package_entity_type_id)


@pytest.mark.django_db
def test_package_class_iter_assets_with_types_not_nentity():
    '''Tests Package model - iterator with package non-NEntity assets and types
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)

    passet_name1 = 'NFact_' + str(random.randint(1e5, 1e6))
    passet_name2 = passet_name1
    while passet_name2 == passet_name1:
        passet_name2 = 'NFact_' + str(random.randint(1e5, 1e6))

    PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT,
        name=passet_name1, index=1)
    passet2 = PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT,
        name=passet_name2, index=0)

    entity_type1 = PackageEntityType.objects.create(
        package=package_obj, parent=None, index=0, name=passet_name1)
    entity_type2 = PackageEntityType.objects.create(
        package=package_obj, parent=None, index=0, name=passet_name2)

    PackageAssetType.objects.create(
        package=package_obj, package_asset=passet2,
        package_entity_type=entity_type2, index=1)
    PackageAssetType.objects.create(
        package=package_obj, package_asset=passet2,
        package_entity_type=entity_type1, index=0)

    package_dc = dict(package_obj)

    assert len(package_dc['Assets']) == 2
    assert package_dc['Assets'][0]['Class'] \
        == package_dc['Assets'][1]['Class'] == PackageAsset.TYPE_FACT
    assert package_dc['Assets'][0]['Uri'] == passet_name2
    assert package_dc['Assets'][1]['Uri'] == passet_name1
    assert package_dc['Assets'][0]['Meta'] \
        == package_dc['Assets'][1]['Meta'] == {}


@pytest.mark.django_db
def test_package_class_iter_assets_with_types_nentity():
    '''Tests Package model - iterator with package NEntity assets and types
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)

    passet_name1 = 'NFact_' + str(random.randint(1e5, 1e6))
    passet_name2 = passet_name1
    while passet_name2 == passet_name1:
        passet_name2 = 'NFact_' + str(random.randint(1e5, 1e6))

    PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_ENTITY,
        name=passet_name1, index=1, is_enabled=True)
    passet2 = PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_ENTITY,
        name=passet_name2, index=0, is_enabled=False)

    entity_type1 = PackageEntityType.objects.create(
        package=package_obj, parent=None, index=0, name=passet_name1)
    entity_type2 = PackageEntityType.objects.create(
        package=package_obj, parent=None, index=0, name=passet_name2)

    PackageAssetType.objects.create(
        package=package_obj, package_asset=passet2,
        package_entity_type=entity_type2, index=1)
    PackageAssetType.objects.create(
        package=package_obj, package_asset=passet2,
        package_entity_type=entity_type1, index=0)

    package_dc = dict(package_obj)

    assert len(package_dc['Assets']) == 2
    assert package_dc['Assets'][0]['Class'] \
        == package_dc['Assets'][1]['Class'] == PackageAsset.TYPE_ENTITY
    assert package_dc['Assets'][0]['Uri'] == passet_name2
    assert package_dc['Assets'][1]['Uri'] == passet_name1

    assert package_dc['Assets'][0]['Meta'] == {
        'Types': [passet_name1, passet_name2],
        'IsEnabled': False,
    }
    assert package_dc['Assets'][1]['Meta'] == {
        'Types': [],
        'IsEnabled': True,
    }


@pytest.mark.django_db
def test_package_class_iter_assets_unset_neighborough_passet():
    '''Tests Package model - iterator
        (with package assets and unset neighborough node asset)
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)

    node_name = 'Factor_' + str(random.randint(1e5, 1e6))
    passet_name = 'NFact_' + str(random.randint(1e5, 1e6))

    node = Node.objects.create(
        package=package_obj, type=NodeType.Fact.value, name=node_name, pos_x=0,
        pos_y=0, index=0, meta={})

    passet = PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT,
        name=passet_name, index=0)

    NodeAsset.objects.create(
        node=node, package_asset=passet, class_index=0, name_index=0)
    NodeAsset.objects.create(
        node=node, package_asset=None, class_index=0, name_index=1)

    package_dc = dict(package_obj)

    assert len(package_dc['Assets']) == 1
    assert package_dc['Assets'][0]['Class'] == PackageAsset.TYPE_FACT
    assert package_dc['Assets'][0]['Uri'] == passet_name
    assert package_dc['Assets'][0]['Meta'] == {}

    assert len(package_dc['Nodes']) == 1
    assert len(package_dc['Nodes'][0]['Assets']) == 1
    assert package_dc['Nodes'][0]['Assets'][0]['Class'] == passet.type
    assert package_dc['Nodes'][0]['Assets'][0]['Uris'] == [passet_name, '']


@pytest.mark.django_db
def test_package_class_iter_assets_unset_exclusive_passet():
    '''Tests Package model - iterator
        (with package assets and unset exclusive node asset)
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)

    node_name = 'Factor_' + str(random.randint(1e5, 1e6))
    passet_name = 'NFact_' + str(random.randint(1e5, 1e6))

    node = Node.objects.create(
        package=package_obj, type=NodeType.Fact.value, name=node_name, pos_x=0,
        pos_y=0, index=0, meta={})

    PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT,
        name=passet_name, index=0)

    NodeAsset.objects.create(
        node=node, package_asset=None, class_index=0, name_index=0)

    package_dc = dict(package_obj)

    assert len(package_dc['Assets']) == 1
    assert package_dc['Assets'][0]['Class'] == PackageAsset.TYPE_FACT
    assert package_dc['Assets'][0]['Uri'] == passet_name
    assert package_dc['Assets'][0]['Meta'] == {}

    assert len(package_dc['Nodes']) == 1
    assert len(package_dc['Nodes'][0]['Assets']) == 1
    assert package_dc['Nodes'][0]['Assets'][0]['Class'] \
        == PackageAsset.TYPE_ENTITY
    assert package_dc['Nodes'][0]['Assets'][0]['Uris'] == ['']


def test_packagehelper_repr():
    '''Tests PackageHelper model - repr
    '''
    package_id = random.randint(1e5, 1e6)
    package_obj = Package(id=package_id)
    phelp_type = random.choice(list(PackageHelperType)).value
    phelp_name = 'Helper #' + str(random.randint(1e5, 1e6))
    phelp_index = random.randint(1e5, 1e6)

    phelp = PackageHelper(
        package=package_obj, type=phelp_type, name=phelp_name,
        index=phelp_index)

    assert str(phelp) == '[' + str(phelp_type) + '][' + str(
        package_id) + '][' + str(phelp_index) + '] ' + phelp_name[:20]


def test_packagehelpernode_repr():
    '''Tests PackageHelperNode model - repr
    '''
    phelp_id = random.randint(1e5, 1e6)
    phelp_obj = PackageHelper(id=phelp_id)
    node_nid = 'Node_' + str(random.randint(1e5, 1e6))
    node_obj = Node(nid=node_nid)
    unode_idx = random.randint(1e5, 1e6)

    phelp_unode = PackageHelperNode(
        package_helper=phelp_obj, node=node_obj, index=unode_idx)

    assert str(phelp_unode) == '[' + str(phelp_id) + '][' + str(
        unode_idx) + '] ' + node_nid


def test_node_repr():
    '''Tests Node model - repr
    '''
    node_name = 'Fact_' + str(random.randint(1e5, 1e6))
    node_obj = Node(nid=node_name, name=node_name)

    assert str(node_obj) == '[' + node_name + '] ' + node_name


def test_nodeasset_repr():
    '''Tests NodeAsset model - repr
    '''
    passet = PackageAsset(
        id=random.randint(1e5, 1e6), type=random.choice(PackageAsset.TYPES)[0])
    class_index = random.randint(1e3, 1e4)
    name_index = random.randint(1e3, 1e4)
    nasset = NodeAsset(
        package_asset=passet, class_index=class_index, name_index=name_index)

    assert str(nasset) == '[' + str(class_index) + '][' + str(name_index) \
        + '] PID=' + str(passet.id)


def test_nodelink_repr():
    '''Tests NodeLink model - repr
    '''
    nlink_type = random.choice(NodeLink.TYPES)[0]
    node = Node(nid='Node_' + str(random.randint(1e3, 1e4)))
    nlink_obj = NodeLink(
        type=nlink_type, linked_node=node, my_pin_index=0, index=0)

    assert str(nlink_obj) == '[' + nlink_type + '] -> ' + node.nid


def test_nodelink_iter():
    '''Tests NodeLink model - iterator
    '''
    nlink_type = random.choice(NodeLink.TYPES)[0]
    node = Node(nid='Node_' + str(random.randint(1e3, 1e4)))
    mp_index = random.randint(1e3, 1e4)
    op_index = mp_index
    while op_index == mp_index:
        op_index = random.randint(1e3, 1e4)
    nlink_obj = NodeLink(
        type=nlink_type, linked_node=node, my_pin_index=mp_index,
        other_pin_index=op_index, index=0)

    try:
        assert isinstance(iter(nlink_obj), Iterable)
    except TypeError:
        assert False

    nlink_dc = dict(nlink_obj)

    assert nlink_dc
    assert nlink_dc['LinkedNodeId'] == node.nid
    assert nlink_dc['MyPinIndex'] == mp_index
    assert nlink_dc['OtherPinIndex'] == op_index


@pytest.mark.django_db
def test_node_iter_basic():
    '''Tests Node model - iterator (basic)
    '''
    node_name = 'Fact_' + str(random.randint(1e5, 1e6))
    pos_x = random.randint(1e5, 1e6)
    pos_y = random.randint(1e5, 1e6)
    node_obj = Node(name=node_name, pos_x=pos_x, pos_y=pos_y)
    try:
        assert isinstance(iter(node_obj), Iterable)
    except TypeError:
        assert False

    node_dc = dict(node_obj)

    assert node_dc
    assert node_dc['PosX'] == pos_x
    assert node_dc['PosY'] == pos_y


@pytest.mark.django_db
def test_node_iter_node_assets():
    '''Tests Node model - iterator (with node assets)
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)

    node_name = 'Fact_' + str(random.randint(1e5, 1e6))
    pos_x = random.randint(1e5, 1e6)
    pos_y = random.randint(1e5, 1e6)
    node_obj = Node.objects.create(
        package=package_obj, type=NodeType.Fact.value, name=node_name,
        pos_x=pos_x, pos_y=pos_y, index=0, meta={})

    passet_name1 = 'NFact_' + str(random.randint(1e5, 1e6))
    passet_name2 = passet_name1
    while passet_name2 == passet_name1:
        passet_name2 = 'NFact_' + str(random.randint(1e5, 1e6))

    passet1 = PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT,
        name=passet_name1, index=random.randint(1e2, 1e3))
    passet2 = PackageAsset.objects.create(
        package=package_obj, type=PackageAsset.TYPE_FACT,
        name=passet_name2, index=random.randint(1e2, 1e3))

    NodeAsset.objects.bulk_create([
        NodeAsset(
            node=node_obj, package_asset=passet1, class_index=0, name_index=1),
        NodeAsset(
            node=node_obj, package_asset=passet2, class_index=0, name_index=0),
    ])

    node_dc = dict(node_obj)

    assert len(node_dc['Assets']) == 1
    assert node_dc['Assets'][0]['Class'] == PackageAsset.TYPE_FACT
    assert node_dc['Assets'][0]['Uris'][0] == passet_name2
    assert node_dc['Assets'][0]['Uris'][1] == passet_name1


@pytest.mark.django_db
def test_node_iter_node_links():
    '''Tests Node model - iterator (with node links)
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    node_name = 'Fact_' + str(random.randint(1e5, 1e6))
    node_obj = Node.objects.create(
        package=package_obj, type=NodeType.Fact.value, name=node_name, pos_x=0,
        pos_y=0, index=0, meta={})

    inp_blk = Node.objects.create(
        nid='Node_' + str(random.randint(1e5, 1e6)), package=package_obj,
        pos_x=0, pos_y=0, index=0, meta={})
    out_blk = Node(
        nid=inp_blk.nid, package=package_obj, pos_x=0, pos_y=0, index=1,
        meta={})
    while inp_blk.nid != out_blk.nid:
        out_blk.nid = 'Node_' + str(random.randint(1e5, 1e6))
    out_blk.save()

    links = [
        NodeLink(
            node=node_obj, type=NodeLink.TYPE_OUTPUT,
            linked_node=out_blk, my_pin_index=56, other_pin_index=78,
            index=3),
        NodeLink(
            node=node_obj, type=NodeLink.TYPE_INPUT,
            linked_node=inp_blk, my_pin_index=34, other_pin_index=12,
            index=2),
        NodeLink(
            node=node_obj, type=NodeLink.TYPE_INPUT,
            linked_node=inp_blk, my_pin_index=12, other_pin_index=34,
            index=1),
    ]
    NodeLink.objects.bulk_create(links)

    for link in links:
        models.signals.post_save.send(NodeLink, instance=link, created=True)

    node_dc = dict(node_obj)

    assert node_dc
    assert 'InLinks' in node_dc
    assert len(node_dc['InLinks']) == 2
    assert node_dc['InLinks'][0]['LinkedNodeId'] == inp_blk.nid
    assert node_dc['InLinks'][0]['MyPinIndex'] == 12
    assert node_dc['InLinks'][0]['OtherPinIndex'] == 34
    assert node_dc['InLinks'][1]['LinkedNodeId'] == inp_blk.nid
    assert node_dc['InLinks'][1]['MyPinIndex'] == 34
    assert node_dc['InLinks'][1]['OtherPinIndex'] == 12

    assert 'OutLinks' in node_dc
    assert len(node_dc['OutLinks']) == 1
    assert node_dc['OutLinks'][0]['LinkedNodeId'] == out_blk.nid
    assert node_dc['OutLinks'][0]['MyPinIndex'] == 56
    assert node_dc['OutLinks'][0]['OtherPinIndex'] == 78


@pytest.mark.django_db
def test_node_iter_node_content_custom():
    '''Tests Node model - iterator (with node contents - type Custom)
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    node_name = 'Node_' + str(random.randint(1e5, 1e6))
    node_meta = {}
    for idx in range(3):
        key = 'TestParam1_' + str(idx) + '_' + str(
            random.randint(1e5, 1e6))
        val = 'someString_' + str(idx) + '_' + str(
            random.randint(1e5, 1e6))
        node_meta[key] = val

    node_obj = Node.objects.create(
        package=package_obj, type=NodeType.Custom.value, name=node_name,
        pos_x=0, pos_y=0, index=0, meta=node_meta)

    node_dc = dict(node_obj)

    assert node_dc

    assert node_dc['Meta'] == node_meta


@pytest.mark.django_db
def test_node_delete():
    '''Tests Node model - delete
    '''
    package_obj = Package.objects.create(filename=TEST_DATA_FNAME)
    node_name = 'Node_' + str(random.randint(1e5, 1e6))

    node_obj = Node.objects.create(
        package=package_obj, type=NodeType.End.value, nid=node_name,
        name=node_name, pos_x=0, pos_y=0, index=0, meta={})

    nodes_qs = Node.objects.filter(package=package_obj, nid=node_obj.nid)
    assert nodes_qs.count() == 1

    node_obj.delete()

    nodes_qs = Node.objects.filter(package=package_obj, nid=node_obj.nid)
    assert nodes_qs.count() == 0

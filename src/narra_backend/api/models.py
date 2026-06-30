# -*- coding: utf-8 -*-

'''Models module
'''

import copy
import json
import string
from collections import OrderedDict
from enum import Enum
from functools import partial
from uuid import uuid4

from django.core.cache import cache
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _u

from .utils.strings import (
    gen_uniq_ident,
    make_random_text,
)


class NodeType(Enum):
    '''Node type class
    '''
    Action = 'Action'
    Choice = 'Choice'
    ChoiceTimeout = 'ChoiceTimeout'
    Condition = 'Condition'
    Custom = 'Custom'
    Delay = 'Delay'
    DialogueLine = 'DialogueLine'
    End = 'End'
    Event = 'Event'
    Fact = 'Fact'
    Objective = 'Objective'
    Reroute = 'Reroute'
    Sound = 'Sound'
    Start = 'Start'
    Story = 'Story'
    Trigger = 'Trigger'


class PackageHelperType(Enum):
    '''Helper type class
    '''
    Comment = 'Comment'
    Image = 'Image'
    Sequence = 'Sequence'
    StickyNote = 'StickyNote'
    Union = 'Union'


class Package(models.Model):
    '''Package model class
    '''
    filename = models.CharField(
        _u('filename'), max_length=512, db_index=True)
    author = models.ForeignKey(
        'units.Member', blank=True, null=True, on_delete=SET_NULL)
    team = models.ForeignKey(
        'units.Team', null=True, blank=True, on_delete=SET_NULL)
    ctime = models.DateTimeField(
        _u('creation time'), default=timezone.now, db_index=True)
    mtime = models.DateTimeField(
        _u('modification time'), default=timezone.now, db_index=True)
    story_name = models.CharField(
        _u('story name'), max_length=128, db_index=True)
    uasset_ver = models.CharField(
        _u('UAsset version'), max_length=16)
    story_ver = models.CharField(
        _u('Story version'), max_length=16)
    json_ver = models.CharField(
        _u('JSON version'), max_length=16)
    locked_at = models.DateTimeField(
        _u('locked at'), null=True, blank=True, default=None)
    locked_by = models.ForeignKey(
        'units.Member', blank=True, null=True, on_delete=SET_NULL,
        related_name='locked_packages')

    class Meta:
        abstract = False
        verbose_name = _u('Package')
        verbose_name_plural = _u('Packages')

    def __str__(self):
        return self.filename

    def to_json(self):
        '''Returns object instance as JSON string
        '''
        return json.dumps(
            dict(self), ensure_ascii=False, indent=2, separators=(',', ':'))

    def fetch_package_assets(self):
        '''Fetches package assets
        '''
        passets_dc = {
            obj.id: obj for obj in PackageAsset.objects.order_by(
                'index').filter(package=self)}
        passets_types = PackageAssetType.objects.order_by('index').filter(
            package=self).select_related('package_entity_type')

        passet_meta_by_passet = {}
        for ptype in passets_types:
            passet_id = ptype.package_asset_id
            if passets_dc[passet_id].type == PackageAsset.TYPE_ENTITY:
                if passet_id not in passet_meta_by_passet:
                    passet_meta_by_passet[passet_id] = {
                        'Types': [],
                        'IsEnabled': passets_dc[passet_id].is_enabled,
                    }
                if ptype.package_entity_type:
                    passet_meta_by_passet[passet_id]['Types'].append(
                        ptype.package_entity_type.name)

        for passet_id, passet_obj in passets_dc.items():
            if passet_obj.type == PackageAsset.TYPE_ENTITY and \
                    passet_id not in passet_meta_by_passet:
                passet_meta_by_passet[passet_id] = {
                    'Types': [],
                    'IsEnabled': passet_obj.is_enabled,
                }

        return [
            {
                '_pid': passet.id,
                'Class': passet.type,
                'Uri': passet.name,
                'Meta': passet_meta_by_passet[
                    passet.id] if passet.id in passet_meta_by_passet else {},
            } for passet in passets_dc.values()]

    @classmethod
    def _bind_entity_types_children(
            cls, entity_types_lst, entity_type_parent, children_lst):
        '''Binds entity types children
        '''
        for entity_type_obj in entity_types_lst:
            if entity_type_obj.parent == entity_type_parent:
                sub_struct = {
                    'Name': entity_type_obj.name,
                    'Children': [],
                }
                cls._bind_entity_types_children(
                    entity_types_lst, entity_type_obj, sub_struct['Children'])
                children_lst.append(sub_struct)

    def fetch_package_entity_types(self):
        '''Fetches package entity types
        '''
        package_entity_types = list(PackageEntityType.objects.order_by(
            'index').filter(package=self))
        entity_types_lst = []
        self._bind_entity_types_children(
            package_entity_types, None, entity_types_lst)

        return entity_types_lst

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('StoryName', self.story_name)
#        yield (
#            'LockedAt', str(int(self.locked_at.timestamp()))
#            if self.locked_at else '')
#        yield ('LockedBy', self.locked_by.email if self.locked_by else '')
        yield ('ModTime', str(int(self.mtime.timestamp())))
        yield ('JSONVersion', self.json_ver)
        yield ('StoryVersion', self.story_ver)
        yield ('UAssetVersion', self.uasset_ver)

        get_part_fn = partial(
            PackageAction.objects.order_by('index').filter, package=self)
        package_actions = cache.get_or_set(
            'package_actions_' + str(self.id), get_part_fn, 3600)
        yield ('Actions', [dict(action) for action in package_actions])

        get_part_fn = self.fetch_package_entity_types
        pkg_entypes = cache.get_or_set(
            'package_entity_types_' + str(self.id), get_part_fn, 3600)
        yield ('EntityTypes', pkg_entypes or [
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
        ])

        get_part_fn = self.fetch_package_assets
        pkg_assets = cache.get_or_set(
            'package_assets_' + str(self.id), get_part_fn, 3600)
        yield ('Assets', [{
            'Class': elem['Class'],
            'Uri': elem['Uri'],
            'Meta': elem['Meta'],
        } for elem in pkg_assets])

        get_part_fn = partial(
            Node.objects.order_by('index').filter, package=self,
            container=None)
        package_nodes = cache.get_or_set(
            'package_nodes_' + str(self.id), get_part_fn, 3600)
        yield ('Nodes', [dict(node) for node in package_nodes])

        get_part_fn = partial(
            PackageHelper.objects.order_by('index').filter, package=self)
        package_helpers = cache.get_or_set(
            'package_helpers_' + str(self.id), get_part_fn, 3600)
        yield ('Helpers', [dict(helper) for helper in package_helpers])

    def remove_actions(self):
        '''Removes package actions
        '''
        PackageAction.objects.filter(package=self).delete()
        models.signals.post_delete.send(Package, instance=self)

    def remove_entity_types(self):
        '''Removes package entity types
        '''
        PackageEntityType.objects.filter(package=self).delete()
        models.signals.post_delete.send(Package, instance=self)

    def remove_assets(self):
        '''Removes package assets
        '''
        PackageAsset.objects.filter(package=self).delete()
        models.signals.post_delete.send(Package, instance=self)

    def remove_nodes(self):
        '''Removes package nodes
        '''
        Node.objects.filter(package=self).delete()
        models.signals.post_delete.send(Package, instance=self)

    def remove_helpers(self):
        '''Removes package helpers
        '''
        PackageHelper.objects.filter(package=self).delete()
        models.signals.post_delete.send(Package, instance=self)

    def can_modify(self, user):
        '''Checks if user can modify package
        '''
        return self.team.is_member(
            user) if self.team else self.author_id == user.id


class PackageAction(models.Model):
    '''Package action model class
    '''
    package = models.ForeignKey(
        'api.Package', on_delete=CASCADE)
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)
    name = models.CharField(
        _u('name'), blank=True, null=True, max_length=256)
    params = JSONField(_u('parameters'))

    class Meta:
        abstract = False
        verbose_name = _u('Package action')
        verbose_name_plural = _u('Package actions')

    def __str__(self):
        return '[' + str(self.package_id) + '][' + str(
            self.index) + '] ' + self.name

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('Name', self.name)
        yield ('Params', self.params)


class PackageAsset(models.Model):
    '''Package asset model class
    '''
    TYPE_ENTITY = 'NEntity'
    TYPE_FACT = 'NFact'
    TYPE_OBJECTIVE = 'NObjective'
    TYPE_STORY = 'NStory'
    TYPE_SOUND_CUE = 'SoundCue'
    TYPES = [
        (TYPE_ENTITY, _u('entity')),
        (TYPE_FACT, _u('fact')),
        (TYPE_OBJECTIVE, _u('objective')),
        (TYPE_STORY, _u('story')),
        (TYPE_SOUND_CUE, _u('sound cue')),
    ]
    package = models.ForeignKey(
        'api.Package', on_delete=CASCADE)
    type = models.CharField(
        _u('type'), choices=TYPES, max_length=16, db_index=True)
    name = models.CharField(
        _u('name'), blank=True, null=True, max_length=256, db_index=True)
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)
    is_enabled = models.BooleanField(
        _u('is enabled'), default=False)

    class Meta:
        abstract = False
        verbose_name = _u('Package asset')
        verbose_name_plural = _u('Package assets')
        unique_together = (('package', 'name'),)

    def __str__(self):
        return '[' + self.type + '][' + str(self.index) + '] ' + self.name


class PackageEntityType(models.Model):
    '''Package entity type model class
    '''
    package = models.ForeignKey(
        'api.Package', on_delete=CASCADE)
    parent = models.ForeignKey(
        'api.PackageEntityType', blank=True, null=True, on_delete=CASCADE)
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)
    name = models.CharField(
        _u('name'), blank=True, null=True, max_length=256)

    class Meta:
        abstract = False
        verbose_name = _u('Package entity type')
        verbose_name_plural = _u('Package entity types')

    def __str__(self):
        return '[PID=' + str(self.package_id) + '][PAR=' + str(
            self.parent_id or 0) + '][IDX=' + str(
                self.index) + '] ' + self.name

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('Name', self.name)


class PackageAssetType(models.Model):
    '''Package asset type model class
    '''
    package = models.ForeignKey(
        'api.Package', on_delete=CASCADE)
    package_asset = models.ForeignKey(
        'api.PackageAsset', on_delete=CASCADE)
    package_entity_type = models.ForeignKey(
        'api.PackageEntityType', blank=True, null=True, on_delete=CASCADE)
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)

    class Meta:
        abstract = False
        verbose_name = _u('Package asset type')
        verbose_name_plural = _u('Package asset types')

    def __str__(self):
        return '[' + str(self.index) + '] ' + str(self.package_entity_type_id)


class PackageHelper(models.Model):
    '''Package helper model class
    '''
    package = models.ForeignKey(
        'api.Package', on_delete=CASCADE)
    hid = models.CharField(
        _u('helper ID'), max_length=128, db_index=True, default=uuid4)
    type = models.CharField(
        _u('type'), choices=sorted(
            [(htype.name, htype.value) for htype in PackageHelperType]),
        max_length=16, db_index=True)
    name = models.CharField(
        _u('name'), blank=True, null=True, max_length=512)
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)
    pos_x = models.IntegerField(
        _u('x position'))
    pos_y = models.IntegerField(
        _u('y position'))
    size_x = models.PositiveIntegerField(
        _u('x size'))
    size_y = models.PositiveIntegerField(
        _u('y size'))
    meta = JSONField(_u('node meta'))

    class Meta:
        abstract = False
        verbose_name = _u('Package helper')
        verbose_name_plural = _u('Package helper')

    def __str__(self):
        return '[' + self.type + '][' + str(self.package_id) + '][' + str(
            self.index) + '] ' + self.name[:20]

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        meta = copy.deepcopy(self.meta)

        if self.type in [
                PackageHelperType.Sequence.value,
                PackageHelperType.Union.value]:
            get_part_fn = partial(
                PackageHelperNode.objects.order_by(
                    'index').select_related('contained_node').values(
                        'node__nid').filter, package_helper=self)
            package_nodes = cache.get_or_set(
                'package_helper_nodes_' + str(self.id), get_part_fn,
                3600)
            meta['ContainedNodes'] = [
                node['node__nid'] for node in package_nodes]

        yield ('Id', self.hid)
        yield ('Meta', meta)
        yield ('Name', self.name)
        yield ('PosX', self.pos_x)
        yield ('PosY', self.pos_y)
        yield ('SizeX', self.size_x)
        yield ('SizeY', self.size_y)
        yield ('Type', self.type)


class PackageHelperNode(models.Model):
    '''Package helper node model class
    '''
    package_helper = models.ForeignKey(
        'api.PackageHelper', on_delete=CASCADE)
    node = models.ForeignKey(
        'api.Node', on_delete=CASCADE, related_name='contained_node')
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)

    class Meta:
        abstract = False
        verbose_name = _u('Package helper node')
        verbose_name_plural = _u('Package helper nodes')

    def __str__(self):
        return '[' + str(self.package_helper_id) + '][' + str(
            self.index) + '] ' + self.node.nid


class Node(models.Model):
    '''Node model class
    '''
    package = models.ForeignKey(
        'api.Package', on_delete=CASCADE)
    container = models.ForeignKey(
        'api.Node', blank=True, null=True, on_delete=CASCADE)
    name = models.CharField(
        _u('name'), max_length=128, db_index=True)
    type = models.CharField(
        _u('type'), choices=sorted(
            [(ntype.name, ntype.value) for ntype in NodeType]),
        max_length=16, db_index=True)
    weight = models.IntegerField(
        _u('weight'), default=0)
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)
    nid = models.CharField(
        _u('node ID'), max_length=128, db_index=True)
    description = models.CharField(
        _u('description'), max_length=512, default='')
    pos_x = models.IntegerField(
        _u('x position'))
    pos_y = models.IntegerField(
        _u('y position'))
    tags = ArrayField(
        models.CharField(max_length=255), default=list)
    trigger_tags = ArrayField(
        models.CharField(max_length=255), default=list)
    input_pins = models.PositiveSmallIntegerField(
        _u('input pins number'), default=1)
    output_pins = models.PositiveSmallIntegerField(
        _u('output pins number'), default=1)
    meta = JSONField(_u('node meta'))

    class Meta:
        abstract = False
        verbose_name = _u('Node')
        verbose_name_plural = _u('Nodes')

    def __str__(self):
        return '[' + self.nid + '] ' + self.name

    def fetch_node_assets(self):
        '''Fetches node's assets
        '''
        node_assets = NodeAsset.objects.order_by(
            'class_index', 'name_index').select_related(
                'package_asset').filter(node=self)

        nassets_dc = OrderedDict()
        for nasset in node_assets:
            if nasset.package_asset:
                pa_type = nasset.package_asset.type
                if pa_type not in nassets_dc:
                    nassets_dc[pa_type] = []
                nassets_dc[pa_type].append(nasset.package_asset.name)
            else:
                items = list(nassets_dc.items())
                if items:
                    pa_type = items[-1][0]
                else:
                    pa_type = PackageAsset.TYPE_ENTITY
                if pa_type not in nassets_dc:
                    nassets_dc[pa_type] = []
                nassets_dc[pa_type].append('')

        return nassets_dc

    def _iter_node_assets(self):
        '''Returns node assets as iterator
        '''
        get_part_fn = self.fetch_node_assets
        node_assets = cache.get_or_set(
            'node_assets_' + str(self.id), get_part_fn, 3600)

        yield (
            'Assets', [{
                'Class': na_class,
                'Uris': na_uris,
            } for na_class, na_uris in node_assets.items()])

    def _iter_node_links(self):
        '''Returns node links as iterator
        '''
        get_part_fn = partial(
            NodeLink.objects.select_related('linked_node').order_by(
                'index').filter, node=self)
        links = cache.get_or_set(
            'node_links_' + str(self.id), get_part_fn, 3600)
        yield (
            'InLinks', [dict(link) for link in links
                        if link.type == NodeLink.TYPE_INPUT])
        yield (
            'OutLinks', [dict(link) for link in links
                         if link.type == NodeLink.TYPE_OUTPUT])

    def _iter_node_components(self):
        '''Returns node components as iterator
        '''
        get_part_fn = partial(
            Node.objects.order_by('index').filter, container=self)
        comps = cache.get_or_set(
            'node_components_' + str(self.id), get_part_fn, 3600)
        yield ('Components', [dict(comp) for comp in comps])

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('Description', self.description)
        yield ('Id', self.nid)
        yield ('Meta', self.meta)
        yield ('Name', self.name)
        yield ('PosX', self.pos_x)
        yield ('PosY', self.pos_y)
        yield ('Tags', self.tags)
        yield ('TriggerTags', self.trigger_tags)
        yield ('Type', self.type)
        yield ('Weight', self.weight)
        yield ('InPins', self.input_pins)
        yield ('OutPins', self.output_pins)

        for item in self._iter_node_assets():
            yield item
        for item in self._iter_node_links():
            yield item
        for item in self._iter_node_components():
            yield item


class NodeAsset(models.Model):
    '''Node asset model class
    '''
    node = models.ForeignKey(
        'api.Node', on_delete=CASCADE)
    package_asset = models.ForeignKey(
        'api.PackageAsset', blank=True, null=True, on_delete=SET_NULL)
    class_index = models.PositiveSmallIntegerField(
        _u('class index'), db_index=True)
    name_index = models.PositiveSmallIntegerField(
        _u('name index'), db_index=True)

    class Meta:
        abstract = False
        verbose_name = _u('Node asset')
        verbose_name_plural = _u('Node assets')

    def __str__(self):
        return '[' + str(self.class_index) + '][' + str(self.name_index) \
            + '] PID=' + str(self.package_asset_id)


class NodeLink(models.Model):
    '''Node link model class
    '''
    TYPE_INPUT = 'inp'
    TYPE_OUTPUT = 'out'
    TYPES = [
        (TYPE_INPUT, _u('input')),
        (TYPE_OUTPUT, _u('output')),
    ]
    node = models.ForeignKey(
        'api.Node', on_delete=CASCADE)
    type = models.CharField(
        _u('type'), choices=TYPES, max_length=8)
    linked_node = models.ForeignKey(
        'api.Node', on_delete=CASCADE,
        related_name='linked_node')
    index = models.PositiveSmallIntegerField(
        _u('index'), db_index=True)
    my_pin_index = models.PositiveSmallIntegerField(
        _u('my pin index'))
    other_pin_index = models.PositiveSmallIntegerField(
        _u('other pin index'), blank=True, null=True)

    class Meta:
        abstract = False
        verbose_name = _u('Node link')
        verbose_name_plural = _u('Node links')

    def __str__(self):
        return '[' + self.type + '] -> ' + self.linked_node.nid

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('LinkedNodeId', self.linked_node.nid)
        yield ('MyPinIndex', self.my_pin_index)
        yield ('OtherPinIndex', self.other_pin_index)


class Release(models.Model):
    '''Release model class
    '''
    ctime = models.DateTimeField(
        _u('creation time'), default=timezone.now)
    unreal_ver = models.CharField(
        _u('unreal version'), max_length=32, db_index=True)
    release_ver = models.CharField(
        _u('release version'), max_length=32, db_index=True)
    changes = models.CharField(
        _u('changes'), max_length=512)

    class Meta:
        abstract = False
        verbose_name = _u('Release')
        verbose_name_plural = _u('Releases')

    def __str__(self):
        return '%s / %s' % (self.unreal_ver, self.release_ver)

    def __iter__(self):
        '''Returns object instance as iterator
        '''
        yield ('id', self.id)
        yield ('unreal_ver', self.unreal_ver)
        yield ('release_ver', self.release_ver)
        yield ('changes', self.changes)


class ReleaseUID(models.Model):
    '''Organization model class
    '''
    UID_MAX_LEN = 64
    UID_CHARS = string.digits + string.ascii_letters + '-.~'

    organization = models.ForeignKey(
        'units.Organization', null=True, blank=True, on_delete=CASCADE)
    ctime = models.DateTimeField(
        _u('creation time'), default=timezone.now)
    release = models.ForeignKey(
        'api.Release', null=True, blank=True, on_delete=CASCADE)
    uid = models.CharField(
        _u('UID'), max_length=UID_MAX_LEN, db_index=True)
    url = models.URLField(
        _u('URL'), max_length=256, default='')

    class Meta:
        abstract = False
        verbose_name = _u('Release UID')
        verbose_name_plural = _u('Release UIDs')

    def __str__(self):
        return '[%s] %s...' % (self.release_id, self.uid[:32])

    @staticmethod
    def gen_uid(release, organization):
        '''Generates unique UID
        '''
        prefix = str(organization.id) + '_' + release.unreal_ver + \
            '_' + release.release_ver + '_'
        uid_rest_len = ReleaseUID.UID_MAX_LEN - len(prefix)

        assert uid_rest_len > 0

        return gen_uniq_ident(
            ReleaseUID, 'uid', lambda: prefix + make_random_text(
                uid_rest_len, ReleaseUID.UID_CHARS))


@receiver(
    models.signals.post_save, sender=PackageAction,
    dispatch_uid='PackageAction save issued')
@receiver(
    models.signals.post_delete, sender=PackageAction,
    dispatch_uid='PackageAction delete issued')
def invalidate_packageaction_cache(sender, instance, **kwargs):
    '''Invalidates PackageAction cache
    '''
    cache.delete_many([
        'package_actions_' + str(instance.package_id),
    ])


@receiver(
    models.signals.post_save, sender=PackageEntityType,
    dispatch_uid='PackageEntityType save issued')
@receiver(
    models.signals.post_delete, sender=PackageEntityType,
    dispatch_uid='PackageEntityType delete issued')
def invalidate_packageentitytype_cache(sender, instance, **kwargs):
    '''Invalidates PackageEntityType cache
    '''
    cache.delete_many([
        'package_entity_types_' + str(instance.package_id),
    ])


@receiver(
    models.signals.post_save, sender=PackageAsset,
    dispatch_uid='PackageAsset save issued')
@receiver(
    models.signals.post_delete, sender=PackageAsset,
    dispatch_uid='PackageAsset delete issued')
def invalidate_packageasset_cache(sender, instance, **kwargs):
    '''Invalidates PackageAssets cache
    '''
    cache.delete('package_assets_' + str(instance.package_id))


@receiver(
    models.signals.post_save, sender=PackageHelperNode,
    dispatch_uid='PackageHelperNode save issued')
@receiver(
    models.signals.post_delete, sender=PackageHelperNode,
    dispatch_uid='PackageHelperNode delete issued')
def invalidate_packagehelper_node_cache(sender, instance, **kwargs):
    '''Invalidates PackageHelperNode cache
    '''
    cache.delete('package_helper_nodes_' + str(
        instance.package_helper_id))


@receiver(
    models.signals.post_save, sender=PackageHelper,
    dispatch_uid='PackageHelper save issued')
@receiver(
    models.signals.post_delete, sender=PackageHelper,
    dispatch_uid='PackageHelper delete issued')
def invalidate_packagehelper_cache(sender, instance, **kwargs):
    '''Invalidates PackageHelper cache
    '''
    cache.delete_many([
        'package_helpers_' + str(instance.package_id),
        'package_helper_nodes_' + str(instance.id),
    ])


@receiver(
    models.signals.post_save, sender=Package,
    dispatch_uid='Package save issued')
@receiver(
    models.signals.post_delete, sender=Package,
    dispatch_uid='Package delete issued')
def invalidate_package_related_caches(sender, instance, **kwargs):
    '''Invalidates Package-related caches
    '''
    package_id = str(instance.id)
    cache.delete_many([
        'package_' + package_id,
        'package_actions_' + package_id,
        'package_entity_types_' + package_id,
        'package_assets_' + package_id,
        'package_nodes_' + package_id,
        'package_helpers_' + package_id,
    ])


@receiver(
    models.signals.post_save, sender=NodeAsset,
    dispatch_uid='NodeAsset save issued')
@receiver(
    models.signals.post_delete, sender=NodeAsset,
    dispatch_uid='NodeAsset delete issued')
def invalidate_nodeasset_cache(sender, instance, **kwargs):
    '''Invalidates NodeAsset cache
    '''
    cache.delete('node_assets_' + str(instance.node_id))


@receiver(
    models.signals.post_save, sender=NodeLink,
    dispatch_uid='NodeLink save issued')
@receiver(
    models.signals.post_delete, sender=NodeLink,
    dispatch_uid='NodeLink delete issued')
def invalidate_nodelink_cache(sender, instance, **kwargs):
    '''Invalidates NodeLink cache
    '''
    cache.delete('node_links_' + str(instance.node_id))


@receiver(
    models.signals.post_save, sender=Node,
    dispatch_uid='Node save issued')
@receiver(
    models.signals.post_delete, sender=Node,
    dispatch_uid='Node delete issued')
def invalidate_node_related_caches(sender, instance, **kwargs):
    '''Invalidates Node-related caches
    '''
    node_id = str(instance.id)
    cache.delete_many([
        'node_' + node_id,
        'node_assets_' + node_id,
        'node_components_' + node_id,
        'node_links_' + node_id,
    ])

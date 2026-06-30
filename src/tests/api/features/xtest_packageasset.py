# -*- coding: utf-8 -*-

'''Tests module
'''

import copy
import string

import pytest
from hypothesis import (
    given,
    HealthCheck,
    settings as ht_settings,
    strategies as st,
)
from hypothesis.extra.django import from_model, TransactionTestCase

from django.conf import settings

from narra_backend.api.models import (
    Package,
    PackageAsset,
)

from ..commons import (
    PACKAGE_DEF,
    valid_story_ver,
    valid_text,
    valid_uasset_ver,
)


ASSET_NAME_CHARS = string.digits + string.ascii_letters \
    + '$&()+,-./:@[\\]^_{}~'


def deduplicate_assets_by_name_and_index(passets):
    '''Deduplicates assets by name
    '''
    return sorted(
        {passet.name: passet for passet in {
            passet.index: passet for passet in passets}.values()}.values(),
        key=lambda passet: passet.index)


def draw_packageassets(data_st, package_obj=None):
    '''Draws a PackageAsset-s
    '''
    types = list(item[0] for item in PackageAsset.TYPES)

    json_ver_st = st.just(settings.PACKAGE_JSON_VER)

    if package_obj is None:
        package_st = from_model(
            Package,
            filename=valid_text(), story_name=valid_text(),
            json_ver=json_ver_st,
            story_ver=valid_story_ver(data_st, json_ver_st),
            uasset_ver=valid_uasset_ver(data_st, json_ver_st))
    else:
        package_st = st.just(package_obj)

    packageassets_st = package_st.flatmap(
        lambda pkg: st.lists(
            from_model(
                PackageAsset,
                package=st.just(pkg),
                type=st.sampled_from(types),
                name=valid_text(alphabet=ASSET_NAME_CHARS, min_size=1),
                index=st.integers(min_value=0, max_value=32767)),
            min_size=1)).map(deduplicate_assets_by_name_and_index)

    return data_st.draw(packageassets_st)


class TestPackageAsset(TransactionTestCase):
    '''Test case class
    '''
    @given(st.data())
    @ht_settings(deadline=2000, suppress_health_check=(HealthCheck.too_slow,))
    @pytest.mark.django_db
    def test_packageasset_model(self, data_st):
        '''Tests PackageAsset model
        '''
        packageassets = draw_packageassets(data_st)

        package_obj = packageassets[0].package

        _package_dc = copy.deepcopy(PACKAGE_DEF)
        _package_dc['StoryName'] = package_obj.story_name
        _package_dc['JSONVersion'] = package_obj.json_ver
        _package_dc['UAssetVersion'] = package_obj.uasset_ver
        _package_dc['StoryVersion'] = package_obj.story_ver

        _package_dc['Assets'].extend({
            '_idx': passet.index,
            '_pid': passet.package_id,
            '_aid': passet.id,
            'Class': passet.type,
            'Meta': {},
            'Uri': passet.name,
        } for passet in sorted(packageassets, key=lambda passet: passet.index))

#        print('assets from db:', [
#            (
#                '_pid', obj.package_id, '_aid', obj.id, str(obj),
#            ) for obj in PackageAsset.objects.filter(
#                package=package_obj).order_by('index')])
#        print('assets from ht:', _package_dc['Assets'])

        package_dc = dict(package_obj)

        assert _package_dc == package_dc

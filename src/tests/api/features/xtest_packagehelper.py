# -*- coding: utf-8 -*-

'''Tests module
'''

import copy

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
    PackageHelper,
)

from ..commons import (
    PACKAGE_DEF,
    valid_story_ver,
    valid_text,
    valid_uasset_ver,
)


def draw_packagehelpers(data_st, package_obj=None):
    '''Draws a PackageHelper-s
    '''
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

    packagehelpers_st = package_st.flatmap(
        lambda pkg: st.lists(
            from_model(
                PackageHelper,
                package=st.just(pkg),
                name=valid_text(),
                index=st.integers(min_value=0, max_value=32767),
                pos_x=st.integers(
                    min_value=-2 ** 31, max_value=2 ** 31 - 1),
                pos_y=st.integers(
                    min_value=-2 ** 31, max_value=2 ** 31 - 1),
                size_x=st.integers(min_value=0, max_value=2 ** 31 - 1),
                size_y=st.integers(min_value=0, max_value=2 ** 31 - 1)),
            min_size=1))

    return data_st.draw(packagehelpers_st)


class TestPackageHelper(TransactionTestCase):
    '''Test case class
    '''
    @given(st.data())
    @ht_settings(deadline=2000, suppress_health_check=(HealthCheck.too_slow,))
    @pytest.mark.django_db
    def test_packagehelper_model(self, data_st):
        '''Tests PackageHelper model
        '''
        packagehelpers = draw_packagehelpers(data_st)

        package_obj = packagehelpers[0].package

        _package_dc = copy.deepcopy(PACKAGE_DEF)
        _package_dc['StoryName'] = package_obj.story_name
        _package_dc['JSONVersion'] = package_obj.json_ver
        _package_dc['UAssetVersion'] = package_obj.uasset_ver
        _package_dc['StoryVersion'] = package_obj.story_ver

        _package_dc['Helpers'].extend([dict(pcomm) for pcomm in sorted(
            packagehelpers, key=lambda pcomm: pcomm.index)])

        package_dc = dict(package_obj)

        assert _package_dc == package_dc

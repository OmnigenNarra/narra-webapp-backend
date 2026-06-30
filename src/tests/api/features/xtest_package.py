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

from narra_backend.api.models import (
    Package,
)

from ..commons import (
    PACKAGE_DEF,
    valid_json_ver,
    valid_story_ver,
    valid_text,
    valid_uasset_ver,
)


def draw_package(data_st):
    '''Draws a Package
    '''
    json_ver_st = valid_json_ver()

    return data_st.draw(from_model(
        Package,
        filename=valid_text(), story_name=valid_text(), json_ver=json_ver_st,
        story_ver=valid_story_ver(data_st, json_ver_st),
        uasset_ver=valid_uasset_ver(data_st, json_ver_st)))


class TestPackage(TransactionTestCase):
    '''Test case class
    '''
    @given(st.data())
    @ht_settings(deadline=2000, suppress_health_check=(HealthCheck.too_slow,))
    @pytest.mark.django_db
    def test_package_model(self, data_st):
        '''Tests Package model
        '''
        package_obj = draw_package(data_st)

        assert package_obj.id

        _package_dc = copy.deepcopy(PACKAGE_DEF)
        _package_dc['StoryName'] = package_obj.story_name
        _package_dc['UAssetVersion'] = package_obj.uasset_ver
        _package_dc['StoryVersion'] = package_obj.story_ver

        package_dc = dict(package_obj)

        assert _package_dc == package_dc

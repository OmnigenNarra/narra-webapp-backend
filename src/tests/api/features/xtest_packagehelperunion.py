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
    Node,
    NodeType,
    Package,
    PackageHelper,
    PackageHelperType,
    PackageHelperNode,
)

from ..commons import (
    PACKAGE_DEF,
    valid_story_ver,
    valid_text,
    valid_uasset_ver,
)


def color_gen(data_st):
    '''Union color entry generator
    '''
    rgba_st = st.floats(
        min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False,
        width=32)

    rgba = data_st.draw(st.lists(rgba_st, min_size=4, max_size=4))

    return st.just('(R=%0.4f,G=%0.4f,B=%0.4f,A=%0.4f)' % tuple(rgba))


def node_nid_gen(data_st):
    '''Node NID entry generator
    '''
    nid = data_st.draw(st.integers(min_value=0))

    return st.just('NStoryBlock_' + str(nid))


def draw_packagehelpers(data_st, package_obj=None):
    '''Draws a PackageHelper-s, type Union
    '''
    types = [
        NodeType.Custom.value,
        NodeType.End.value,
        NodeType.Choice.value,
        NodeType.Start.value,
        NodeType.Story.value,
    ]

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

    packagehelper_st = package_st.flatmap(
        lambda pkg: st.lists(
            from_model(
                PackageHelper,
                package=st.just(pkg),
                type=st.just(PackageHelperType.Union.value),
                name=valid_text(),
                color=color_gen(data_st),
                index=st.integers(min_value=0, max_value=32767),
                pos_x=st.integers(
                    min_value=-2 ** 31, max_value=2 ** 31 - 1),
                pos_y=st.integers(
                    min_value=-2 ** 31, max_value=2 ** 31 - 1),
                size_x=st.integers(min_value=0, max_value=2 ** 31 - 1),
                size_y=st.integers(min_value=0, max_value=2 ** 31 - 1)),
            min_size=1))

    packagehelper_objs = data_st.draw(packagehelper_st)

    from_model(
        Node,
        package=st.just(package_obj),
        nid=node_nid_gen(data_st),
        name=valid_text(),
        type=st.sampled_from(types),
        description=valid_text(),
        pos_x=st.integers(min_value=-2 ** 31, max_value=2 ** 31 - 1),
        pos_y=st.integers(min_value=-2 ** 31, max_value=2 ** 31 - 1),
        index=st.integers(min_value=0, max_value=32767)).flatmap(
            lambda node: st.lists(
                from_model(
                    PackageHelperNode,
                    package_helper=st.sampled_from(packagehelper_st),
                    node=st.just(node),
                    index=st.integers(min_value=0, max_value=32767)),
                min_size=0))

    return packagehelper_objs


class TestPackageHelperUnion(TransactionTestCase):
    '''Test case class
    '''
    @given(st.data())
    @ht_settings(deadline=2000, suppress_health_check=(HealthCheck.too_slow,))
    @pytest.mark.django_db
    def test_packagehelper_union_model(self, data_st):
        '''Tests PackageHelper model, type Union
        '''
        packagehelpers = draw_packagehelpers(data_st)

        package_obj = packagehelpers[0].package

        _package_dc = copy.deepcopy(PACKAGE_DEF)
        _package_dc['StoryName'] = package_obj.story_name
        _package_dc['JSONVersion'] = package_obj.json_ver
        _package_dc['UAssetVersion'] = package_obj.uasset_ver
        _package_dc['StoryVersion'] = package_obj.story_ver

        _package_dc['Helpers'].extend([dict(phelp) for phelp in sorted(
            packagehelpers, key=lambda phelp: phelp.index)])

        package_dc = dict(package_obj)

        assert _package_dc == package_dc

# -*- coding: utf-8 -*-

'''Migration module
'''

from django.conf import settings


def migrate(package_dc):
    '''Migration method
    '''
    ver = '4.6.0'
    package_dc['JSONVersion'] = ver
    package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver]['StoryVersion']
    package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    for phelp_dc in package_dc['Helpers']:
        if 'Id' not in phelp_dc:
            phelp_dc['Id'] = ''

    return package_dc

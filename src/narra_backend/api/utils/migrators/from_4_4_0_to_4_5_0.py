# -*- coding: utf-8 -*-

'''Migration module
'''

from django.conf import settings


def convert_nodes(nodes):
    '''Converts node
    '''
    for node_data in nodes:
        node_data['Weight'] = 0
        if node_data['Type'] == 'Condition':
            if node_data['Meta']['Mode'] == 'Switch':
                for idx, case_str in enumerate(node_data['Meta'].pop('Cases')):
                    if 'Cases' not in node_data['Meta']:
                        node_data['Meta']['Cases'] = []
                    node_data['Meta']['Cases'].append({
                        'Name': 'Case #' + str(idx + 1),
                        'Value': case_str,
                    })
            elif node_data['Meta']['Mode'] in ['Random', 'Iterate']:
                node_data['Meta']['Cases'] = []
                for idx in range(node_data['OutPins']):
                    node_data['Meta']['Cases'].append({
                        'Name': 'Case #' + str(idx + 1),
                    })

        convert_nodes(node_data['Components'])


def migrate(package_dc):
    '''Migration method
    '''
    ver = '4.5.0'
    package_dc['JSONVersion'] = ver
    package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver]['StoryVersion']
    package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    for asset_entry in package_dc['Assets']:
        if asset_entry['Class'] == 'NEntity':
            if 'Types' not in asset_entry['Meta']:
                asset_entry['Meta']['Types'] = []
            asset_entry['Meta']['IsEnabled'] = True

    convert_nodes(package_dc['Nodes'])

    return package_dc

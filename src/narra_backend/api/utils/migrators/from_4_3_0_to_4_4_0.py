# -*- coding: utf-8 -*-

'''Migration module
'''

from django.conf import settings

from narra_backend.api.models import NodeType


def _get_pins_num_by_mypinindex(node_data):
    '''Get pins number by MyPinIndex
    '''
    if not node_data['InLinks']:
        return 0

    return max([link['MyPinIndex'] for link in node_data['InLinks']]) + 1


def _get_pins_num_by_cases(node_data):
    '''Get pins number by MyPinIndex
    '''
    if node_data['Type'] == NodeType.Condition.value:
        if node_data['Meta']['Mode'] in ['Branch', 'Switch']:
            return len(node_data['Meta']['Cases'])
        if node_data['Meta']['Mode'] == 'DoN':
            return 2
        if node_data['Meta']['Mode'] in ['Iterate', 'Random']:
            return 1

        raise ValueError

    if node_data['Type'] in [
            NodeType.Action.value,
            NodeType.Choice.value,
            NodeType.ChoiceTimeout.value,
            NodeType.Custom.value,
            NodeType.Delay.value,
            NodeType.DialogueLine.value,
            NodeType.End.value,
            NodeType.Event.value,
            NodeType.Fact.value,
            NodeType.Objective.value,
            NodeType.Reroute.value,
            NodeType.Sound.value,
            NodeType.Start.value,
            NodeType.Story.value,
            NodeType.Trigger.value]:
        return 1

    raise ValueError


def setup_components_inpins(node_data):
    '''Setups components InPins attribute
    '''
    node_data['InPins'] = 1
    for _node_data in node_data['Components']:
        setup_components_inpins(_node_data)


def migrate(package_dc):
    '''Migration method
    '''
    ver = '4.4.0'
    package_dc['JSONVersion'] = ver
    package_dc['StoryVersion'] = settings.PACKAGE_VERSIONS[ver]['StoryVersion']
    package_dc['UAssetVersion'] = settings.PACKAGE_VERSIONS[ver][
        'UAssetVersion']

    for node_data in package_dc['Nodes']:
        node_data['InPins'] = max([
            _get_pins_num_by_mypinindex(node_data),
            _get_pins_num_by_cases(node_data),
        ])
        setup_components_inpins(node_data)

    return package_dc

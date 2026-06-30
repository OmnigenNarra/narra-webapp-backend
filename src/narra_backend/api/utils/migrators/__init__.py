# -*- coding: utf-8 -*-

'''Migrators utils module
'''

import copy
import importlib
import logging

from semver import (
    parse_version_info as pvi,
)


LOG = logging.getLogger(__name__)


class VersionMigrator:
    '''Version migrator class
    '''
    def __init__(
            self, package_dc, curr_version, latest_version,
            available_versions):
        self.package_dc = package_dc
        self.curr_version = pvi(curr_version)
        self.latest_version = pvi(latest_version)
        self.available_versions = (pvi(ver) for ver in available_versions)

    def get_next_version(self):
        '''Returns next version
        '''
        to_version = None
        while True:
            to_version = next(self.available_versions)
            if to_version == self.curr_version:
                return next(self.available_versions)
            if to_version > self.curr_version:
                return to_version

    def migrate(self):
        '''Does migration step(s)
        '''
        while self.curr_version < self.latest_version:
            try:
                to_version = self.get_next_version()
            except StopIteration:
                LOG.error('No next version: %s', self.curr_version)
                break

            mod_name = ('from_' + str(self.curr_version) + '_to_' + str(
                to_version)).replace('.', '_')
            try:
                migrate_mod = importlib.import_module(
                    '.' + mod_name, package=__package__)
            except ImportError:
                LOG.error('No migration module: %s', mod_name)
                break

            package_dc = copy.deepcopy(self.package_dc)
            self.package_dc = migrate_mod.migrate(package_dc)
            self.curr_version = to_version

        return self.package_dc

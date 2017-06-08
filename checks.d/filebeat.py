# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import json
import os

# project
from checks import AgentCheck


class FilebeatCheck(AgentCheck):

    def check(self, instance):
        registry_file_path = instance.get('registry_file_path')
        if registry_file_path is None:
            raise Exception('An absolute path to a filebeat registry path must be specified')

        registry_contents = self._parse_registry_file(registry_file_path)

        for item in registry_contents.itervalues():
            self._process_registry_item(item)

    def _parse_registry_file(self, registry_file_path):
        try:
            with open(registry_file_path) as registry_file:
                return json.load(registry_file)
        except IOError:
            self.log.warn('No filebeat registry file found at %s' % (registry_file_path, ))
            return {}

    def _process_registry_item(self, item):
        source = item['source']
        offset = item['offset']

        try:
            stats = os.stat(source)

            if self._is_same_file(stats, item['FileStateOS']):
                unprocessed_bytes = stats.st_size - offset

                self.gauge('filebeat.registry.unprocessed_bytes', unprocessed_bytes,
                           tags=["source:{0}".format(source)])
            else:
                self.log.debug("Filebeat source %s appears to have changed" % (source, ))
        except OSError:
            self.log.debug("Unable to get stats on filebeat source %s" % (source, ))

    def _is_same_file(self, stats, file_state_os):
        return stats.st_dev == file_state_os['device'] and stats.st_ino == file_state_os['inode']

"""
Collects extended network metrics.
"""
# stdlib
import re

# project
from checks import AgentCheck
from utils import network


class NetworkExt(AgentCheck):

    SOURCE_TYPE_NAME = 'system'

    def check(self, instance):
        if instance is None:
            instance = {}

        proc_location = self.agentConfig.get('procfs_path', '/proc').rstrip('/')
        network.check_all(self, "system.net", proc_location)

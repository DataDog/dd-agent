# stdlib
import os
import re

# project
from checks import AgentCheck
from config import _is_affirmative
from util import Platform
from utils.subprocess_output import get_subprocess_output

class NsdCheck(AgentCheck):
    # Stats info https://www.nlnetlabs.nl/projects/nsd/nsd-control.8.html

    NSD_CTL = ['nsd-control', 'stats']

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("NSD check only supports one configured instance.")

    def check(self, instance):
        if instance is None:
            instance = {}

        host = instance.get('host')
        tags = instance.get('tags', [])

        nsd_out, _, _ = get_subprocess_output(self.NSD_CTL + ['-s', host], self.log)
        self.log.debug(self.NSD_CTL + ['-s', host])
        self.log.debug(nsd_out)

        data = re.findall(r'(\S+)=(.*\d)', nsd_out)

        for stat in data:
            self.log.debug('nsd.{}:{}'.format(stat[0], stat[1]))

            if 'num.' in stat[0]:
                self.rate('nsd.{}'.format(stat[0]), float(stat[1]), tags=tags)
            else:
                self.gauge('nsd.{}'.format(stat[0]), float(stat[1]), tags=tags)

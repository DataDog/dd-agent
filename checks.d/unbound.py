# stdlib
import re

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output

class UnboundCheck(AgentCheck):
    # Stats info https://unbound.net/documentation/unbound-control.html

    UNBOUND_CTL = ['unbound-control', 'stats']

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("Unbound check only supports one configured instance.")

    def check(self, instance):
        if instance is None:
            instance = {}

        host = instance.get('host')
        tags = instance.get('tags', [])

        ub_out, _, _ = get_subprocess_output(self.UNBOUND_CTL + ['-s', host], self.log)
        self.log.debug(self.UNBOUND_CTL + ['-s', host])
        self.log.debug(ub_out)

        data = re.findall(r'(\S+)=(.*\d)', ub_out)

        for stat in data:
            if 'histogram' not in stat[0]: # dont send histogram metrics
                self.log.debug('unbound.{}:{}'.format(stat[0], stat[1]))

                if 'num.' in stat[0]:
                    self.rate('unbound.{}'.format(stat[0]), float(stat[1]), tags=tags)
                elif 'time.' in stat[0]:
                    self.gauge('unbound.{}'.format(stat[0]), float(stat[1]), tags=tags)
                elif 'unwanted.' in stat[0]:
                    self.rate('unbound.{}'.format(stat[0]), float(stat[1]), tags=tags)
                else:
                    self.gauge('unbound.{}'.format(stat[0]), float(stat[1]), tags=tags)

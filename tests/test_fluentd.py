import unittest
import logging
import os
from nose.plugins.attrib import attr
logger = logging.getLogger(__file__)

from tests.common import get_check

@attr(requires='fluentd')
class TestFluentd(unittest.TestCase):

    def setUp(self):
        self.fluentd_config = """
init_config:

instances:
    -   monitor_agent_url: http://localhost:24220/api/plugins.json
        tags:
            - instance:first
    -   monitor_agent_url: http://localhost:24220/api/plugins.json
        tags:
            - instance:second
"""

    def testFluentd(self):
        f, instances = get_check('fluentd', self.fluentd_config)

        f.check(instances[0])
        metrics = f.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:first'])

        f.check(instances[1])
        metrics = f.get_metrics()
        self.assertEquals(metrics[0][3].get('tags'), ['instance:second'])

        service_checks = f.get_service_checks()
        is_ok = [sc for sc in service_checks if sc['check'] == 'fluentd.is_ok']
        for i in range(len(is_ok)):
            self.assertEquals(set(is_ok[i]['tags']), set(['host:localhost', 'port:24220']), service_checks)

if __name__ == '__main__':
    unittest.main()

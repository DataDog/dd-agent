import unittest
import logging
import time

from util import get_hostname
from tests.common import load_check
from nose.plugins.attrib import attr
logging.basicConfig()

@attr('process')
class ProcessTestCase(unittest.TestCase):

    def build_config(self, config, n):
        critical_low = [2, 2, 2, -1, 2, -2, 2]
        critical_high = [2, 2, 2, 3, -1, 4, -2]
        warning_low = [1, -1, 2, -1, 2, -1, 2]
        warning_high = [1, 3, -1, 2, -1, 3, -1]

        for i in range(7):
            name = 'ssh' + str(i)
            config['instances'].append({
                'name': name,
                'search_string': ['ssh', 'sshd'],
                'thresholds': {
                    'critical': [n - critical_low[i], n + critical_high[i]],
                    'warning': [n - warning_low[i], n + warning_high[i]]
                }
            })

        return config

    def testCheck(self):
        config = {
            'init_config': {},
            'instances': []
        }
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }
        search_string = ['ssh', 'sshd']

        self.check = load_check('process', config, self.agentConfig)

        pids = self.check.find_pids(search_string)
        config = self.build_config(config, len(pids))

        for i in range(7):
            self.check.check(config['instances'][i])
            time.sleep(1)

        service_checks = self.check.get_service_checks()

        assert service_checks

        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) > 0)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 0]), 1, service_checks)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 1]), 2, service_checks)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 2]), 4, service_checks)

if __name__ == "__main__":
    unittest.main()

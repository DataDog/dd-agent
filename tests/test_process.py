import unittest
import logging
import time

from util import get_hostname
from tests.common import load_check
from nose.plugins.attrib import attr
logging.basicConfig()

@attr('process')
class ProcessTestCase(unittest.TestCase):
    offset = 0
    nb_procs = [0, 1, 3, 5, 6]
    def build_config(self, config):
        # 6 possible configurations:
        # C--W--W--C
        # W--C--C--W
        # W--C--W--C
        # C--W--C--W
        # C--C--W--W
        # W--W--C--C
        # 1--2--4--5
        # There is some redundancy but every cases should be tested
        critical_low = [2, 1, 2, 1, 1, 4]
        critical_high = [4, 5, 5, 4, 2, 5]
        warning_low = [1, 2, 1, 2, 4, 1]
        warning_high = [5, 4, 4, 5, 5, 2]

        for i in range(6):
            name = 'test' + str(i)
            config['instances'].append({
                'name': name,
                'search_string': ['test'],
                'thresholds': {
                    'critical': [critical_low[i], critical_high[i]],
                    'warning': [warning_low[i], warning_high[i]]
                }
            })

        # Adding two cases where there is no configuration
        config['instances'].append({
            'name': 'testnothresholds',
            'search_string': ['test']
        })
        config['instances'].append({
            'name': 'testnoranges',
            'search_string': ['test'],
            'thresholds': {
                "test": "test"
            }
        })
        return config

    def find_pids(self, search_string, exact_match=True):
        x = self.nb_procs[self.offset]
        ret = []
        for i in range(x):
            ret.append(0)
        return ret

    def testCheck(self):
        config = {
            'init_config': {},
            'instances': []
        }
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('process', config, self.agentConfig)

        config = self.build_config(config)
        self.check.find_pids = self.find_pids

        for i in self.nb_procs:
            for j in range(len(config['instances'])):
                self.check.check(config['instances'][j])
                time.sleep(1)

            self.offset += 1

        service_checks = self.check.get_service_checks()

        assert service_checks

        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) > 0)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 0]), 12, service_checks)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 1]), 6, service_checks)
        self.assertEquals(len([t for t in service_checks
            if t['status']== 2]), 22, service_checks)

if __name__ == "__main__":
    unittest.main()

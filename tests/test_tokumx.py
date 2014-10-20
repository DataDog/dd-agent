import unittest
from nose.plugins.attrib import attr
import time

import pymongo

from tests.common import load_check

PORT1 = 37017
PORT2 = 37018
MAX_WAIT = 150

@attr(requires='mongo')
class TestTokuMX(unittest.TestCase):
    def testTokuMXCheck(self):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.config = {
            'instances': [{
                'server': "mongodb://localhost:%s/test" % PORT1
            },
            {
                'server': "mongodb://localhost:%s/test" % PORT2
            }]
        }

        # Test mongodb with checks.d
        self.check = load_check('tokumx', self.config, self.agentConfig)

        # Run the check against our running server
        self.check.check(self.config['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(self.config['instances'][0])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

        metric_val_checks = {
            'mongodb.connections.current': lambda x: x >= 1,
            'mongodb.connections.available': lambda x: x >= 1,
            'mongodb.uptime': lambda x: x >= 0,
            'mongodb.ft.cachetable.size.current': lambda x: x > 0,
            'mongodb.ft.cachetable.size.limit': lambda x: x > 0,
        }

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue( metric_val_checks[metric_name]( m[2] ) )

        # Run the check against our running server
        self.check.check(self.config['instances'][1])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(self.config['instances'][1])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue( metric_val_checks[metric_name]( m[2] ) )

if __name__ == '__main__':
    unittest.main()

# stdlib
import time
from types import ListType
import unittest

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import load_check

PORT1 = 37017
PORT2 = 37018
MAX_WAIT = 150


@attr(requires='mongo')
class TestMongo(unittest.TestCase):
    def testMongoCheck(self):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.config = {
            'instances': [{
                'server': "mongodb://localhost:%s/test" % PORT1
            }, {
                'server': "mongodb://localhost:%s/test" % PORT2
            }]
        }

        # Test mongodb with checks.d
        self.check = load_check('mongo', self.config, self.agentConfig)

        # Run the check against our running server
        self.check.check(self.config['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(self.config['instances'][0])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)

        metric_val_checks = {
            'mongodb.connections.current': lambda x: x >= 1,
            'mongodb.connections.available': lambda x: x >= 1,
            'mongodb.uptime': lambda x: x >= 0,
            'mongodb.mem.resident': lambda x: x > 0,
            'mongodb.mem.virtual': lambda x: x > 0
        }

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue(metric_val_checks[metric_name](m[2]))

        # Run the check against our running server
        self.check.check(self.config['instances'][1])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(self.config['instances'][1])

        # Service checks
        service_checks = self.check.get_service_checks()
        print service_checks
        service_checks_count = len(service_checks)
        self.assertTrue(isinstance(service_checks, ListType))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == self.check.SERVICE_CHECK_NAME]), 4, service_checks)
        # Assert that all service checks have the proper tags: host and port
        self.assertEquals(len([sc for sc in service_checks if "host:localhost" in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "port:%s" % PORT1 in sc['tags'] or "port:%s" % PORT2 in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "db:test" in sc['tags']]), service_checks_count, service_checks)

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue(metric_val_checks[metric_name](m[2]))

    def testMongoOldConfig(self):
        conf = {
            'init_config': {},
            'instances': [
                {'server': "mongodb://localhost:%s/test" % PORT1},
                {'server': "mongodb://localhost:%s/test" % PORT2},
            ]
        }

        # Test the first mongodb instance
        self.check = load_check('mongo', conf, {})

        # Run the check against our running server
        self.check.check(conf['instances'][0])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(conf['instances'][0])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)

        metric_val_checks = {
            'mongodb.connections.current': lambda x: x >= 1,
            'mongodb.connections.available': lambda x: x >= 1,
            'mongodb.uptime': lambda x: x >= 0,
            'mongodb.mem.resident': lambda x: x > 0,
            'mongodb.mem.virtual': lambda x: x > 0
        }

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue(metric_val_checks[metric_name](m[2]))

        # Run the check against our running server
        self.check.check(conf['instances'][1])
        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rates
        self.check.check(conf['instances'][1])

        # Metric assertions
        metrics = self.check.get_metrics()
        assert metrics
        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 0)

        for m in metrics:
            metric_name = m[0]
            if metric_name in metric_val_checks:
                self.assertTrue(metric_val_checks[metric_name](m[2]))

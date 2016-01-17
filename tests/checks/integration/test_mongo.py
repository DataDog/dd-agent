# stdlib
from types import ListType
import time
import unittest

# 3p
from mock import Mock
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest, load_check

PORT1 = 37017
PORT2 = 37018
MAX_WAIT = 150

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate


class TestMongoUnit(AgentCheckTest):
    """
    Unit tests for MongoDB AgentCheck.
    """
    CHECK_NAME = 'mongo'

    MONGODB_CONFIG = {
        'server': "mongodb://localhost:%s/test" % PORT1
    }

    def test_build_metric_list(self):
        """
        Build the metric list according to the user configuration.
        Print a warning when an option has no match.
        """
        # Initialize check
        config = {
            'instances': [self.MONGODB_CONFIG]
        }

        self.load_check(config)
        setattr(self.check, "log", Mock())
        build_metric_list = self.check._build_metric_list_to_collect

        # Default metric list
        DEFAULT_METRICS = self.check.BASE_METRICS

        # No option
        no_additional_metrics = build_metric_list([])
        self.assertEquals(len(no_additional_metrics), len(DEFAULT_METRICS))

        # One correct option
        default_and_tcmalloc_metrics = build_metric_list(['tcmalloc'])
        self.assertEquals(
            len(default_and_tcmalloc_metrics),
            len(DEFAULT_METRICS) + len(self.check.TCMALLOC_METRICS)
        )

        # One wrong and correct option
        default_and_tcmalloc_metrics = build_metric_list(['foobar', 'top'])
        self.assertEquals(
            len(default_and_tcmalloc_metrics),
            len(DEFAULT_METRICS) + len(self.check.TOP_METRICS)
        )
        self.assertEquals(self.check.log.warning.called, 1)

    def test_metric_resolution(self):
        """
        Resolve metric names and types.
        """
        # Initialize check and tests
        config = {
            'instances': [self.MONGODB_CONFIG]
        }
        metrics_to_collect = {
            'foobar': (GAUGE, 'barfoo'),
            'foo.bar': (RATE, 'bar.foo'),
            'fOoBaR': GAUGE,
            'fOo.baR': RATE,
        }
        self.load_check(config)
        resolve_metric = self.check._resolve_metric

        # Assert

        # Priority to aliases when defined
        self.assertEquals((GAUGE, 'mongodb.barfoo'), resolve_metric('foobar', metrics_to_collect))
        self.assertEquals((RATE, 'mongodb.bar.foops'), resolve_metric('foo.bar', metrics_to_collect))  # noqa
        self.assertEquals((GAUGE, 'mongodb.qux.barfoo'), resolve_metric('foobar', metrics_to_collect, prefix="qux"))  # noqa

        #  Resolve an alias when not defined
        self.assertEquals((GAUGE, 'mongodb.foobar'), resolve_metric('fOoBaR', metrics_to_collect))
        self.assertEquals((RATE, 'mongodb.foo.barps'), resolve_metric('fOo.baR', metrics_to_collect))  # noqa
        self.assertEquals((GAUGE, 'mongodb.qux.foobar'), resolve_metric('fOoBaR', metrics_to_collect, prefix="qux"))  # noqa

    def test_metric_normalization(self):
        """
        Metric names suffixed with `.R`, `.r`, `.W`, `.w` are renamed.
        """
        # Initialize check and tests
        config = {
            'instances': [self.MONGODB_CONFIG]
        }
        metrics_to_collect = {
            'foo.bar': GAUGE,
            'foobar.r': GAUGE,
            'foobar.R': RATE,
            'foobar.w': RATE,
            'foobar.W': GAUGE,
        }
        self.load_check(config)
        resolve_metric = self.check._resolve_metric

        # Assert
        self.assertEquals((GAUGE, 'mongodb.foo.bar'), resolve_metric('foo.bar', metrics_to_collect))  # noqa

        self.assertEquals((RATE, 'mongodb.foobar.sharedps'), resolve_metric('foobar.R', metrics_to_collect))  # noqa
        self.assertEquals((GAUGE, 'mongodb.foobar.intent_shared'), resolve_metric('foobar.r', metrics_to_collect))  # noqa
        self.assertEquals((RATE, 'mongodb.foobar.intent_exclusiveps'), resolve_metric('foobar.w', metrics_to_collect))  # noqa
        self.assertEquals((GAUGE, 'mongodb.foobar.exclusive'), resolve_metric('foobar.W', metrics_to_collect))  # noqa


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

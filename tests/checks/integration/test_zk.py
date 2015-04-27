# stdlib
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='zookeeper')
class ZooKeeperTestCase(AgentCheckTest):
    CHECK_NAME = 'zk'

    CONFIG = {
        'host': "127.0.0.1",
        'port': 2181,
        'expected_mode': "standalone",
        'tags': ["mytag"]
    }

    WRONG_EXPECTED_MODE = {
        'host': "127.0.0.1",
        'port': 2181,
        'expected_mode': "follower",
        'tags': []
    }

    CONNECTION_FAILURE_CONFIG = {
        'host': "127.0.0.1",
        'port': 2182,
        'expected_mode': "follower",
        'tags': []
    }

    METRICS = [
        'zookeeper.latency.min',
        'zookeeper.latency.avg',
        'zookeeper.latency.max',
        'zookeeper.bytes_received',
        'zookeeper.bytes_sent',
        'zookeeper.connections',
        'zookeeper.connections',
        'zookeeper.bytes_outstanding',
        'zookeeper.outstanding_requests',
        'zookeeper.zxid.epoch',
        'zookeeper.zxid.count',
        'zookeeper.nodes',
    ]

    def test_check(self):
        """
        Collect ZooKeeper metrics.
        """
        config = {
            'instances': [self.CONFIG]
        }
        self.run_check(config)

        # Test metrics
        for mname in self.METRICS:
            self.assertMetric(mname, tags=["mode:standalone", "mytag"], count=1)

        # Test service checks
        self.assertServiceCheck("zookeeper.ruok", status=AgentCheck.OK)
        self.assertServiceCheck("zookeeper.mode", status=AgentCheck.OK)

        self.coverage_report()

    def test_wrong_expected_mode(self):
        """
        Raise a 'critical' service check when ZooKeeper is not in the expected mode
        """
        config = {
            'instances': [self.WRONG_EXPECTED_MODE]
        }
        self.run_check(config)

        # Test service checks
        self.assertServiceCheck("zookeeper.mode", status=AgentCheck.CRITICAL)

    def test_error_state(self):
        """
        Raise a 'critical' service check when ZooKeeper is in an error state
        """
        config = {
            'instances': [self.CONNECTION_FAILURE_CONFIG]
        }

        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )

        # Test service checks
        self.assertServiceCheck("zookeeper.ruok", status=AgentCheck.CRITICAL)

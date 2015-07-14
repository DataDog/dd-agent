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
        'expected_mode': "down",
        'tags': []
    }

    STAT_METRICS = [
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
        'zookeeper.instances',
    ]

    MNTR_METRICS = [
        'zookeeper.packets.sent',
        'zookeeper.approximate.data.size',
        'zookeeper.num.alive.connections',
        'zookeeper.open.file.descriptor.count',
        'zookeeper.avg.latency',
        'zookeeper.znode.count',
        'zookeeper.outstanding.requests',
        'zookeeper.min.latency',
        'zookeeper.ephemerals.count',
        'zookeeper.watch.count',
        'zookeeper.max.file.descriptor.count',
        'zookeeper.packets.received',
        'zookeeper.max.latency',
    ]

    STATUS_TYPES = [
        'leader',
        'follower',
        'observer',
        'standalone',
        'down',
        'inactive',
        'unknown',
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
        for mname in self.STAT_METRICS:
            self.assertMetric(mname, tags=["mode:standalone", "mytag"], count=1)

        for mname in self.MNTR_METRICS:
            self.assertMetric(mname, tags=["mode:standalone", "mytag"], count=1)

        # Test service checks
        self.assertServiceCheck("zookeeper.ruok", status=AgentCheck.OK)
        self.assertServiceCheck("zookeeper.mode", status=AgentCheck.OK)

        expected_mode = self.CONFIG['expected_mode']
        for t in self.STATUS_TYPES:
            expected_value = 0
            if t == expected_mode:
                expected_value = 1
            mname = "zookeeper.instances." + t
            self.assertMetric(mname, value=expected_value, count=1)

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
        Raise a 'critical' service check when ZooKeeper is in an error state.
        Report status as down.
        """
        config = {
            'instances': [self.CONNECTION_FAILURE_CONFIG]
        }

        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )

        self.assertServiceCheck("zookeeper.ruok", status=AgentCheck.CRITICAL)

        self.assertMetric("zookeeper.instances", tags=["mode:down"], count=1)

        expected_mode = self.CONNECTION_FAILURE_CONFIG['expected_mode']
        for t in self.STATUS_TYPES:
            expected_value = 0
            if t == expected_mode:
                expected_value = 1
            mname = "zookeeper.instances." + t
            self.assertMetric(mname, value=expected_value, count=1)

# stdlib
import os
from distutils.version import LooseVersion
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
        'zookeeper.packets_sent',
        'zookeeper.approximate_data_size',
        'zookeeper.num_alive_connections',
        'zookeeper.open_file_descriptor_count',
        'zookeeper.avg_latency',
        'zookeeper.znode_count',
        'zookeeper.outstanding_requests',
        'zookeeper.min_latency',
        'zookeeper.ephemerals_count',
        'zookeeper.watch_count',
        'zookeeper.max_file_descriptor_count',
        'zookeeper.packets_received',
        'zookeeper.max_latency',
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
        self.run_check_twice(config)

        # Test metrics
        for mname in self.STAT_METRICS:
            self.assertMetric(mname, tags=["mode:standalone", "mytag"], count=1)

        zk_version = os.environ.get("FLAVOR_VERSION")

        if zk_version and LooseVersion(zk_version) > LooseVersion("3.4.0"):
            for mname in self.MNTR_METRICS:
                self.assertMetric(mname, tags=["mode:standalone", "mytag"], count=1)

        # Test service checks
        self.assertServiceCheck("zookeeper.ruok", status=AgentCheck.OK)
        self.assertServiceCheck("zookeeper.mode", status=AgentCheck.OK)

        expected_mode = self.CONFIG['expected_mode']
        mname = "zookeeper.instances." + expected_mode
        self.assertMetric(mname, value=1, count=1)

        self.coverage_report()

    def test_wrong_expected_mode(self):
        """
        Raise a 'critical' service check when ZooKeeper is not in the expected mode.
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
        mname = "zookeeper.instances." + expected_mode
        self.assertMetric(mname, value=1, count=1)

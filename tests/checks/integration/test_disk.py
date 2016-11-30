# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='system')
class TestCheckDisk(AgentCheckTest):
    CHECK_NAME = 'disk'

    DISK_GAUGES = [
        'system.disk.total',
        'system.disk.used',
        'system.disk.free',
        'system.disk.in_use',
    ]

    INODE_GAUGES = [
        'system.fs.inodes.total',
        'system.fs.inodes.used',
        'system.fs.inodes.free',
        'system.fs.inodes.in_use'
    ]

    # Really a basic check to see if all metrics are there
    def test_check(self):
        self.run_check({'instances': [{'use_mount': 'no'}]})

        # Assert metrics
        for metric in self.DISK_GAUGES + self.INODE_GAUGES:
            self.assertMetric(metric, tags=[])

        self.coverage_report()

    # Test two instances
    def test_bad_config(self):
        self.assertRaises(Exception,
                          lambda: self.run_check({'instances': [{}, {}]}))

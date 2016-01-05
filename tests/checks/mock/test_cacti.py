# stdlib
import logging
import os
import shutil
import unittest

# project
from tests.checks.common import Fixtures, get_check

log = logging.getLogger()

CONFIG = """
init_config:

instances:
    -   mysql_host: localhost
        mysql_user: root
        rrd_path:   /tmp/cacti_test/rrds
        rrd_whitelist: %s
""" % Fixtures.file('whitelist.txt')


class TestCacti(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = '/tmp/cacti_test'
        self.rrd_dir = os.path.join(os.path.dirname(__file__), "cacti")

        # Create our temporary RRD path, if needed
        try:
            os.mkdir(self.tmp_dir)
        except Exception:
            # Ignore, directory already exists
            pass

    def tearDown(self):
        # Clean up the temp directory
        shutil.rmtree(self.tmp_dir)

    def _copy_rrds(self, xml_dir):
        if os.access("/usr/bin/rrdtool", os.R_OK | os.X_OK):
            # Copy the latest RRDs from /var/lib/rra/ to the test location
            shutil.copytree("/var/lib/cacti/rra/", os.path.join(self.tmp_dir, 'rrds'))
            return True
        else:
            return False

    def testChecks(self):
        check, instances = get_check('cacti', CONFIG)
        rrd_dir = os.path.join(self.tmp_dir, 'rrds')

        # Restore the RRDs from the XML dumps
        if not self._copy_rrds(self.rrd_dir):
            return

        # Do a check to establish the last timestamps
        check.check(instances[0])
        check.get_metrics()

        # Bump the last timestamps back 20 minutes so we have some actual data
        twenty_min = 20 * 60
        for k,v in check.last_ts.items():
            check.last_ts[k] = v - twenty_min

        # Do a first check
        check.check(instances[0])
        results1 = check.get_metrics()

        # Check again and make sure no new metrics are picked up
        # But we will still have the payload stats
        check.check(instances[0])
        results2 = check.get_metrics()
        last_ts1 = check.last_ts[rrd_dir + '/localhost_hdd_free_10.rrd.AVERAGE']

        # Check once more to make sure last_ts ignores None vals when calculating
        # where to start from
        check.check(instances[0])
        check.get_metrics()
        last_ts2 = check.last_ts[rrd_dir + '/localhost_hdd_free_10.rrd.AVERAGE']

        self.assertEquals(last_ts1, last_ts2)

        metrics = [r[0] for r in results2]

        # make sure diagnostic metrics are included
        assert 'cacti.metrics.count' in metrics
        assert 'cacti.rrd.count' in metrics
        assert 'cacti.hosts.count' in metrics

        metrics_count = [r for r in results2 if r[0] == 'cacti.metrics.count'][0][2]
        hosts_count = [r for r in results2 if r[0] == 'cacti.hosts.count'][0][2]
        rrd_count = [r for r in results2 if r[0] == 'cacti.rrd.count'][0][2]

        assert metrics_count == 0
        assert hosts_count == 1
        assert rrd_count == 3

        load1 = [m[2] for m in results1 if m[0] == 'system.load.1' and m[2]]

        # Make sure some load metrics were returned
        assert len(load1) > 0

        # Should not have any - not included in the whitelist
        current_users = [m[2] for m in results1 if m[0] == 'system.users.current' and m[2]]
        self.assertEquals(len(current_users), 0)

        disk_used = [m for m in results1 if m[0] == 'system.disk.used' and m[2]]
        assert len(disk_used) > 0

        # Make sure no None values are picked up
        none_metrics = [m[2] for m in results1 if m[2] is None]
        self.assertEquals(len(none_metrics), 0)

import unittest
import os
import os.path
import logging; logger = logging.getLogger()
from checks.cacti import Cacti
import subprocess
import shutil

class TestCacti(unittest.TestCase):
    def setUp(self):
        self.cacti = Cacti(logger)
        self.tmp_dir = '/tmp/cacti_test'
        self.rrd_dir = os.path.join(os.path.dirname(__file__), "cacti")
        self.config = {
            'cacti_mysql_server': 'localhost',
            'cacti_mysql_user': 'root',
            'cacti_mysql_pass': '',
            'cacti_rrd_path': self.tmp_dir,
            'cacti_rrd_whitelist': os.path.join(os.path.dirname(__file__), "cacti", "whitelist.txt")
        }

        try:
            os.mkdir(self.tmp_dir)
        except:
            # Ignore, directory already exists
            pass

    def _restore_rrds(self, xml_dir):
        for filename in os.listdir(xml_dir):
            if filename.endswith('.xml'):
                xml_path = '/'.join([xml_dir, filename])
                rrd_name = filename.replace('.xml', '.rrd')
                subprocess.call(
                    ["/usr/bin/rrdtool","restore", xml_path, '/'.join([self.tmp_dir, rrd_name])]
                )

    def testChecks(self):
        # Restore the RRDs from the XML dumps
        self._restore_rrds(self.rrd_dir)

        # Do a first check
        results1 = self.cacti.check(self.config)

        # Check again and make sure no new metrics are picked up
        # But we will still have the payload stats
        results2 = self.cacti.check(self.config)
        last_ts1 = self.cacti.last_ts[self.tmp_dir + '/localhost_hdd_free_10.rrd.AVERAGE']

        # Check once more to make sure last_ts ignores None vals when calculating
        # where to start from
        results3 = self.cacti.check(self.config)
        last_ts2 = self.cacti.last_ts[self.tmp_dir + '/localhost_hdd_free_10.rrd.AVERAGE']

        self.assertEquals(last_ts1, last_ts2)

        self.assertEquals(results2[2][0], 'cacti.metrics.count')
        self.assertEquals(results2[2][2], 0)
        load1 = [m[2] for m in results1 if m[0] == 'system.load.1' and m[2]]
        self.assertEquals(len(load1), 253)
        self.assertEquals(load1[5], 0.17943333333)

        # Should not have any - not included in the whitelist
        current_users = [m[2] for m in results1 if m[0] == 'system.users.current' and m[2]]
        self.assertEquals(len(current_users), 0)

        disk_used = [m for m in results1 if m[0] == 'system.disk.used' and m[2]]
        self.assertEquals(max([m[2] for m in disk_used]), 144814.03333007812)
        self.assertEquals(disk_used[5][3]['device_name'], '/dev/mapper/dogdev0-root')

        # Make sure no None values are picked up
        none_metrics = [m[2] for m in results1 if m[2] is None]
        self.assertEquals(len(none_metrics), 0)

        # Cleanup by removing our temp files
        shutil.rmtree(self.tmp_dir)

if __name__ == '__main__':
    unittest.main()

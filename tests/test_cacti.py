import unittest
import os
import os.path
import logging; logger = logging.getLogger()
from checks.cacti import Cacti

class TestCacti(unittest.TestCase):
    def setUp(self):
        self.cacti = Cacti(logger)
        self.config = {
            'cacti_mysql_server': 'localhost',
            'cacti_mysql_user': 'root',
            'cacti_mysql_pass': '',
            'cacti_rrd_path': os.path.join(os.path.dirname(__file__), "cacti"),
            'cacti_rrd_whitelist': os.path.join(os.path.dirname(__file__), "cacti", "whitelist.txt")
        }

    def testChecks(self):
        # Do a first check
        results1 = self.cacti.check(self.config)

        # Check again and make sure no new metrics are picked up
        results2 = self.cacti.check(self.config)
        self.assertEquals(results2, [])

        load1 = [m[2] for m in results1 if m[0] == 'system.load.1' and m[2]]
        self.assertEquals(len(load1), 201)
        self.assertEquals(load1[5], 1.1195333333333335)

        # Should not have any - not included in the whitelist
        current_users = [m[2] for m in results1 if m[0] == 'system.users.current' and m[2]]
        self.assertEquals(len(current_users), 0)

        disk_used = [m for m in results1 if m[0] == 'system.disk.used' and m[2]]
        self.assertEquals(max([m[2] for m in disk_used]), 157843297.06666666)
        self.assertEquals(disk_used[5][3]['device_name'], '/dev/mapper/dogdev0-root')

if __name__ == '__main__':
    unittest.main()

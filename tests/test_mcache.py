import unittest
import logging
from subprocess import Popen, PIPE
import multiprocessing
from checks.db.mcache import *

class TestMemCache(unittest.TestCase):
    def setUp(self):
        self.c = Memcache(logging.getLogger(__file__))

    def _countConnections(self, port):
        pid = multiprocessing.current_process().pid
        p1 = Popen(['lsof', '-a', '-p{0}'.format(pid), '-i4'], stdout=PIPE)
        p2 = Popen(["grep", ":{0}".format(port)], stdin=p1.stdout, stdout=PIPE)
        p3 = Popen(["wc", "-l"], stdin=p2.stdout, stdout=PIPE)
        output = p3.communicate()[0]
        return int(output.strip())

    def testConnectionLeaks(self):
        for i in range(3):
            # Count open connections to localhost:11211, should be 0
            self.assertEquals(self._countConnections(11211), 0)
            r = self.c.check({"memcache_server": "localhost"})
            # Verify that the count is still 0
            self.assertEquals(self._countConnections(11211), 0)

    def testMetrics(self):
        r = self.c.check({"memcache_server": "localhost",
                           "memcache_instance_1": "localhost:11211:mytag",
                           "memcache_instance_2": "dummy:11211:myothertag",
                           "memcache_instance_3": "localhost:11211:mythirdtag"})

        self.assertEquals(len([t for t in r if t[0] == "memcache.total_items"]), 3, r)

if __name__ == '__main__':
    unittest.main()

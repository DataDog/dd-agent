import unittest
import logging
logging.basicConfig(level=logging.DEBUG)
from subprocess import Popen, PIPE
import multiprocessing
from checks.db.mcache import *

class TestMemCache(unittest.TestCase):
    def setUp(self):
        self.c = Memcache(logging.getLogger())

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
            self.c.check({"memcache_server": "localhost"})
            # Verify that the count is still 0
            self.assertEquals(self._countConnections(11211), 0)

if __name__ == '__main__':
    unittest.main()

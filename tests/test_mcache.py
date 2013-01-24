import unittest
import logging
import os
from subprocess import Popen, PIPE
from checks.db.mcache import *
from nose.plugins.skip import SkipTest

class TestMemCache(unittest.TestCase):
    def setUp(self):
        self.c = Memcache(logging.getLogger(__file__))
        self.agent_config = {
            "memcache_server": "localhost",
            "memcache_instance_1": "localhost:11211:mytag",
            "memcache_instance_2": "dummy:11211:myothertag",
            "memcache_instance_3": "localhost:11211:mythirdtag",
        }

    def _countConnections(self, port):
        pid = os.getpid()
        p1 = Popen(['lsof', '-a', '-p%s' %
            pid, '-i4'], stdout=PIPE)
        p2 = Popen(["grep", ":%s" % port], stdin=p1.stdout, stdout=PIPE)
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
        raise SkipTest("Test is not working anymore on travis boxes. Needs further investigation")
        self.c.check(self.agent_config)
        r = self.c.check(self.agent_config)

        self.assertEquals(len([t for t in r if t[0] == "memcache.total_items"]), 3, r)
        self.assertEquals(len([t for t in r if t[3].get('tags') == ["instance:mythirdtag"]]), 20, r)

    def testMemoryLeak(self):
        raise SkipTest("Test is not working anymore on travis boxes. Needs further investigation")
        self.c.check(self.agent_config)
        import gc
        gc.set_debug(gc.DEBUG_LEAK)
        try:
            start = len(gc.garbage)
            for i in range(10):
                self.c.check(self.agent_config)
            end = len(gc.garbage)
            self.assertEquals(end - start, 0, gc.garbage)
        finally:
            gc.set_debug(0)



if __name__ == '__main__':
    unittest.main()
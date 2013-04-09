import unittest
import logging
import os
import time
from subprocess import Popen, PIPE
from nose.plugins.skip import SkipTest

from tests.common import load_check


class TestMemCache(unittest.TestCase):
    def setUp(self):
        self.c = load_check('mcache', {'init_config': {}, 'instances': {}}, None)
        self.agent_config = {
            "memcache_server": "localhost",
            "memcache_instance_1": "localhost:11211:mytag",
            "memcache_instance_2": "localhost:11211:mythirdtag",
        }
        self.conf = self.c.parse_agent_config(self.agent_config)

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
            new_conf = self.c.parse_agent_config({"memcache_server": "localhost"})
            self.c.check(new_conf['instances'][0])
            # Verify that the count is still 0
            self.assertEquals(self._countConnections(11211), 0)

    def testMetrics(self):
        for instance in self.conf['instances']:
            self.c.check(instance)
            # Sleep for 1 second so the rate interval >=1
            time.sleep(1)
            self.c.check(instance)

        r = self.c.get_metrics()

        # Check that we got metrics from 3 hosts (aka all but the dummy host)
        self.assertEquals(len([t for t in r if t[0] == "memcache.total_items"]), 3, r)

        # Check that we got 21 metrics for a specific host
        self.assertEquals(len([t for t in r if t[3].get('tags') == ["instance:mythirdtag"]]), 21, r)

    def testDummyHost(self):
        new_conf = self.c.parse_agent_config({"memcache_instance_1": "dummy:11211:myothertag"})
        self.assertRaises(Exception, self.c.check, new_conf['instances'][0])

    def testMemoryLeak(self):
        # See https://github.com/DataDog/dd-agent/issues/438 for more info
        raise SkipTest('Failing on travis. See github issue #438 for more information.')
        for instance in self.conf['instances']:
            self.c.check(instance)
        self.c.get_metrics()
        time.sleep(1)

        import gc
        gc.set_debug(gc.DEBUG_LEAK)
        try:
            start = len(gc.garbage)
            for i in range(10):
                for instance in self.conf['instances']:
                    self.c.check(instance)
                self.c.get_metrics()
                time.sleep(1)

            end = len(gc.garbage)
            self.assertEquals(end - start, 0, gc.garbage)
        finally:
            gc.set_debug(0)



if __name__ == '__main__':
    unittest.main()
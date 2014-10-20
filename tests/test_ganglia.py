import logging
import unittest
import subprocess
try:
    import cProfile as profile
except ImportError:
    import profile
import pstats
import tempfile
from util import json, md5
import time
import xml.etree.ElementTree as tree
from cStringIO import StringIO

from checks.ganglia import Ganglia

TEST_FN = "tests/ganglia.txt"

class TestGanglia(unittest.TestCase):
    def testSpeed(self):
        # Pretend to be gmetad and serve a large piece of content
        server = subprocess.Popen("nc -l 8651 < %s" % TEST_FN, shell=True)
        # Wait for 1 second
        time.sleep(1)

        pfile = tempfile.NamedTemporaryFile()
        g = Ganglia(logging.getLogger(__file__))
        # Running the profiler
        # profile.runctx("g.check({'ganglia_host': 'localhost', 'ganglia_port': 8651})", {}, {"g": g}, pfile.name)
        # p = pstats.Stats(pfile.name)
        # p.sort_stats('time').print_stats()
        parsed = StringIO(g.check({'ganglia_host': 'localhost', 'ganglia_port': 8651}))
        original = open(TEST_FN)
        x1 = tree.parse(parsed)
        x2 = tree.parse(original)
        # Cursory test
        self.assertEquals([c.tag for c in x1.getroot()], [c.tag for c in x2.getroot()])


if __name__ == '__main__':
    unittest.main()

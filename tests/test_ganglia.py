import logging
import unittest
import subprocess
try:
    import cProfile as profile
except ImportError:
    import profile
import pstats
import tempfile
from hashlib import md5
from util import json
import time

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
        self.assertEquals(md5(g.check({'ganglia_host': 'localhost', 'ganglia_port': 8651})).hexdigest(), md5(open(TEST_FN).read()).hexdigest())

if __name__ == '__main__':
    unittest.main()

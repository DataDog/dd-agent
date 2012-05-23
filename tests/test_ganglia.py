import logging
logging.basicConfig()
import unittest
import subprocess
try:
    import cProfile as profile
except ImportError:
    import profile
import pstats
import tempfile
from hashlib import md5

from checks.ganglia import Ganglia

TEST_FN = "tests/ganglia.txt"

class TestGanglia(unittest.TestCase):
    def testSpeed(self, size_in_bytes=10000):
        """Pretend to be gmetad and serve a large piece of content
        """
        server = subprocess.Popen("nc -l 8651 < %s" % TEST_FN, shell=True)

        pfile = tempfile.NamedTemporaryFile()
        g = Ganglia(logging.getLogger('tests'))
        # Running the profiler
        # profile.runctx("g.check({'ganglia_host': 'localhost', 'ganglia_port': 8651})", {}, {"g": g}, pfile.name)
        # p = pstats.Stats(pfile.name)
        # p.sort_stats('time').print_stats()
        self.assertEquals(md5(g.check({'ganglia_host': 'localhost', 'ganglia_port': 8651})).hexdigest(), md5(open(TEST_FN).read()).hexdigest())

if __name__ == '__main__':
    unittest.main()

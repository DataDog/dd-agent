# stdlib
from cStringIO import StringIO
import logging
import subprocess
import time
import unittest

# 3p
import xml.etree.ElementTree as tree

# project
from checks.ganglia import Ganglia
from tests.checks.common import Fixtures


class TestGanglia(unittest.TestCase):
    def testSpeed(self):
        # Pretend to be gmetad and serve a large piece of content
        original_file = Fixtures.file('ganglia.txt')
        subprocess.Popen("nc -l 8651 < %s" % original_file, shell=True)
        # Wait for 1 second
        time.sleep(1)

        g = Ganglia(logging.getLogger(__file__))
        parsed = StringIO(g.check({'ganglia_host': 'localhost', 'ganglia_port': 8651}))
        original = Fixtures.file('ganglia.txt')
        x1 = tree.parse(parsed)
        x2 = tree.parse(original)
        # Cursory test
        self.assertEquals([c.tag for c in x1.getroot()], [c.tag for c in x2.getroot()])

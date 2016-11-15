# stdlib
import logging
import os
import unittest

# 3p
from nose.plugins.attrib import attr

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

from checks.system.unix import Cpu


@attr(requires='system')
class TestSystem(unittest.TestCase):

    def testCPU(self):
        global logger
        logger.info(os.environ['PATH'])
        cpu = Cpu(logger)
        res = cpu.check({})
        # Make sure we sum up to 100% (or 99% in the case of macs)
        assert abs(reduce(lambda a, b: a+b, res.values(), 0) - 100) <= 5, res

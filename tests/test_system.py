import unittest
import logging

logging.basicConfig()
logger = logging.getLogger()

from checks.system import *

class TestSystem(unittest.TestCase):
    def testCPU(self):
        global logger
        cpu = Cpu()
        res = cpu.check(logger, {})
        # Make sure we sum up to 100%
        assert reduce(lambda a,b:a+b, res.values(), 0) == 100, res

if __name__ == "__main__":
    unittest.main()

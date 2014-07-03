# stdlib
import unittest
import logging
import gc
import sys

# 3p
#from nose.plugins.attrib import attr

# project
import checks.system.win32 as w32

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)


AGENT_CONFIG = {} # None of the windows checks use this.

class TestWin32(unittest.TestCase):
    def _checkMemoryLeak(self, func):
        # FIXME: This should use @attr('windows')instead of checking for the
        # platform, but just importing nose.plugins.attrib causes all the tests
        # to fail with uncollected garbage.
        if sys.platform != 'win32':
            return
        gc.set_debug(gc.DEBUG_LEAK)
        try:
            start = len(gc.garbage)
            func()
            end = len(gc.garbage)
            self.assertEquals(end - start, 0, gc.garbage)
        finally:
            gc.set_debug(0)

    def testDisk(self):
        dsk = w32.Disk(log)
        self._checkMemoryLeak(lambda: dsk.check(AGENT_CONFIG))

    def testIO(self):
        io = w32.IO(log)
        self._checkMemoryLeak(lambda: io.check(AGENT_CONFIG))

    def testProcesses(self):
        proc = w32.Processes(log)
        self._checkMemoryLeak(lambda: proc.check(AGENT_CONFIG))

    def testMemory(self):
        mem = w32.Memory(log)
        self._checkMemoryLeak(lambda: mem.check(AGENT_CONFIG))

    def testNetwork(self):
        net = w32.Network(log)
        self._checkMemoryLeak(lambda: net.check(AGENT_CONFIG))

    def testCPU(self):
        cpu = w32.Cpu(log)
        self._checkMemoryLeak(lambda: cpu.check(AGENT_CONFIG))


if __name__ == "__main__":
    unittest.main()

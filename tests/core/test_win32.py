# stdlib
import gc
import logging
import unittest

# 3p
from nose.plugins.attrib import attr
import psutil

# datadog
import checks.system.win32 as w32

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)


AGENT_CONFIG = {}  # None of the windows checks use this.


@attr(requires='windows')
class TestWin32(unittest.TestCase):
    def _checkMemoryLeak(self, func):
        gc.set_debug(gc.DEBUG_LEAK)
        try:
            start = len(gc.garbage)
            func()
            end = len(gc.garbage)
            self.assertEquals(end - start, 0, gc.garbage)
        finally:
            gc.set_debug(0)

    def _checkHandleLeak(self, func, *args, **kwargs):
        """
        Runs the passed func twice and checks that the number of handles held
        by the process hasn't increased between the first and the second run
        """
        # Grab the current process
        proc = psutil.Process()

        func(*args, **kwargs)
        middle = proc.num_handles()

        func(*args, **kwargs)
        end = proc.num_handles()

        self.assertEquals(end - middle, 0)

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

    def testNoHandleLeak(self):
        io = w32.IO(log)
        proc = w32.Processes(log)
        mem = w32.Memory(log)
        net = w32.Network(log)
        cpu = w32.Cpu(log)

        self._checkHandleLeak(io.check, AGENT_CONFIG)
        self._checkHandleLeak(proc.check, AGENT_CONFIG)
        self._checkHandleLeak(mem.check, AGENT_CONFIG)
        self._checkHandleLeak(net.check, AGENT_CONFIG)
        self._checkHandleLeak(cpu.check, AGENT_CONFIG)

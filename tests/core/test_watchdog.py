# stdlib
from contextlib import contextmanager
from random import random, randrange
import os
import subprocess
import sys
import time
import unittest
import urllib as url

# 3p
from mock import patch
from nose.plugins.attrib import attr

# project
# needed because of the subprocess calls
sys.path.append(os.getcwd())
from ddagent import Application
from util import Watchdog


class WatchdogKill(Exception):
    """
    The watchdog attempted to kill the process.
    """
    pass


@attr('unix')
@attr(requires='core_integration')
class TestWatchdog(unittest.TestCase):
    """
    Test watchdog in various conditions
    """
    JITTER_FACTOR = 2

    @contextmanager
    def set_time(self, time):
        """
        Helper, a context manager to set the current time value.
        """
        # Set the current time within `util` module
        mock_time = patch("util.time.time")
        mock_time.start().return_value = time

        # Yield
        yield

        # Unset the time mock
        mock_time.stop()

    @patch.object(Watchdog, 'self_destruct', side_effect=WatchdogKill)
    def test_watchdog_frenesy_detection(self, mock_restarted):
        """
        Watchdog restarts the process on suspicious high activity.
        """
        # Limit the restart timeframe for test purpose
        Watchdog._RESTART_TIMEFRAME = 1

        # Create a watchdog with a low activity tolerancy
        process_watchdog = Watchdog(10, max_resets=3)
        ping_watchdog = process_watchdog.reset

        with self.set_time(1):
            # Can be reset 3 times within the watchdog timeframe
            for x in xrange(0, 3):
                ping_watchdog()

            # On the 4th attempt, the watchdog detects a suspicously high activity
            self.assertRaises(WatchdogKill, ping_watchdog)

        with self.set_time(3):
            # Gets back to normal when the activity timeframe expires.
            ping_watchdog()

    def test_watchdog(self):
        """
        Verify that watchdog kills ourselves even when spinning
        Verify that watchdog kills ourselves when hanging
        """
        start = time.time()
        try:
            subprocess.check_call(["python", __file__, "busy"], stderr=subprocess.STDOUT)
            raise Exception("Should have died with an error")
        except subprocess.CalledProcessError:
            duration = int(time.time() - start)
            self.assertTrue(duration < self.JITTER_FACTOR * 5)

        # Start pseudo web server
        subprocess.Popen(["nc", "-l", "31834"])
        start = time.time()
        try:
            subprocess.check_call(["python", __file__, "net"])
            raise Exception("Should have died with an error")
        except subprocess.CalledProcessError:
            duration = int(time.time() - start)
            self.assertTrue(duration < self.JITTER_FACTOR * 5)

        # Normal loop, should run 5 times
        start = time.time()
        try:
            subprocess.check_call(["python", __file__, "normal"])
            duration = int(time.time() - start)
            self.assertTrue(duration < self.JITTER_FACTOR * 5)
        except subprocess.CalledProcessError:
            self.fail("Watchdog killed normal process after %s seconds" % int(time.time() - start))

        # Fast tornado, not killed
        start = time.time()
        p = subprocess.Popen(["python", __file__, "fast"])
        p.wait()
        duration = int(time.time() - start)
        # should die as soon as flush_trs has been called
        self.assertTrue(duration < self.JITTER_FACTOR * 10)

        # Slow tornado, killed by the Watchdog
        start = time.time()
        p = subprocess.Popen(["python", __file__, "slow"])
        p.wait()
        duration = int(time.time() - start)
        self.assertTrue(duration < self.JITTER_FACTOR * 4)


class MockTxManager(object):
    def flush(self):
        "Pretend to flush for a long time"
        time.sleep(5)
        sys.exit(0)


class MemoryHogTxManager(object):
    def __init__(self, watchdog):
        self._watchdog = watchdog

    def flush(self):
        rand_data = []
        while True:
            rand_data.append('%030x' % randrange(256**15))
            self._watchdog.reset()


class PseudoAgent(object):
    """Same logic as the agent, simplified"""
    def busy_run(self):
        w = Watchdog(5)
        w.reset()
        while True:
            random()

    def hanging_net(self):
        w = Watchdog(5)
        w.reset()
        x = url.urlopen("http://localhost:31834")
        print "ERROR Net call returned", x
        return True

    def normal_run(self):
        w = Watchdog(2)
        w.reset()
        for i in range(5):
            time.sleep(1)
            w.reset()

    def slow_tornado(self):
        a = Application(12345, {"bind_host": "localhost"})
        a._watchdog = Watchdog(4)
        a._tr_manager = MockTxManager()
        a.run()

    def fast_tornado(self):
        a = Application(12345, {"bind_host": "localhost"})
        a._watchdog = Watchdog(6)
        a._tr_manager = MockTxManager()
        a.run()


if __name__ == "__main__":
    if sys.argv[1] == "busy":
        a = PseudoAgent()
        a.busy_run()
    elif sys.argv[1] == "net":
        a = PseudoAgent()
        a.hanging_net()
    elif sys.argv[1] == "normal":
        a = PseudoAgent()
        a.normal_run()
    elif sys.argv[1] == "slow":
        a = PseudoAgent()
        a.slow_tornado()
    elif sys.argv[1] == "fast":
        a = PseudoAgent()
        a.fast_tornado()
    elif sys.argv[1] == "test":
        t = TestWatchdog()
        t.runTest()
    elif sys.argv[1] == "memory":
        a = PseudoAgent()
        a.use_lots_of_memory()

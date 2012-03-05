import unittest
import subprocess
from threading import Timer
import os
import sys
from signal import SIGKILL
from random import random
import urllib as url
import time

class TestWatchdog(unittest.TestCase):
    """Test watchdog in various conditions
    """
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def runTest(self):
        """Verify that watchdog kills ourselves even when spinning
        Verify that watchdog kills ourselves when hanging
        """
        start = time.time()
        try:
            result = subprocess.check_output(["python", "test_watchdog.py", "busy"], stderr=subprocess.STDOUT)
            raise Exception("Should have died with an error")
        except subprocess.CalledProcessError:
            duration = int(time.time() - start)
            print "SUCCESS, busy loop was killed in %s seconds" % int(time.time() - start)
            self.assertEquals(duration, 5)

        # Start pseudo web server
        print "nc pid", subprocess.Popen(["nc", "-l", "31834"]).pid
        try:
            subprocess.check_call(["python", "test_watchdog.py", "net"])
            raise Exception("Should have died with an error")
        except subprocess.CalledProcessError:
            duration = int(time.time() - start)
            print "SUCCESS, hanging net was killed in %s seconds" % int(time.time() - start)
            self.assertEquals(duration, 5)

def watchdog(f):
    def selfdestruct():
        print "SUCCESS, self-destructing"
        os.kill(os.getpid(), SIGKILL)

    def wrapped(self):
        t = Timer(5, selfdestruct, [])
        t.start()
        f(self)
        t.cancel()
        print "FAILURE, did not self-destruct"
    return wrapped

    
class PseudoAgent(object):
    """Same logic as the agent, simplified"""
    @watchdog
    def busyRun(self):
        x = 0
        while True:
            x = random()

    @watchdog
    def hangingNet(self):
        x = url.urlopen("http://localhost:31834")
        print "ERROR Net call returned", x
        return True

if __name__ == "__main__":
    if sys.argv[1] == "busy":
        a = PseudoAgent()
        a.busyRun()
    elif sys.argv[1] == "net":
        a = PseudoAgent()
        a.hangingNet()
    elif sys.argv[1] == "test":
        t = TestWatchdog()
        t.runTest()

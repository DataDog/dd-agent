import unittest
from checks import AgentCheck, Check
import time
import logging
class DummyAgentCheck(AgentCheck):

    def check(self):

        self.gauge("m1", 42)
        self.gauge("m2", 42.0)
        self.gauge("m3", float('nan'))
        self.gauge("m4", float('inf'))
        self.gauge("m5", float('-inf'))
        self.rate("m6", 23)
        time.sleep(1)
        self.rate("m6", float('inf'))

        self.rate("m7", 42)
        time.sleep(1)
        self.rate("m7", 45)
        self.rate("m8", 42)
        time.sleep(1)
        self.rate("m8", float('nan'))

class DummyOldCheck(Check):

    def __init__(self):
        Check.__init__(self, logging.getLogger('dummy'))
        self.gauge("m1")
        self.gauge("m2")
        self.gauge("m3")
        self.gauge("m4")
        self.gauge("m5")
        self.counter("m6")
        self.counter("m7")
        self.counter("m8")

    def check(self):
        self.save_sample("m1", 42)
        self.save_sample("m2", 42.0)
        self.save_sample("m3", float('nan'))
        self.save_sample("m4", float('inf'))
        self.save_sample("m5", float('-inf'))
        self.save_sample("m6", 23)
        time.sleep(1)
        self.save_sample("m6", float('inf'))

        self.save_sample("m7", 42)
        time.sleep(1)
        self.save_sample("m7", 45)
        self.save_sample("m8", 42)
        time.sleep(1)
        self.save_sample("m8", float('nan'))



class TestSpecialFloatValues(unittest.TestCase):

    def test_agent_check(self):

        c = DummyAgentCheck("dummy", {}, {})
        c.check()
        m = c.get_metrics()

        self.assertTrue(len(m) == 3)
        self.assertTrue(len([k for k in m if k[0]=='m1']) == 1)
        self.assertTrue(len([k for k in m if k[0]=='m2']) == 1)
        self.assertTrue(len([k for k in m if k[0]=='m7']) == 1)

    def test_old_check(self):
        c = DummyOldCheck()
        c.check()
        m = c.get_metrics()
        self.assertTrue(len(m) == 3)
        self.assertTrue(len([k for k in m if k[0]=='m1']) == 1)
        self.assertTrue(len([k for k in m if k[0]=='m2']) == 1)
        self.assertTrue(len([k for k in m if k[0]=='m7']) == 1)



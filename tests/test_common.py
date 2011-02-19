"Tests to validate the core check logic"
import time
import unittest
from checks import *

class TestCore(unittest.TestCase):
    def setUp(self):
        self.c = Check()
        self.c.gauge("test-metric")
        self.c.counter("test-counter")

    def test_gauge(self):
        self.assertEquals(self.c.is_gauge("test-metric"), True)
        self.assertEquals(self.c.is_counter("test-metric"), False)
        self.c.save_sample("test-metric", 1.0)
        # call twice in a row, should be invariant
        self.assertEquals(self.c.get_sample("test-metric"), 1.0)
        self.assertEquals(self.c.get_sample("test-metric"), 1.0)
        self.assertEquals(self.c.get_sample_with_timestamp("test-metric")[1], 1.0)
        # new value, old one should be gone
        self.c.save_sample("test-metric", 2.0)
        self.assertEquals(self.c.get_sample("test-metric"), 2.0)
        self.assertEquals(len(self.c._sample_store["test-metric"]), 1)
        # with explicit timestamp
        self.c.save_sample("test-metric", 3.0, 1298066183.607717)
        self.assertEquals(self.c.get_sample_with_timestamp("test-metric"), (1298066183.607717, 3.0))

    def testEdgeCases(self):
        self.assertRaises(UnknownValue, self.c.get_sample, "unknown-metric")
        # same value
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(Infinity, self.c.get_sample, "test-counter")

    def test_counter(self):
        pass

    def test_samples(self):
        pass

if __name__ == '__main__':
    unittest.main()

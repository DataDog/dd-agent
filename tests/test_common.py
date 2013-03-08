import time
import unittest
import logging
logger = logging.getLogger()
from checks import Check, CheckException, UnknownValue, CheckException, Infinity
from checks.collector import Collector
from aggregator import MetricsAggregator

class TestCore(unittest.TestCase):
    "Tests to validate the core check logic"
    
    def setUp(self):
        self.c = Check(logger)
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
        self.assertEquals(self.c.get_sample_with_timestamp("test-metric"), (1298066183.607717, 3.0, None, None))
        # get_samples()
        self.assertEquals(self.c.get_samples(), {"test-metric": 3.0})

    def testEdgeCases(self):
        self.assertRaises(CheckException, self.c.get_sample, "unknown-metric")
        # same value
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(Infinity, self.c.get_sample, "test-counter")

    def test_counter(self):
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(UnknownValue, self.c.get_sample, "test-counter", expire=False)
        self.c.save_sample("test-counter", 2.0, 2.0)
        self.assertEquals(self.c.get_sample("test-counter", expire=False), 1.0)
        self.assertEquals(self.c.get_sample_with_timestamp("test-counter", expire=False), (2.0, 1.0, None, None))
        self.assertEquals(self.c.get_samples(expire=False), {"test-counter": 1.0})
        self.c.save_sample("test-counter", -2.0, 3.0)
        self.assertRaises(UnknownValue, self.c.get_sample_with_timestamp, "test-counter")

    def test_tags(self):
        # Test metric tagging
        now = int(time.time())
        # Tag metrics
        self.c.save_sample("test-counter", 1.0, 1.0, tags = ["tag1", "tag2"])
        self.c.save_sample("test-counter", 2.0, 2.0, tags = ["tag1", "tag2"])
        # Only 1 point recording for this combination of tags, won't be sent
        self.c.save_sample("test-counter", 3.0, 3.0, tags = ["tag1", "tag3"])
        self.c.save_sample("test-metric", 3.0, now, tags = ["tag3", "tag4"])
        # Arg checks
        self.assertRaises(CheckException, self.c.save_sample, "test-metric", 4.0, now + 5, tags = "abc")
        # This is a different combination of tags
        self.c.save_sample("test-metric", 3.0, now, tags = ["tag5", "tag3"])
        results = self.c.get_metrics()
        results.sort()
        self.assertEquals(results,
                          [("test-counter", 2.0, 1.0, {"tags": ["tag1", "tag2"]}),
                           ("test-metric", now, 3.0, {"tags": ["tag3", "tag4"]}),
                           ("test-metric", now, 3.0, {"tags": ["tag3", "tag5"]}),
                           ])
        # Tagged metrics are not available through get_samples anymore
        self.assertEquals(self.c.get_samples(), {})

    def test_samples(self):
        self.assertEquals(self.c.get_samples(), {})
        self.c.save_sample("test-metric", 1.0, 0.0)  # value, ts
        self.c.save_sample("test-counter", 1.0, 1.0) # value, ts
        self.c.save_sample("test-counter", 4.0, 2.0) # value, ts
        assert "test-metric"  in self.c.get_samples_with_timestamps(expire=False), self.c.get_samples_with_timestamps(expire=False)
        self.assertEquals(self.c.get_samples_with_timestamps(expire=False)["test-metric"], (0.0, 1.0, None, None))
        assert "test-counter" in self.c.get_samples_with_timestamps(expire=False), self.c.get_samples_with_timestamps(expire=False)
        self.assertEquals(self.c.get_samples_with_timestamps(expire=False)["test-counter"], (2.0, 3.0, None, None))

    def test_name(self):
        self.assertEquals(self.c.normalize("metric"), "metric")
        self.assertEquals(self.c.normalize("metric", "prefix"), "prefix.metric")
        self.assertEquals(self.c.normalize("__metric__", "prefix"), "prefix.metric")
        self.assertEquals(self.c.normalize("abc.metric(a+b+c{}/5)", "prefix"), "prefix.abc.metric_a_b_c_5")
        self.assertEquals(self.c.normalize("VBE.default(127.0.0.1,,8080).happy", "varnish"), "varnish.VBE.default_127.0.0.1_8080.happy")

    def test_metadata(self):
        c = Collector({}, None, {})
        assert "hostname" in c._get_metadata()
        assert "socket-fqdn" in c._get_metadata()
        assert "socket-hostname" in c._get_metadata()

class TestAggregator(unittest.TestCase):
    def setUp(self):
        self.aggr = MetricsAggregator('test-aggr')

    def test_dupe_tags(self):
        self.aggr.increment('test-counter', 1, tags=['a', 'b'])
        self.aggr.increment('test-counter', 1, tags=['a', 'b', 'b'])
        self.assertEquals(len(self.aggr.metrics), 1, self.aggr.metrics)
        metric = self.aggr.metrics.values()[0]
        self.assertEquals(metric.value, 2)

if __name__ == '__main__':
    unittest.main()

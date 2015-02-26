import logging
import os
import time
import unittest

from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest

from aggregator import MetricsAggregator
from checks import (
    AgentCheck,
    Check,
    CheckException,
    CheckException,
    Infinity,
    UnknownValue,
)
from checks.collector import Collector
from tests.common import load_check
from util import get_hostname

logger = logging.getLogger()

class TestCore(unittest.TestCase):
    "Tests to validate the core check logic"

    def setUp(self):
        self.c = Check(logger)
        self.c.gauge("test-metric")
        self.c.counter("test-counter")

    def setUpAgentCheck(self):
        self.ac = AgentCheck('test', {}, {'checksd_hostname': "foo"})

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

        # Same tests for the AgentCheck
        self.setUpAgentCheck()
        self.assertEquals(self.ac.normalize("metric"), "metric")
        self.assertEquals(self.ac.normalize("metric", "prefix"), "prefix.metric")
        self.assertEquals(self.ac.normalize("__metric__", "prefix"), "prefix.metric")
        self.assertEquals(self.ac.normalize("abc.metric(a+b+c{}/5)", "prefix"), "prefix.abc.metric_a_b_c_5")
        self.assertEquals(self.ac.normalize("VBE.default(127.0.0.1,,8080).happy", "varnish"), "varnish.VBE.default_127.0.0.1_8080.happy")

        self.assertEqual(self.ac.normalize("PauseTotalNs", "prefix", fix_case = True), "prefix.pause_total_ns")
        self.assertEqual(self.ac.normalize("Metric.wordThatShouldBeSeparated", "prefix", fix_case = True), "prefix.metric.word_that_should_be_separated")

    def test_metadata(self):
        c = Collector({"collect_instance_metadata": True}, None, {}, "foo")
        assert "hostname" in c._get_metadata()
        assert "socket-fqdn" in c._get_metadata()
        assert "socket-hostname" in c._get_metadata()

    def test_service_check(self):
        check_name = 'test.service_check'
        status = AgentCheck.CRITICAL
        tags = ['host:test', 'other:thing']
        host_name = 'foohost'
        timestamp = time.time()

        check = AgentCheck('test', {}, {'checksd_hostname':'foo'})
        check.service_check(check_name, status, tags, timestamp, host_name)
        self.assertEquals(len(check.service_checks), 1, check.service_checks)
        val = check.get_service_checks()
        self.assertEquals(len(val), 1)
        check_run_id = val[0].get('id', None)
        self.assertNotEquals(check_run_id, None)
        self.assertEquals([{
                    'id': check_run_id,
                    'check': check_name,
                    'status': status,
                    'host_name': host_name,
                    'tags': tags,
                    'timestamp': timestamp,
                    'message': None,
                }], val)
        self.assertEquals(len(check.service_checks), 0, check.service_checks)

    @attr(requires='sysstat')
    def test_collector(self):
        agentConfig = {
            'api_key': 'test_apikey',
            'check_timings': True,
            'collect_ec2_tags': True,
            'collect_instance_metadata': False,
            'version': 'test',
            'tags': '',
        }

        # Run a single checks.d check as part of the collector.
        redis_config = {
            "init_config": {},
            "instances": [{"host": "localhost", "port": 6379}]
        }
        checks = [load_check('redisdb', redis_config, agentConfig)]

        c = Collector(agentConfig, [], {}, get_hostname(agentConfig))
        payload = c.run({
            'initialized_checks': checks,
            'init_failed_checks': {}
        })
        metrics = payload['metrics']

        # Check that we got a timing metric for all checks.
        timing_metrics = [m for m in metrics
            if m[0] == 'datadog.agent.check_run_time']
        all_tags = []
        for metric in timing_metrics:
            all_tags.extend(metric[3]['tags'])
        for check in checks:
            tag = "check:%s" % check.name
            assert tag in all_tags, all_tags

    def test_min_collection_interval(self):
        if os.environ.get('TRAVIS', False):
            raise SkipTest('ntp server times out too often on Travis')
        config = {'instances': [{'host': '0.amazon.pool.ntp.org', 'timeout': 1}], 'init_config': {}}

        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        # default min collection interval for that check is 20sec
        check = load_check('ntp', config, agentConfig)

        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)

        check.run()
        metrics = check.get_metrics()
        # No metrics should be collected as it's too early
        self.assertEquals(len(metrics), 0, metrics)

        # equivalent to time.sleep(20)
        check.last_collection_time[0] -= 20
        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)
        check.last_collection_time[0] -= 3
        check.run()
        metrics = check.get_metrics()
        self.assertEquals(len(metrics), 0, metrics)
        check.DEFAULT_MIN_COLLECTION_INTERVAL = 0
        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)

        config = {'instances': [{'host': '0.amazon.pool.ntp.org', 'timeout': 1, 'min_collection_interval':3}], 'init_config': {}}
        check = load_check('ntp', config, agentConfig)
        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)
        check.run()
        metrics = check.get_metrics()
        self.assertEquals(len(metrics), 0, metrics)
        check.last_collection_time[0] -= 4
        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)

        config = {'instances': [{'host': '0.amazon.pool.ntp.org', 'timeout': 1, 'min_collection_interval': 12}], 'init_config': { 'min_collection_interval':3}}
        check = load_check('ntp', config, agentConfig)
        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)
        check.run()
        metrics = check.get_metrics()
        self.assertEquals(len(metrics), 0, metrics)
        check.last_collection_time[0] -= 4
        check.run()
        metrics = check.get_metrics()
        self.assertEquals(len(metrics), 0, metrics)
        check.last_collection_time[0] -= 8
        check.run()
        metrics = check.get_metrics()
        self.assertTrue(len(metrics) > 0, metrics)




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

import time
import unittest

import nose.tools as nt

from checks import AgentCheck

class TestCountType(unittest.TestCase):

    def test_count(self):
        metric = 'test.count.type.1'
        tags = ['test', 'type:count']
        hostname = 'test.host'
        device_name = 'host1'
        agent_check = AgentCheck('test_count_check', {}, {})
        counts = [0, 1, 1, 2, 3, 5, 8]
        for count in counts:
            agent_check.submit_count(metric, count,
                                     tags=tags,
                                     hostname=hostname,
                                     device_name=device_name)
        flush_ts = time.time()
        results = agent_check.get_metrics()
        nt.assert_true(results is not None)
        nt.assert_equal(1, len(results))
        result = results[0]
        ret_metric, timestamp, value = result[0], result[1], result[2]
        nt.assert_equal(metric, ret_metric, msg="Metric name is incorrect")
        nt.ok_(abs(flush_ts-timestamp) <= 1, msg="Time is off by more than a second")
        nt.assert_equal(sum(counts), value)

    def test_count_from_counter(self):
        metric = 'test.count.type.2'
        tags = ['test', 'type:count']
        hostname = 'test.host'
        device_name = 'host1'
        agent_check = AgentCheck('test_count_check', {}, {})
        counters = [0, 1, 2, 4, 7, 12, 20]
        for counter in counters:
            agent_check.count_from_counter(metric, counter, tags=tags,
                                           hostname=hostname,
                                           device_name=device_name)
        flush_ts = time.time()
        results = agent_check.get_metrics()
        nt.assert_true(results is not None)
        nt.assert_equal(1, len(results))
        result = results[0]
        ret_metric, timestamp, value = result[0], result[1], result[2]
        nt.assert_equal(metric, ret_metric, msg="Metric name is incorrect")
        nt.ok_(abs(flush_ts-timestamp) <= 1, msg="Time is off by more than a second")
        nt.assert_equal(counters[-1]-counters[0], value)
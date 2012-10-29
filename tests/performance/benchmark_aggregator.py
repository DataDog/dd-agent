"""
Performance tests for the agent/dogstatsd metrics aggregator.
"""


from aggregator import MetricsAggregator




class TestAggregatorPerf(object):

    def test_aggregation_performance(self):
        ma = MetricsAggregator('my.host')

        flush_count = 10
        loops_per_flush = 10000
        metric_count = 5

        for _ in xrange(flush_count):
            for i in xrange(loops_per_flush):
                # Counters
                for j in xrange(metric_count):
                    ma.submit_packets('counter.%s:%s|c' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h' % (j, i))
            ma.flush()


if __name__ == '__main__':
    t = TestAggregatorPerf()
    t.test_aggregation_performance()

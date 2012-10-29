"""
Performance tests for the agent/dogstatsd metrics aggregator.
"""


from aggregator import MetricsAggregator




class TestAggregatorPerf(object):

    FLUSH_COUNT = 10
    LOOPS_PER_FLUSH = 5000
    METRIC_COUNT = 5

    def test_dogstatsd_aggregation_perf(self):
        ma = MetricsAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                # Counters
                for j in xrange(self.METRIC_COUNT):
                    ma.submit_packets('counter.%s:%s|c' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h' % (j, i))
                    ma.submit_packets('set.%s:%s|s' % (j, 1.0))
            ma.flush()

    def test_checksd_aggregation_perf(self):
        ma = MetricsAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                # Counters
                for j in xrange(self.METRIC_COUNT):
                    ma.increment('counter.%s' % j, i)
                    ma.gauge('gauge.%s' % j, i)
                    ma.histogram('histogram.%s' % j, i)
                    ma.set('set.%s' % j, float(i))
            ma.flush()



if __name__ == '__main__':
    t = TestAggregatorPerf()
    t.test_dogstatsd_aggregation_perf()
    t.test_checksd_aggregation_perf()

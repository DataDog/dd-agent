"""
Performance tests for the agent/dogstatsd metrics aggregator.
"""


from aggregator import MetricsAggregator, MetricsBucketAggregator




class TestAggregatorPerf(object):

    FLUSH_COUNT = 10
    LOOPS_PER_FLUSH = 2000
    METRIC_COUNT = 5

    def test_dogstatsd_aggregation_perf(self):
        ma = MetricsBucketAggregator('my.host')

        for _ in xrange(self.FLUSH_COUNT):
            for i in xrange(self.LOOPS_PER_FLUSH):
                for j in xrange(self.METRIC_COUNT):

                    # metrics
                    ma.submit_packets('counter.%s:%s|c' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h' % (j, i))
                    ma.submit_packets('set.%s:%s|s' % (j, 1.0))

                    # tagged metrics
                    ma.submit_packets('counter.%s:%s|c|#tag1,tag2' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g|#tag1,tag2' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h|#tag1,tag2' % (j, i))
                    ma.submit_packets('set.%s:%s|s|#tag1,tag2' % (j, i))

                    # sampled metrics
                    ma.submit_packets('counter.%s:%s|c|@0.5' % (j, i))
                    ma.submit_packets('gauge.%s:%s|g|@0.5' % (j, i))
                    ma.submit_packets('histogram.%s:%s|h|@0.5' % (j, i))
                    ma.submit_packets('set.%s:%s|s|@0.5' % (j, i))

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
    #t.test_checksd_aggregation_perf()

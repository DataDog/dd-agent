# -*- coding: utf-8 -*-
# stdlib
import random
import time
import unittest

# 3p
from nose.plugins.attrib import attr
import nose.tools as nt

# project
from aggregator import DEFAULT_HISTOGRAM_AGGREGATES
from dogstatsd import MetricsBucketAggregator


@attr(requires='core_integration')
class TestUnitMetricsBucketAggregator(unittest.TestCase):
    def setUp(self):
        self.interval = 1

    @staticmethod
    def sort_metrics(metrics):
        def sort_by(m):
            return (m['metric'], ','.join(m['tags'] or []))
        return sorted(metrics, key=sort_by)

    @staticmethod
    def sort_events(metrics):
        def sort_by(m):
            return (m['msg_title'], m['msg_text'], ','.join(m.get('tags', None) or []))
        return sorted(metrics, key=sort_by)

    def sleep_for_interval_length(self, interval=None):
        time.sleep(interval or self.interval)

    def wait_for_bucket_boundary(self, interval=None):
        i = interval or self.interval
        while time.time() % i > 0.01:
            pass

    @staticmethod
    def assert_almost_equal(i, j, e=1):
        # Floating point math?
        assert abs(i - j) <= e, "%s %s %s" % (i, j, e)

    def test_counter_normalization(self):
        ag_interval = 10
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)

        # Assert counters are normalized.
        stats.submit_packets('int:1|c')
        stats.submit_packets('int:4|c')
        stats.submit_packets('int:15|c')

        stats.submit_packets('float:5|c')

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 2

        floatc, intc = metrics

        nt.assert_equal(floatc['metric'], 'float')
        nt.assert_equal(floatc['points'][0][1], 0.5)
        nt.assert_equal(floatc['host'], 'myhost')

        nt.assert_equal(intc['metric'], 'int')
        nt.assert_equal(intc['points'][0][1], 2)
        nt.assert_equal(intc['host'], 'myhost')

    def test_histogram_normalization(self):
        ag_interval = 10
        # The min is not enabled by default
        stats = MetricsBucketAggregator('myhost', interval=ag_interval,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min'])
        for i in range(5):
            stats.submit_packets('h1:1|h')
        for i in range(20):
            stats.submit_packets('h2:1|h')

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        _, _, h1count, _, _, _, _, _, h2count, _, _, _ = metrics

        nt.assert_equal(h1count['points'][0][1], 0.5)
        nt.assert_equal(h2count['points'][0][1], 2)

    def test_tags(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('gauge:1|c')
        stats.submit_packets('gauge:2|c|@1')
        stats.submit_packets('gauge:4|c|#tag1,tag2')
        stats.submit_packets('gauge:8|c|#tag2,tag1') # Should be the same as above
        stats.submit_packets('gauge:16|c|#tag3,tag4')

        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())

        assert len(metrics) == 3
        first, second, third = metrics

        nt.assert_equal(first['metric'], 'gauge')
        nt.assert_equal(first['tags'], None)
        nt.assert_equal(first['points'][0][1], 3)
        nt.assert_equal(first['host'], 'myhost')

        nt.assert_equal(second['metric'], 'gauge')
        nt.assert_equal(second['tags'], ('tag1', 'tag2'))
        nt.assert_equal(second['points'][0][1], 12)
        nt.assert_equal(second['host'], 'myhost')

        nt.assert_equal(third['metric'], 'gauge')
        nt.assert_equal(third['tags'], ('tag3', 'tag4'))
        nt.assert_equal(third['points'][0][1], 16)
        nt.assert_equal(third['host'], 'myhost')

    def test_tags_gh442(self):
        import dogstatsd
        from aggregator import api_formatter

        serialized = dogstatsd.serialize_metrics([api_formatter("foo", 12, 1, ('tag',), 'host')], "test-host")
        self.assertTrue('"tags": ["tag"]' in serialized[0], serialized)

    def test_counter(self):
        ag_interval = 1.0
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)

        # Track some counters.
        stats.submit_packets('my.first.counter:1|c')
        stats.submit_packets('my.first.counter:5|c')
        stats.submit_packets('my.second.counter:1|c')
        stats.submit_packets('my.third.counter:3|c')

        # Ensure they roll up nicely.
        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 3

        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 6)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 1)

        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 3)

        self.sleep_for_interval_length(ag_interval)
        # Ensure that counters reset to zero.
        metrics = self.sort_metrics(stats.flush())
        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 0)
        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 0)
        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 0)

    def test_empty_counter(self):
        ag_interval = self.interval
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        # Should be an empty list
        nt.assert_equals(len(metrics), 0)

        # Track some counters.
        stats.submit_packets('my.first.counter:%s|c' % (1 * ag_interval))
        # Call flush before the bucket_length has been exceeded
        metrics = self.sort_metrics(stats.flush())
        # Should be an empty list
        nt.assert_equals(len(metrics), 0)

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        # Should now have the data
        nt.assert_equals(len(metrics), 1)
        nt.assert_equals(metrics[0]['metric'], 'my.first.counter')
        nt.assert_equals(metrics[0]['points'][0][1], 1)

    def test_counter_buckets(self):
        ag_interval = 5
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)
        self.wait_for_bucket_boundary(ag_interval)

        # Track some counters.
        stats.submit_packets("my.first.counter:%s|c" % (1 * ag_interval))
        stats.submit_packets("my.second.counter:%s|c" % (1 * ag_interval))
        stats.submit_packets("my.third.counter:%s|c" % (3 * ag_interval))
        time.sleep(ag_interval)
        stats.submit_packets("my.first.counter:%s|c" % (5 * ag_interval))

        # Want to get 2 different entries for my.first.counter in one set of metrics,
        #  so wait for the time bucket interval to pass
        self.sleep_for_interval_length(ag_interval)
        # Ensure they roll up nicely.
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 6)

        first, first_b, second, second_b, third, third_b = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 1)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(first_b['metric'], 'my.first.counter')
        nt.assert_equals(first_b['points'][0][1], 5)
        nt.assert_equals(first_b['points'][0][0] - first['points'][0][0], ag_interval)

        nt.assert_equals(first['points'][0][0] % ag_interval, 0)
        nt.assert_equals(first_b['points'][0][0] % ag_interval, 0)

        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 1)
        nt.assert_equals(second_b['metric'], 'my.second.counter')
        nt.assert_equals(second_b['points'][0][1], 0)

        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 3)
        nt.assert_equals(third_b['metric'], 'my.third.counter')
        nt.assert_equals(third_b['points'][0][1], 0)

        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 0)

        self.sleep_for_interval_length(ag_interval)
        # Ensure that counters reset to zero.
        metrics = self.sort_metrics(stats.flush())
        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 0)
        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 0)
        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 0)

    def test_counter_flush_during_bucket(self):
        ag_interval = 5
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)
        self.wait_for_bucket_boundary(ag_interval)
        time.sleep(0.5)

        # Track some counters.
        stats.submit_packets("my.first.counter:%s|c" % (1 * ag_interval))
        stats.submit_packets("my.second.counter:%s|c" % (1 * ag_interval))
        stats.submit_packets("my.third.counter:%s|c" % (3 * ag_interval))
        time.sleep(ag_interval)
        stats.submit_packets("my.first.counter:%s|c" % (5 * ag_interval))

        # Want to get the date from the 2 buckets in 2 differnt calls, so don't wait for
        #  the bucket interval to pass
        metrics = self.sort_metrics(stats.flush())

        nt.assert_equals(len(metrics), 3)
        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 1)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 1)

        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 3)

        #Now wait for the bucket interval to pass, and get the other points
        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())

        nt.assert_equals(len(metrics), 3)

        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 0)

        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 0)

        self.sleep_for_interval_length(ag_interval)
        # Ensure that counters reset to zero.
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 3)
        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 0)
        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 0)
        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 0)

        self.sleep_for_interval_length(ag_interval)
        # Ensure that counters reset to zero.
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 3)
        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 0)
        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 0)
        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 0)

    def test_sampled_counter(self):
        # Submit a sampled counter.
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('sampled.counter:1|c|@0.5')
        self.sleep_for_interval_length()
        metrics = stats.flush()
        assert len(metrics) == 1
        m = metrics[0]
        assert m['metric'] == 'sampled.counter'
        nt.assert_equal(m['points'][0][1], 2)

    def test_gauge(self):
        ag_interval = 2
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)
        self.wait_for_bucket_boundary(ag_interval)

        # Track some counters.
        stats.submit_packets('my.first.gauge:1|g')
        stats.submit_packets('my.first.gauge:5|g')
        stats.submit_packets('my.second.gauge:1.5|g')

        # Ensure that gauges roll up correctly.
        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 2)

        first, second = metrics

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.gauge')
        nt.assert_equals(second['points'][0][1], 1.5)

        # Ensure that old gauges get dropped due to old timestamps
        stats.submit_metric('my.first.gauge', 5, 'g')
        stats.submit_metric('my.first.gauge', 1, 'g', timestamp=1000000000)
        stats.submit_metric('my.second.gauge', 20, 'g', timestamp=1000000000)

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 1)

        first = metrics[0]

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

    def test_gauge_buckets(self):
        # Tests calling returing data from 2 time buckets
        ag_interval = self.interval
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)
        self.wait_for_bucket_boundary(ag_interval)

        # Track some counters.
        stats.submit_packets('my.first.gauge:1|g')
        stats.submit_packets('my.first.gauge:5|g')
        stats.submit_packets('my.second.gauge:1.5|g')
        self.sleep_for_interval_length(ag_interval)
        stats.submit_packets('my.second.gauge:9.5|g')

        # Ensure that gauges roll up correctly.
        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 3)

        first, second, second_b = metrics

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second_b['metric'], 'my.second.gauge')
        nt.assert_equals(second_b['points'][0][1], 9.5)

        nt.assert_equals(second['metric'], 'my.second.gauge')
        nt.assert_equals(second['points'][0][1], 1.5)

        #check that they come back empty
        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 0)

    def test_gauge_flush_during_bucket(self):
        #Tests returning data when flush is called in the middle of a time bucket that has data
        ag_interval = self.interval
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)
        self.wait_for_bucket_boundary(ag_interval)

        # Track some counters.
        stats.submit_packets('my.first.gauge:1|g')
        stats.submit_packets('my.first.gauge:5|g')
        stats.submit_packets('my.second.gauge:1.5|g')
        self.sleep_for_interval_length(ag_interval)
        stats.submit_packets('my.second.gauge:9.5|g')

        # Ensure that gauges roll up correctly.
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 2)

        first, second = metrics

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.gauge')
        nt.assert_equals(second['points'][0][1], 1.5)


        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(len(metrics), 1)

        nt.assert_equals(second['metric'], 'my.second.gauge')
        nt.assert_equals(second['points'][0][1], 1.5)

    def test_sets(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('my.set:10|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')

        # Assert that it's treated normally.
        self.sleep_for_interval_length()
        metrics = stats.flush()

        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equal(m['metric'], 'my.set')
        nt.assert_equal(m['points'][0][1], 3)

        # Assert there are no more sets
        assert not stats.flush()

    def test_string_sets(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('my.set:string|s')
        stats.submit_packets('my.set:sets|s')
        stats.submit_packets('my.set:sets|s')
        stats.submit_packets('my.set:test|s')
        stats.submit_packets('my.set:test|s')
        stats.submit_packets('my.set:test|s')

        # Assert that it's treated normally.
        self.sleep_for_interval_length()
        metrics = stats.flush()

        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equal(m['metric'], 'my.set')
        nt.assert_equal(m['points'][0][1], 3)

        # Assert there are no more sets
        assert not stats.flush()
        self.sleep_for_interval_length()
        assert not stats.flush()

    def test_sets_buckets(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('my.set:10|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')
        self.sleep_for_interval_length()
        stats.submit_packets('my.set:40|s')

        # Assert that it's treated normally.
        self.sleep_for_interval_length()
        metrics = stats.flush()

        nt.assert_equal(len(metrics), 2)
        m, m2 = metrics
        nt.assert_equal(m['metric'], 'my.set')
        nt.assert_equal(m['points'][0][1], 3)

        nt.assert_equal(m2['metric'], 'my.set')
        nt.assert_equal(m2['points'][0][1], 1)

        # Assert there are no more sets
        assert not stats.flush()

    def test_sets_flush_during_bucket(self):
        ag_interval = self.interval
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)
        self.wait_for_bucket_boundary(ag_interval)

        stats.submit_packets('my.set:10|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')
        self.sleep_for_interval_length(ag_interval)
        stats.submit_packets('my.set:40|s')

        # Assert that it's treated normally.
        metrics = stats.flush()

        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equal(m['metric'], 'my.set')
        nt.assert_equal(m['points'][0][1], 3)

        self.sleep_for_interval_length(ag_interval)
        metrics = stats.flush()
        m = metrics[0]
        nt.assert_equal(m['metric'], 'my.set')
        nt.assert_equal(m['points'][0][1], 1)

        # Assert there are no more sets
        assert not stats.flush()

    def test_gauge_sample_rate(self):
        ag_interval = self.interval
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)

        # Submit a sampled gauge metric.
        stats.submit_packets('sampled.gauge:10|g|@0.1')

        # Assert that it's treated normally.
        self.sleep_for_interval_length(ag_interval)
        metrics = stats.flush()
        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equal(m['metric'], 'sampled.gauge')
        nt.assert_equal(m['points'][0][1], 10)

    def test_histogram(self):
        ag_interval = self.interval
        # The min is not enabled by default
        stats = MetricsBucketAggregator('myhost', interval=ag_interval,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min'])
        self.wait_for_bucket_boundary(ag_interval)

        # Sample all numbers between 1-100 many times. This
        # means our percentiles should be relatively close to themselves.
        percentiles = range(100)
        random.shuffle(percentiles) # in place
        for i in percentiles:
            for j in xrange(20):
                for type_ in ['h', 'ms']:
                    m = 'my.p:%s|%s' % (i, type_)
                    stats.submit_packets(m)

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())

        nt.assert_equal(len(metrics), 6)
        p95, pavg, pcount, pmax, pmed, pmin = self.sort_metrics(metrics)
        nt.assert_equal(p95['metric'], 'my.p.95percentile')
        self.assert_almost_equal(p95['points'][0][1], 95, 10)
        self.assert_almost_equal(pmax['points'][0][1], 99, 1)
        self.assert_almost_equal(pmed['points'][0][1], 50, 2)
        self.assert_almost_equal(pavg['points'][0][1], 50, 2)
        self.assert_almost_equal(pmin['points'][0][1], 1, 1)
        nt.assert_equals(pcount['points'][0][1], 4000) # 100 * 20 * 2
        nt.assert_equals(p95['host'], 'myhost')

        # Ensure that histograms are reset.
        metrics = self.sort_metrics(stats.flush())
        assert not metrics


    def test_sampled_histogram(self):
        # Submit a sampled histogram.
        # The min is not enabled by default
        stats = MetricsBucketAggregator(
            'myhost',
            interval=self.interval,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min']
        )
        stats.submit_packets('sampled.hist:5|h|@0.5')


        # Assert we scale up properly.
        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        p95, pavg, pcount, pmax, pmed, pmin = self.sort_metrics(metrics)

        nt.assert_equal(pcount['points'][0][1], 2)
        for p in [p95, pavg, pmed, pmax, pmin]:
            nt.assert_equal(p['points'][0][1], 5)

    def test_histogram_buckets(self):
        ag_interval = 1
        # The min is not enabled by default
        stats = MetricsBucketAggregator('myhost', interval=ag_interval,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min'])

        # Sample all numbers between 1-100 many times. This
        # means our percentiles should be relatively close to themselves.
        self.wait_for_bucket_boundary(ag_interval)
        percentiles = range(100)
        random.shuffle(percentiles) # in place
        for i in percentiles:
            for j in xrange(20):
                for type_ in ['h', 'ms']:
                    m = 'my.p:%s|%s' % (i, type_)
                    stats.submit_packets(m)

        self.wait_for_bucket_boundary(ag_interval)
        percentiles = range(50)
        random.shuffle(percentiles) # in place
        for i in percentiles:
            for j in xrange(20):
                for type_ in ['h', 'ms']:
                    m = 'my.p:%s|%s' % (i, type_)
                    stats.submit_packets(m)

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())

        nt.assert_equal(len(metrics), 12)
        p95, p95_b, pavg, pavg_b, pcount, pcount_b, pmax, pmax_b, pmed, pmed_b, pmin, pmin_b = self.sort_metrics(metrics)
        nt.assert_equal(p95['metric'], 'my.p.95percentile')
        self.assert_almost_equal(p95['points'][0][1], 95, 10)
        self.assert_almost_equal(pmax['points'][0][1], 99, 1)
        self.assert_almost_equal(pmed['points'][0][1], 50, 2)
        self.assert_almost_equal(pavg['points'][0][1], 50, 2)
        self.assert_almost_equal(pmin['points'][0][1], 1, 1)
        nt.assert_equals(pcount['points'][0][1], 4000) # 100 * 20 * 2

        nt.assert_equal(p95_b['metric'], 'my.p.95percentile')
        self.assert_almost_equal(p95_b['points'][0][1], 47, 10)
        self.assert_almost_equal(pmax_b['points'][0][1], 49, 1)
        self.assert_almost_equal(pmed_b['points'][0][1], 25, 2)
        self.assert_almost_equal(pavg_b['points'][0][1], 25, 2)
        self.assert_almost_equal(pmin_b['points'][0][1], 1, 1)
        nt.assert_equals(pcount_b['points'][0][1], 2000) # 100 * 20 * 2

        nt.assert_equals(p95['host'], 'myhost')

        # Ensure that histograms are reset.
        metrics = self.sort_metrics(stats.flush())
        assert not metrics
        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        assert not metrics


    def test_histogram_flush_during_bucket(self):
        ag_interval = 1
        # The min is not enabled by default
        stats = MetricsBucketAggregator('myhost', interval=ag_interval,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min'])

        # Sample all numbers between 1-100 many times. This
        # means our percentiles should be relatively close to themselves.
        self.wait_for_bucket_boundary(ag_interval)
        percentiles = range(100)
        random.shuffle(percentiles) # in place
        for i in percentiles:
            for j in xrange(20):
                for type_ in ['h', 'ms']:
                    m = 'my.p:%s|%s' % (i, type_)
                    stats.submit_packets(m)

        self.wait_for_bucket_boundary(ag_interval)
        percentiles = range(50)
        random.shuffle(percentiles) # in place
        for i in percentiles:
            for j in xrange(20):
                for type_ in ['h', 'ms']:
                    m = 'my.p:%s|%s' % (i, type_)
                    stats.submit_packets(m)

        metrics = self.sort_metrics(stats.flush())

        nt.assert_equal(len(metrics), 6)
        p95, pavg, pcount, pmax, pmed, pmin = self.sort_metrics(metrics)
        nt.assert_equal(p95['metric'], 'my.p.95percentile')
        self.assert_almost_equal(p95['points'][0][1], 95, 10)
        self.assert_almost_equal(pmax['points'][0][1], 99, 1)
        self.assert_almost_equal(pmed['points'][0][1], 50, 2)
        self.assert_almost_equal(pavg['points'][0][1], 50, 2)
        self.assert_almost_equal(pmin['points'][0][1], 1, 1)
        nt.assert_equal(pcount['points'][0][1], 4000) # 100 * 20 * 2
        nt.assert_equals(p95['host'], 'myhost')

        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 6)
        p95_b, pavg_b, pcount_b, pmax_b, pmed_b, pmin_b = self.sort_metrics(metrics)
        nt.assert_equal(p95_b['metric'], 'my.p.95percentile')
        self.assert_almost_equal(p95_b['points'][0][1], 47, 10)
        self.assert_almost_equal(pmax_b['points'][0][1], 49, 1)
        self.assert_almost_equal(pmed_b['points'][0][1], 25, 2)
        self.assert_almost_equal(pavg_b['points'][0][1], 25, 2)
        self.assert_almost_equal(pmin_b['points'][0][1], 1, 1)
        nt.assert_equals(pcount_b['points'][0][1], 2000) # 100 * 20 * 2

        # Ensure that histograms are reset.
        metrics = self.sort_metrics(stats.flush())
        assert not metrics

    def test_batch_submission(self):
        # Submit a sampled histogram.
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        metrics = [
            'counter:1|c',
            'counter:1|c',
            'gauge:1|g'
        ]
        packet = "\n".join(metrics)
        stats.submit_packets(packet)

        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(2, len(metrics))
        counter, gauge = metrics
        assert counter['points'][0][1] == 2
        assert gauge['points'][0][1] == 1


    def test_bad_packets_throw_errors(self):
        packets = [
            'missing.value.and.type',
            'missing.type:2',
            'missing.value|c',
            '2|c',
            'unknown.type:2|z',
            'string.value:abc|c',
            'string.sample.rate:0|c|@abc',
            # Bad event-like packets
            '_ev{1,2}:bad_header'
            '_e{1,}:invalid|headers',
            '_e:missing|size|headers',
            '_e:{1,1}:t|t|t:bad_meta|h',
        ]

        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        for packet in packets:
            try:
                stats.submit_packets(packet)
            except Exception:
                assert True
            else:
                assert False, 'invalid : %s' % packet

    def test_metrics_expiry(self):
        # Ensure metrics eventually expire and stop submitting.
        ag_interval = self.interval
        expiry = ag_interval * 5 + 2
        # The min is not enabled by default
        stats = MetricsBucketAggregator('myhost', interval=ag_interval,
            expiry_seconds=expiry,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min'])
        stats.submit_packets('test.counter:123|c')
        stats.submit_packets('test.gauge:55|g')
        stats.submit_packets('test.set:44|s')
        stats.submit_packets('test.histogram:11|h')
        submit_time = time.time()
        submit_bucket_timestamp = submit_time - (submit_time % ag_interval)

        # Ensure points keep submitting
        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 9)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 123)
        nt.assert_equal(metrics[0]['points'][0][0], submit_bucket_timestamp)

        #flush without waiting - should get nothing
        metrics = self.sort_metrics(stats.flush())
        assert not metrics, str(metrics)

        #Don't sumbit anything
        submit_time = time.time()
        bucket_timestamp = submit_time - (submit_time % ag_interval)

        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 1)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 0)
        nt.assert_equal(metrics[0]['points'][0][0], bucket_timestamp)

        stats.submit_packets('test.gauge:5|g')
        self.sleep_for_interval_length()
        time.sleep(0.3)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 2)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 0)
        nt.assert_equal(metrics[1]['metric'], 'test.gauge')
        nt.assert_equal(metrics[1]['points'][0][1], 5)

        #flush without waiting - should get nothing
        metrics = self.sort_metrics(stats.flush())
        assert not metrics, str(metrics)

        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())

        nt.assert_equal(len(metrics), 1)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 0)

        # Now sleep for longer than the expiry window and ensure
        # no points are submitted
        self.sleep_for_interval_length()
        time.sleep(2)
        m = stats.flush()
        assert not m, str(m)

        # If we submit again, we're all good.
        stats.submit_packets('test.counter:123|c')
        stats.submit_packets('test.gauge:55|g')
        stats.submit_packets('test.set:44|s')
        stats.submit_packets('test.histogram:11|h')
        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 9)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 123)


    def test_diagnostic_stats(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        for i in xrange(10):
            stats.submit_packets('metric:10|c')
        stats.send_packet_count('datadog.dogstatsd.packet.count')

        self.sleep_for_interval_length()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(2, len(metrics))
        first, second = metrics

        nt.assert_equal(first['metric'], 'datadog.dogstatsd.packet.count')
        nt.assert_equal(first['points'][0][1], 10)

    def test_histogram_counter(self):
        # Test whether histogram.count == increment
        # same deal with a sample rate
        ag_interval = self.interval
        cnt = 100000
        for run in [1, 2]:
            stats = MetricsBucketAggregator('myhost', interval=ag_interval)
            for i in xrange(cnt):
                if run == 2:
                    stats.submit_packets('test.counter:1|c|@0.5')
                    stats.submit_packets('test.hist:1|ms|@0.5')
                else:
                    stats.submit_packets('test.counter:1|c')
                    stats.submit_packets('test.hist:1|ms')
            self.sleep_for_interval_length(ag_interval)
            metrics = self.sort_metrics(stats.flush())
            assert len(metrics) > 0

            #depending on timing, some runs may return the metric more that one bucket, meaning there may be
            # more than one 'metric' for each of the counters
            counter_count = 0
            hist_count = 0
            for num in [m['points'][0][1] for m in metrics if m['metric'] == 'test.counter']:
                counter_count += num
            for num in [m['points'][0][1] for m in metrics if m['metric'] == 'test.hist.count']:
                hist_count += num

            nt.assert_equal(counter_count, cnt * run)
            nt.assert_equal(hist_count, cnt * run)

    def test_scientific_notation(self):
        ag_interval = 10
        stats = MetricsBucketAggregator('myhost', interval=ag_interval)

        stats.submit_packets('test.scinot:9.512901e-05|g')
        self.sleep_for_interval_length(ag_interval)

        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 1
        ts, val = metrics[0].get('points')[0]
        nt.assert_almost_equal(val, 9.512901e-05)

    def test_event_tags(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('_e{6,4}:title1|text')
        stats.submit_packets('_e{6,4}:title2|text|#t1')
        stats.submit_packets('_e{6,4}:title3|text|#t1,t2:v2,t3,t4')
        stats.submit_packets('_e{6,4}:title4|text|k:key|p:normal|#t1,t2')

        events = self.sort_events(stats.flush_events())

        assert len(events) == 4
        first, second, third, fourth = events

        try:
            first['tags']
        except Exception:
            assert True
        else:
            assert False, "event['tags'] shouldn't be defined when no tags aren't explicited in the packet"
        nt.assert_equal(first['msg_title'], 'title1')
        nt.assert_equal(first['msg_text'], 'text')

        nt.assert_equal(second['msg_title'], 'title2')
        nt.assert_equal(second['msg_text'], 'text')
        nt.assert_equal(second['tags'], sorted(['t1']))

        nt.assert_equal(third['msg_title'], 'title3')
        nt.assert_equal(third['msg_text'], 'text')
        nt.assert_equal(third['tags'], sorted(['t1', 't2:v2', 't3', 't4']))

        nt.assert_equal(fourth['msg_title'], 'title4')
        nt.assert_equal(fourth['msg_text'], 'text')
        nt.assert_equal(fourth['aggregation_key'], 'key')
        nt.assert_equal(fourth['priority'], 'normal')
        nt.assert_equal(fourth['tags'], sorted(['t1', 't2']))

    def test_event_title(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('_e{0,4}:|text')
        stats.submit_packets(u'_e{9,4}:2intitulé|text')
        stats.submit_packets('_e{14,4}:3title content|text')
        stats.submit_packets('_e{14,4}:4title|content|text')
        stats.submit_packets('_e{13,4}:5title\\ntitle|text') # \n stays escaped

        events = self.sort_events(stats.flush_events())

        assert len(events) == 5
        first, second, third, fourth, fifth = events

        nt.assert_equal(first['msg_title'], '')
        nt.assert_equal(second['msg_title'], u'2intitulé')
        nt.assert_equal(third['msg_title'], '3title content')
        nt.assert_equal(fourth['msg_title'], '4title|content')
        nt.assert_equal(fifth['msg_title'], '5title\\ntitle')

    def test_event_text(self):
        stats = MetricsBucketAggregator('myhost', interval=self.interval)
        stats.submit_packets('_e{2,0}:t1|')
        stats.submit_packets('_e{2,12}:t2|text|content')
        stats.submit_packets('_e{2,23}:t3|First line\\nSecond line') # \n is a newline
        stats.submit_packets(u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪') # utf-8 compliant

        events = self.sort_events(stats.flush_events())

        assert len(events) == 4
        first, second, third, fourth = events

        nt.assert_equal(first['msg_text'], '')
        nt.assert_equal(second['msg_text'], 'text|content')
        nt.assert_equal(third['msg_text'], 'First line\nSecond line')
        nt.assert_equal(fourth['msg_text'], u'♬ †øU †øU ¥ºu T0µ ♪')

    def test_recent_point_threshold(self):
        ag_interval = 1
        threshold = 100
        # The min is not enabled by default
        stats = MetricsBucketAggregator(
            'myhost',
            recent_point_threshold=threshold,
            interval=ag_interval,
            histogram_aggregates=DEFAULT_HISTOGRAM_AGGREGATES+['min']
        )
        timestamp_beyond_threshold = time.time() - threshold*2

        # Ensure that old gauges get dropped due to old timestamps
        stats.submit_metric('my.first.gauge', 5, 'g')
        stats.submit_metric('my.first.gauge', 1, 'g', timestamp=timestamp_beyond_threshold)
        stats.submit_metric('my.second.gauge', 20, 'g', timestamp=timestamp_beyond_threshold)

        self.sleep_for_interval_length(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 1

        first = metrics[0]
        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        timestamp_within_threshold = time.time() - threshold/2
        bucket_for_timestamp_within_threshold = timestamp_within_threshold - (timestamp_within_threshold % ag_interval)
        stats.submit_metric('my.1.gauge', 5, 'g')
        stats.submit_metric('my.1.gauge', 1, 'g', timestamp=timestamp_within_threshold)
        stats.submit_metric('my.2.counter', 20, 'c', timestamp=timestamp_within_threshold)
        stats.submit_metric('my.3.set', 20, 's', timestamp=timestamp_within_threshold)
        stats.submit_metric('my.4.histogram', 20, 'h', timestamp=timestamp_within_threshold)

        self.sleep_for_interval_length(ag_interval)
        flush_timestamp = time.time()
        # The bucket timestamp is the beginning of the bucket that ended before we flushed
        bucket_timestamp = flush_timestamp - (flush_timestamp % ag_interval) - ag_interval
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 11)

        first, first_b, second, second_b, third, h1, h2, h3, h4, h5, h6 = metrics
        nt.assert_equals(first['metric'], 'my.1.gauge')
        nt.assert_equals(first['points'][0][1], 1)
        nt.assert_equals(first['host'], 'myhost')
        self.assert_almost_equal(first['points'][0][0], bucket_for_timestamp_within_threshold, 0.1)
        nt.assert_equals(first_b['metric'], 'my.1.gauge')
        nt.assert_equals(first_b['points'][0][1], 5)
        self.assert_almost_equal(first_b['points'][0][0], bucket_timestamp, 0.1)

        nt.assert_equals(second['metric'], 'my.2.counter')
        nt.assert_equals(second['points'][0][1], 20)
        self.assert_almost_equal(second['points'][0][0], bucket_for_timestamp_within_threshold, 0.1)
        nt.assert_equals(second_b['metric'], 'my.2.counter')
        nt.assert_equals(second_b['points'][0][1], 0)
        self.assert_almost_equal(second_b['points'][0][0], bucket_timestamp, 0.1)

        nt.assert_equals(third['metric'], 'my.3.set')
        nt.assert_equals(third['points'][0][1], 1)
        self.assert_almost_equal(third['points'][0][0], bucket_for_timestamp_within_threshold, 0.1)

        nt.assert_equals(h1['metric'], 'my.4.histogram.95percentile')
        nt.assert_equals(h1['points'][0][1], 20)
        self.assert_almost_equal(h1['points'][0][0], bucket_for_timestamp_within_threshold, 0.1)
        nt.assert_equal(h1['points'][0][0], h2['points'][0][0])
        nt.assert_equal(h1['points'][0][0], h3['points'][0][0])
        nt.assert_equal(h1['points'][0][0], h4['points'][0][0])
        nt.assert_equal(h1['points'][0][0], h5['points'][0][0])

    def test_calculate_bucket_start(self):
        stats = MetricsBucketAggregator('myhost', interval=10)
        nt.assert_equal(stats.calculate_bucket_start(13284283), 13284280)
        nt.assert_equal(stats.calculate_bucket_start(13284280), 13284280)
        stats = MetricsBucketAggregator('myhost', interval=5)
        nt.assert_equal(stats.calculate_bucket_start(13284287), 13284285)
        nt.assert_equal(stats.calculate_bucket_start(13284280), 13284280)

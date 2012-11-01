
import random
import time

import nose.tools as nt

from dogstatsd import MetricsAggregator


class TestUnitDogStatsd(object):

    @staticmethod
    def sort_metrics(metrics):
        def sort_by(m):
            return (m['metric'],  ','.join(m['tags'] or []))
        return sorted(metrics, key=sort_by)

    def test_tags(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('gauge:1|c')
        stats.submit_packets('gauge:2|c|@1')
        stats.submit_packets('gauge:4|c|#tag1,tag2')
        stats.submit_packets('gauge:8|c|#tag2,tag1') # Should be the same as above
        stats.submit_packets('gauge:16|c|#tag3,tag4')

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


    def test_counter(self):
        stats = MetricsAggregator('myhost')

        # Track some counters.
        stats.submit_packets('my.first.counter:1|c')
        stats.submit_packets('my.first.counter:5|c')
        stats.submit_packets('my.second.counter:1|c')
        stats.submit_packets('my.third.counter:3|c')

        # Ensure they roll up nicely.
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

        # Ensure that counters reset to zero.
        metrics = self.sort_metrics(stats.flush())
        first, second, third = metrics
        nt.assert_equals(first['metric'], 'my.first.counter')
        nt.assert_equals(first['points'][0][1], 0)
        nt.assert_equals(second['metric'], 'my.second.counter')
        nt.assert_equals(second['points'][0][1], 0)
        nt.assert_equals(third['metric'], 'my.third.counter')
        nt.assert_equals(third['points'][0][1], 0)


    def test_sampled_counter(self):

        # Submit a sampled counter.
        stats = MetricsAggregator('myhost')
        stats.submit_packets('sampled.counter:1|c|@0.5')
        metrics = stats.flush()
        assert len(metrics) == 1
        m = metrics[0]
        assert m['metric'] == 'sampled.counter'
        nt.assert_equal(m['points'][0][1], 2)

    def test_gauge(self):
        stats = MetricsAggregator('myhost')

        # Track some counters.
        stats.submit_packets('my.first.gauge:1|g')
        stats.submit_packets('my.first.gauge:5|g')
        stats.submit_packets('my.second.gauge:1.5|g')

        # Ensure that gauges roll up correctly.
        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 2

        first, second = metrics

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.gauge')
        nt.assert_equals(second['points'][0][1], 1.5)


    def test_sets(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('my.set:10|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:20|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')
        stats.submit_packets('my.set:30|s')

        # Assert that it's treated normally.
        metrics = stats.flush()
        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equal(m['metric'], 'my.set')
        nt.assert_equal(m['points'][0][1], 3)

        # Assert there are no more sets
        assert not stats.flush()


    def test_rate(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('my.rate:10|_dd-r')
        # Sleep 1 second so the time interval > 0
        time.sleep(1)
        stats.submit_packets('my.rate:40|_dd-r')

        # Check that the rate is calculated correctly
        metrics = stats.flush()
        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equals(m['metric'], 'my.rate')
        nt.assert_equals(m['points'][0][1], 30)

        # Assert that no more rates are given
        assert not stats.flush()

    def test_gauge_sample_rate(self):
        stats = MetricsAggregator('myhost')

        # Submit a sampled gauge metric.
        stats.submit_packets('sampled.gauge:10|g|@0.1')

        # Assert that it's treated normally.
        metrics = stats.flush()
        nt.assert_equal(len(metrics), 1)
        m = metrics[0]
        nt.assert_equal(m['metric'], 'sampled.gauge')
        nt.assert_equal(m['points'][0][1], 10)

    def test_histogram(self):
        stats = MetricsAggregator('myhost')

        # Sample all numbers between 1-100 many times. This
        # means our percentiles should be relatively close to themselves.
        percentiles = range(100)
        random.shuffle(percentiles) # in place
        for i in percentiles:
            for j in xrange(20):
                for type_ in ['h', 'ms']:
                    m = 'my.p:%s|%s' % (i, type_)
                    stats.submit_packets(m)

        metrics = self.sort_metrics(stats.flush())

        def assert_almost_equal(i, j, e=1):
            # Floating point math?
            assert abs(i - j) <= e, "%s %s %s" % (i, j, e)

        nt.assert_equal(len(metrics), 5)
        p95, pavg, pcount, pmax, pmed = self.sort_metrics(metrics)
        nt.assert_equal(p95['metric'], 'my.p.95percentile')
        assert_almost_equal(p95['points'][0][1], 95, 10)
        assert_almost_equal(pmax['points'][0][1], 99, 1)
        assert_almost_equal(pmed['points'][0][1], 50, 2)
        assert_almost_equal(pavg['points'][0][1], 50, 2)
        assert_almost_equal(pcount['points'][0][1], 4000, 0) # 100 * 20 * 2
        nt.assert_equals(p95['host'], 'myhost')

        # Ensure that histograms are reset.
        metrics = self.sort_metrics(stats.flush())
        assert not metrics


    def test_sampled_histogram(self):
        # Submit a sampled histogram.
        stats = MetricsAggregator('myhost')
        stats.submit_packets('sampled.hist:5|h|@0.5')


        # Assert we scale up properly.
        metrics = self.sort_metrics(stats.flush())
        p95, pavg, pcount, pmax, pmed = self.sort_metrics(metrics)

        nt.assert_equal(pcount['points'][0][1], 2)
        for p in [p95, pavg, pmed, pmax]:
            nt.assert_equal(p['points'][0][1], 5)

    def test_batch_submission(self):
        # Submit a sampled histogram.
        stats = MetricsAggregator('myhost')
        metrics = [
            'counter:1|c',
            'counter:1|c',
            'gauge:1|g'
        ]
        packet = "\n".join(metrics)
        stats.submit_packets(packet)

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
        ]

        stats = MetricsAggregator('myhost')
        for packet in packets:
            try:
                stats.submit_packets(packet)
            except:
                assert True
            else:
                assert False, 'invalid : %s' % packet

    def test_metrics_expiry(self):
        # Ensure metrics eventually expire and stop submitting.
        stats = MetricsAggregator('myhost', expiry_seconds=1)
        stats.submit_packets('test.counter:123|c')

        # Ensure points keep submitting
        assert stats.flush()
        assert stats.flush()
        time.sleep(0.5)
        assert stats.flush()

        # Now sleep for longer than the expiry window and ensure
        # no points are submitted
        time.sleep(2)
        m = stats.flush()
        assert not m, str(m)

        # If we submit again, we're all good.
        stats.submit_packets('test.counter:123|c')
        assert stats.flush()


    def test_diagnostic_stats(self):
        stats = MetricsAggregator('myhost')
        for i in xrange(10):
            stats.submit_packets('metric:10|c')
        stats.send_packet_count('datadog.dogstatsd.packet.count')
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equals(2, len(metrics))
        first, second = metrics

        nt.assert_equal(first['metric'], 'datadog.dogstatsd.packet.count')
        nt.assert_equal(first['points'][0][1], 10)

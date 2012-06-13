
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
        stats.submit('gauge:1|c')
        stats.submit('gauge:2|c|@1')
        stats.submit('gauge:4|c|#tag1,tag2')
        stats.submit('gauge:8|c|#tag2,tag1') # Should be the same as above
        stats.submit('gauge:16|c|#tag3,tag4')

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
        stats.submit('my.first.counter:1|c')
        stats.submit('my.first.counter:5|c')
        stats.submit('my.second.counter:1|c')
        stats.submit('my.third.counter:3|c')

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

        # Ensure they're gone now.
        assert not len(stats.flush())

    def test_sampled_counter(self):

        # Submit a sampled counter.
        stats = MetricsAggregator('myhost')
        stats.submit('sampled.counter:1|c|@0.5')
        metrics = stats.flush()
        assert len(metrics) == 1
        m = metrics[0]
        assert m['metric'] == 'sampled.counter'
        nt.assert_equal(m['points'][0][1], 2)

    def test_gauge(self):
        stats = MetricsAggregator('myhost')

        # Track some counters.
        stats.submit('my.first.gauge:1|g')
        stats.submit('my.first.gauge:5|g')
        stats.submit('my.second.gauge:1.5|g')

        # Ensure they roll up nicely.
        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 2

        first, second = metrics

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        nt.assert_equals(second['metric'], 'my.second.gauge')
        nt.assert_equals(second['points'][0][1], 1.5)


        # Ensure they shall be flushed no more.
        metrics = stats.flush()
        assert not len(metrics)

    def test_gauge_sample_rate(self):
        stats = MetricsAggregator('myhost')

        # Submit a sampled gauge metric.
        stats.submit('sampled.gauge:10|g|@0.1')

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
                    stats.submit(m)

        metrics = self.sort_metrics(stats.flush())

        def assert_almost_equal(i, j, e=1):
            # Floating point math?
            assert abs(i - j) <= e, "%s %s %s" % (i, j, e)
        nt.assert_equal(len(metrics), 8)
        p75, p85, p95, p99, pavg, pcount, pmax, pmin = self.sort_metrics(metrics)
        nt.assert_equal(p75['metric'], 'my.p.75percentile')
        assert_almost_equal(p75['points'][0][1], 75, 10)
        assert_almost_equal(p85['points'][0][1], 85, 10)
        assert_almost_equal(p95['points'][0][1], 95, 10)
        assert_almost_equal(p99['points'][0][1], 99, 10)
        assert_almost_equal(pavg['points'][0][1], 50, 2)
        assert_almost_equal(pmax['points'][0][1], 99, 1)
        assert_almost_equal(pmin['points'][0][1], 0, 1)
        assert_almost_equal(pcount['points'][0][1], 4000, 0) # 100 * 20 * 2
        nt.assert_equals(p75['host'], 'myhost')

    def test_sampled_histogram(self):
        # Submit a sampled histogram.
        stats = MetricsAggregator('myhost')
        stats.submit('sampled.hist:5|h|@0.5')

        # Assert we scale up properly.
        metrics = self.sort_metrics(stats.flush())
        p75, p85, p95, p99, pavg, pcount, pmin, pmax = self.sort_metrics(metrics)

        nt.assert_equal(pcount['points'][0][1], 2)
        for p in [p75, p85, p99, pavg, pmin, pmax]:
            nt.assert_equal(p['points'][0][1], 5)


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
                stats.submit(packet)
            except:
                assert True
            else:
                assert False, 'invalid : %s' % packet




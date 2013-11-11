# -*- coding: utf-8 -*-
import random
import time

import unittest
import nose.tools as nt

from dogstatsd import MetricsAggregator


class TestUnitDogStatsd(unittest.TestCase):

    @staticmethod
    def sort_metrics(metrics):
        def sort_by(m):
            return (m['metric'],  ','.join(m['tags'] or []))
        return sorted(metrics, key=sort_by)

    @staticmethod
    def sort_events(metrics):
        def sort_by(m):
            return (m['title'], m['text'],  ','.join(m.get('tags', None) or []))
        return sorted(metrics, key=sort_by)

    def test_counter_normalization(self):
        stats = MetricsAggregator('myhost', interval=10)

        # Assert counters are normalized.
        stats.submit_packets('int:1|c')
        stats.submit_packets('int:4|c')
        stats.submit_packets('int:15|c')

        stats.submit_packets('float:5|c')


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
        stats = MetricsAggregator('myhost', interval=10)
        for i in range(5):
            stats.submit_packets('h1:1|h')
        for i in range(20):
            stats.submit_packets('h2:1|h')

        metrics = self.sort_metrics(stats.flush())
        _, _, h1count, _, _, \
        _, _, h2count, _, _ = metrics

        nt.assert_equal(h1count['points'][0][1], 0.5)
        nt.assert_equal(h2count['points'][0][1], 2)


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

    def test_tags_gh442(self):
        import util
        import dogstatsd
        from aggregator import api_formatter

        json = util.generate_minjson_adapter()
        dogstatsd.json = json
        serialized = dogstatsd.serialize_metrics([api_formatter("foo", 12, 1, ('tag',), 'host')])
        assert '"tags": ["tag"]' in serialized

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

        # Ensure that old gauges get dropped due to old timestamps
        stats.gauge('my.first.gauge', 5)
        stats.gauge('my.first.gauge', 1, timestamp=1000000000)
        stats.gauge('my.second.gauge', 20, timestamp=1000000000)

        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 1

        first = metrics[0]

        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

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

    def test_string_sets(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('my.set:string|s')
        stats.submit_packets('my.set:sets|s')
        stats.submit_packets('my.set:sets|s')
        stats.submit_packets('my.set:test|s')
        stats.submit_packets('my.set:test|s')
        stats.submit_packets('my.set:test|s')

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
            # Bad event-like packets
            '_ev{1,2}:bad_header'
            '_e{1,}:invalid|headers',
            '_e:missing|size|headers',
            '_e:{1,1}:t|t|t:bad_meta|h',
        ]

        stats = MetricsAggregator('myhost')
        for packet in packets:
            try:
                stats.submit_packets(packet)
            except Exception:
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

    def test_histogram_counter(self):
        # Test whether histogram.count == increment
        # same deal with a sample rate
        cnt = 100000
        for run in [1, 2]:
            stats = MetricsAggregator('myhost')
            for i in xrange(cnt):
                if run == 2:
                    stats.submit_packets('test.counter:1|c|@0.5')
                    stats.submit_packets('test.hist:1|ms|@0.5')
                else:
                    stats.submit_packets('test.counter:1|c')
                    stats.submit_packets('test.hist:1|ms')
            metrics = self.sort_metrics(stats.flush())
            assert len(metrics) > 0

            nt.assert_equal([m['points'][0][1] for m in metrics if m['metric'] == 'test.counter'], [cnt * run])
            nt.assert_equal([m['points'][0][1] for m in metrics if m['metric'] == 'test.hist.count'], [cnt * run])

    def test_scientific_notation(self):
        stats = MetricsAggregator('myhost', interval=10)

        stats.submit_packets('test.scinot:9.512901e-05|g')
        metrics = self.sort_metrics(stats.flush())

        assert len(metrics) == 1
        ts, val = metrics[0].get('points')[0]
        nt.assert_almost_equal(val, 9.512901e-05)

    def test_event_tags(self):
        stats = MetricsAggregator('myhost')
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
        nt.assert_equal(first['title'], 'title1')
        nt.assert_equal(first['text'], 'text')

        nt.assert_equal(second['title'], 'title2')
        nt.assert_equal(second['text'], 'text')
        nt.assert_equal(second['tags'], sorted(['t1']))

        nt.assert_equal(third['title'], 'title3')
        nt.assert_equal(third['text'], 'text')
        nt.assert_equal(third['tags'], sorted(['t1', 't2:v2', 't3', 't4']))

        nt.assert_equal(fourth['title'], 'title4')
        nt.assert_equal(fourth['text'], 'text')
        nt.assert_equal(fourth['aggregation_key'], 'key')
        nt.assert_equal(fourth['priority'], 'normal')
        nt.assert_equal(fourth['tags'], sorted(['t1', 't2']))

    def test_event_title(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('_e{0,4}:|text')
        stats.submit_packets(u'_e{9,4}:2intitulé|text')
        stats.submit_packets('_e{14,4}:3title content|text')
        stats.submit_packets('_e{14,4}:4title|content|text')
        stats.submit_packets('_e{13,4}:5title\\ntitle|text') # \n stays escaped

        events = self.sort_events(stats.flush_events())

        assert len(events) == 5
        first, second, third, fourth, fifth = events

        nt.assert_equal(first['title'], '')
        nt.assert_equal(second['title'], u'2intitulé')
        nt.assert_equal(third['title'], '3title content')
        nt.assert_equal(fourth['title'], '4title|content')
        nt.assert_equal(fifth['title'], '5title\\ntitle')

    def test_event_text(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('_e{2,0}:t1|')
        stats.submit_packets('_e{2,12}:t2|text|content')
        stats.submit_packets('_e{2,23}:t3|First line\\nSecond line') # \n is a newline
        stats.submit_packets(u'_e{2,19}:t4|♬ †øU †øU ¥ºu T0µ ♪') # utf-8 compliant

        events = self.sort_events(stats.flush_events())

        assert len(events) == 4
        first, second, third, fourth = events

        nt.assert_equal(first['text'], '')
        nt.assert_equal(second['text'], 'text|content')
        nt.assert_equal(third['text'], 'First line\nSecond line')
        nt.assert_equal(fourth['text'], u'♬ †øU †øU ¥ºu T0µ ♪')

if __name__ == "__main__":
    unittest.main()

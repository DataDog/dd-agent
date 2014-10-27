# -*- coding: utf-8 -*-
import random
import time

import unittest
import nose.tools as nt

from aggregator import MetricsAggregator


class TestUnitDogStatsd(unittest.TestCase):

    @staticmethod
    def sort_metrics(metrics):
        def sort_by(m):
            return (m['metric'], m['host'], m['device_name'], ','.join(m['tags'] or []))
        return sorted(metrics, key=sort_by)

    @staticmethod
    def sort_events(metrics):
        def sort_by(m):
            return (m['msg_title'], m['msg_text'], ','.join(m.get('tags', None) or []))
        return sorted(metrics, key=sort_by)

    @staticmethod
    def assert_almost_equal(i, j, e=1):
        # Floating point math?
        assert abs(i - j) <= e, "%s %s %s" % (i, j, e)

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

    def test_magic_tags(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('my.gauge.a:1|c|#host:test-a')
        stats.submit_packets('my.gauge.b:4|c|#tag1,tag2,host:test-b')
        stats.submit_packets('my.gauge.b:8|c|#host:test-b,tag2,tag1')
        stats.submit_packets('my.gauge.c:10|c|#tag3')
        stats.submit_packets('my.gauge.c:16|c|#device:floppy,tag3')

        metrics = self.sort_metrics(stats.flush())

        nt.assert_equal(len(metrics), 4)
        first, second, third, fourth = metrics

        nt.assert_equal(first['metric'], 'my.gauge.a')
        nt.assert_equal(first['tags'], None)
        nt.assert_equal(first['points'][0][1], 1)
        nt.assert_equal(first['host'], 'test-a')

        nt.assert_equal(second['metric'], 'my.gauge.b')
        nt.assert_equal(second['tags'], ('tag1', 'tag2'))
        nt.assert_equal(second['points'][0][1], 12)
        nt.assert_equal(second['host'], 'test-b')

        nt.assert_equal(third['metric'], 'my.gauge.c')
        nt.assert_equal(third['tags'], ('tag3', ))
        nt.assert_equal(third['points'][0][1], 10)
        nt.assert_equal(third['device_name'], None)

        nt.assert_equal(fourth['metric'], 'my.gauge.c')
        nt.assert_equal(fourth['tags'], ('tag3', ))
        nt.assert_equal(fourth['points'][0][1], 16)
        nt.assert_equal(fourth['device_name'], 'floppy')

    def test_tags_gh442(self):
        import dogstatsd
        from aggregator import api_formatter

        serialized = dogstatsd.serialize_metrics([api_formatter("foo", 12, 1, ('tag',), 'host')])
        assert '"tags": ["tag"]' in serialized[0]

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

    def test_rate_errors(self):
        stats = MetricsAggregator('myhost')
        stats.submit_packets('my.rate:10|_dd-r')
        # Sleep 1 second so the time interval > 0 (timestamp is converted to an int)
        time.sleep(1)
        stats.submit_packets('my.rate:9|_dd-r')

        # Since the difference < 0 we shouldn't get a value
        metrics = stats.flush()
        nt.assert_equal(len(metrics), 0)

        stats.submit_packets('my.rate:10|_dd-r')
        # Trying to have the times be the same
        stats.submit_packets('my.rate:40|_dd-r')

        metrics = stats.flush()
        nt.assert_equal(len(metrics), 0)


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

        nt.assert_equal(len(metrics), 5)
        p95, pavg, pcount, pmax, pmed = self.sort_metrics(metrics)
        nt.assert_equal(p95['metric'], 'my.p.95percentile')
        self.assert_almost_equal(p95['points'][0][1], 95, 10)
        self.assert_almost_equal(pmax['points'][0][1], 99, 1)
        self.assert_almost_equal(pmed['points'][0][1], 50, 2)
        self.assert_almost_equal(pavg['points'][0][1], 50, 2)
        self.assert_almost_equal(pcount['points'][0][1], 4000, 0) # 100 * 20 * 2
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

    def test_monokey_batching_notags(self):
        stats = MetricsAggregator('host')
        stats.submit_packets('test_hist:0.3|ms:2.5|ms|@0.5:3|ms')

        stats_ref = MetricsAggregator('host')
        packets = [
                'test_hist:0.3|ms',
                'test_hist:2.5|ms|@0.5',
                'test_hist:3|ms'
        ]
        stats_ref.submit_packets("\n".join(packets))

        metrics = stats.flush()
        metrics_ref = stats_ref.flush()

        self.assertTrue(len(metrics) == len(metrics_ref) == 5, (metrics, metrics_ref))

        for i in range(len(metrics)):
            nt.assert_equal(metrics[i]['points'][0][1], metrics_ref[i]['points'][0][1])

    def test_monokey_batching_withtags(self):
        stats = MetricsAggregator('host')
        stats.submit_packets('test_gauge:1.5|g|#tag1:one,tag2:two:2.3|g|#tag3:three:3|g')

        stats_ref = MetricsAggregator('host')
        packets = [
                'test_gauge:1.5|g|#tag1:one,tag2:two',
                'test_gauge:2.3|g|#tag3:three',
                'test_gauge:3|g'
        ]
        stats_ref.submit_packets("\n".join(packets))

        metrics = self.sort_metrics(stats.flush())
        metrics_ref = self.sort_metrics(stats_ref.flush())

        self.assertTrue(len(metrics) == len(metrics_ref) == 3, (metrics, metrics_ref))

        for i in range(len(metrics)):
            nt.assert_equal(metrics[i]['points'][0][1], metrics_ref[i]['points'][0][1])
            nt.assert_equal(metrics[i]['tags'], metrics_ref[i]['tags'])


    def test_monokey_batching_withtags_with_sampling(self):
        stats = MetricsAggregator('host')
        stats.submit_packets('test_metric:1.5|c|#tag1:one,tag2:two:2.3|g|#tag3:three:3|g:42|h|#tag1:12,tag42:42|@0.22')

        stats_ref = MetricsAggregator('host')
        packets = [
                'test_metric:1.5|c|#tag1:one,tag2:two',
                'test_metric:2.3|g|#tag3:three',
                'test_metric:3|g',
                'test_metric:42|h|#tag1:12,tag42:42|@0.22'

        ]
        stats_ref.submit_packets("\n".join(packets))

        metrics = self.sort_metrics(stats.flush())
        metrics_ref = self.sort_metrics(stats_ref.flush())

        self.assertTrue(len(metrics) == len(metrics_ref) == 8, (metrics, metrics_ref))
        for i in range(len(metrics)):
            nt.assert_equal(metrics[i]['points'][0][1], metrics_ref[i]['points'][0][1])
            nt.assert_equal(metrics[i]['tags'], metrics_ref[i]['tags'])

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
        ag_interval = 1
        expiry = ag_interval * 4 + 2
        stats = MetricsAggregator('myhost', interval=ag_interval, expiry_seconds=expiry)
        stats.submit_packets('test.counter:123|c')
        stats.submit_packets('test.gauge:55|g')
        stats.submit_packets('test.set:44|s')
        stats.submit_packets('test.histogram:11|h')

        # Ensure points keep submitting
        time.sleep(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 8)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 123)
        time.sleep(ag_interval)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 1)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 0)

        time.sleep(ag_interval)
        time.sleep(0.5)
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 1)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 0)

        # Now sleep for longer than the expiry window and ensure
        # no points are submitted
        time.sleep(ag_interval)
        time.sleep(2)
        m = stats.flush()
        assert not m, str(m)

        # If we submit again, we're all good.
        stats.submit_packets('test.counter:123|c')
        stats.submit_packets('test.gauge:55|g')
        stats.submit_packets('test.set:44|s')
        stats.submit_packets('test.histogram:11|h')

        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 8)
        nt.assert_equal(metrics[0]['metric'], 'test.counter')
        nt.assert_equal(metrics[0]['points'][0][1], 123)


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
        stats = MetricsAggregator('myhost')
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
        stats = MetricsAggregator('myhost')
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
        threshold = 100
        stats = MetricsAggregator('myhost', recent_point_threshold=threshold)
        timestamp_beyond_threshold = time.time() - threshold*2
        timestamp_within_threshold = time.time() - threshold/2

        # Ensure that old gauges get dropped due to old timestamps
        stats.submit_metric('my.first.gauge', 5, 'g')
        stats.submit_metric('my.first.gauge', 1, 'g', timestamp=timestamp_beyond_threshold)
        stats.submit_metric('my.second.gauge', 20, 'g', timestamp=timestamp_beyond_threshold)

        metrics = self.sort_metrics(stats.flush())
        assert len(metrics) == 1

        first = metrics[0]
        nt.assert_equals(first['metric'], 'my.first.gauge')
        nt.assert_equals(first['points'][0][1], 5)
        nt.assert_equals(first['host'], 'myhost')

        # Ensure that old gauges get dropped due to old timestamps
        stats.submit_metric('my.1.gauge', 5, 'g')
        stats.submit_metric('my.1.gauge', 1, 'g', timestamp=timestamp_within_threshold)
        stats.submit_metric('my.2.counter', 20, 'c', timestamp=timestamp_within_threshold)
        stats.submit_metric('my.3.set', 20, 's', timestamp=timestamp_within_threshold)
        stats.submit_metric('my.4.histogram', 20, 'h', timestamp=timestamp_within_threshold)

        flush_timestamp = time.time()
        metrics = self.sort_metrics(stats.flush())
        nt.assert_equal(len(metrics), 8)

        first, second, third, h1, h2, h3, h4, h5 = metrics
        nt.assert_equals(first['metric'], 'my.1.gauge')
        nt.assert_equals(first['points'][0][1], 1)
        nt.assert_equals(first['host'], 'myhost')
        self.assert_almost_equal(first['points'][0][0], timestamp_within_threshold, 0.1)

        nt.assert_equals(second['metric'], 'my.2.counter')
        nt.assert_equals(second['points'][0][1], 20)
        self.assert_almost_equal(second['points'][0][0], flush_timestamp, 0.1)

        nt.assert_equals(third['metric'], 'my.3.set')
        nt.assert_equals(third['points'][0][1], 1)
        self.assert_almost_equal(third['points'][0][0], flush_timestamp, 0.1)

        nt.assert_equals(h1['metric'], 'my.4.histogram.95percentile')
        nt.assert_equals(h1['points'][0][1], 20)
        self.assert_almost_equal(h1['points'][0][0], flush_timestamp, 0.1)
        nt.assert_equal(h1['points'][0][0], h2['points'][0][0])
        nt.assert_equal(h1['points'][0][0], h3['points'][0][0])
        nt.assert_equal(h1['points'][0][0], h4['points'][0][0])
        nt.assert_equal(h1['points'][0][0], h5['points'][0][0])

    def test_packet_string_endings(self):
        stats = MetricsAggregator('myhost')

        stats.submit_packets('line_ending.generic:500|c')
        stats.submit_packets('line_ending.unix:400|c\n')
        stats.submit_packets('line_ending.windows:300|c\r\n')

        metrics = self.sort_metrics(stats.flush())

        assert len(metrics) == 3

        first, second, third = metrics
        nt.assert_equals(first['metric'], 'line_ending.generic')
        nt.assert_equals(first['points'][0][1], 500)

        nt.assert_equals(second['metric'], 'line_ending.unix')
        nt.assert_equals(second['points'][0][1], 400)

        nt.assert_equals(third['metric'], 'line_ending.windows')
        nt.assert_equals(third['points'][0][1], 300)

if __name__ == "__main__":
    unittest.main()

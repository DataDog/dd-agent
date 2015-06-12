# stdlib
import unittest

# project
from aggregator import Histogram, MetricsAggregator
from config import get_histogram_aggregates, get_histogram_percentiles

class TestHistogram(unittest.TestCase):
    def test_default(self):
        stats = MetricsAggregator('myhost')

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        self.assertEquals(len(metrics), 5, metrics)

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        self.assertEquals(
            sorted(value_by_type.keys()),
            ['95percentile', 'avg', 'count', 'max', 'median'], value_by_type
        )

        self.assertEquals(value_by_type['max'], 19, value_by_type)
        self.assertEquals(value_by_type['median'], 9, value_by_type)
        self.assertEquals(value_by_type['avg'], 9.5, value_by_type)
        self.assertEquals(value_by_type['count'], 20.0, value_by_type)
        self.assertEquals(value_by_type['95percentile'], 18, value_by_type)

    def test_custom_single_percentile(self):
        configstr = '0.40'
        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=get_histogram_percentiles(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['percentiles'],
            [0.40],
            stats.metric_config[Histogram]
        )

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        self.assertEquals(len(metrics), 5, metrics)

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        self.assertEquals(value_by_type['40percentile'], 7, value_by_type)

    def test_custom_multiple_percentile(self):
        configstr = '0.4, 0.65, 0.999'
        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=get_histogram_percentiles(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['percentiles'],
            [0.4, 0.65, 0.99],
            stats.metric_config[Histogram]
        )

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        self.assertEquals(len(metrics), 7, metrics)

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        self.assertEquals(value_by_type['40percentile'], 7, value_by_type)
        self.assertEquals(value_by_type['65percentile'], 12, value_by_type)
        self.assertEquals(value_by_type['99percentile'], 19, value_by_type)

    def test_custom_invalid_percentile(self):
        configstr = '1.2342'
        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=get_histogram_percentiles(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['percentiles'],
            [],
            stats.metric_config[Histogram]
        )

    def test_custom_invalid_percentile2(self):
        configstr = 'aoeuoeu'
        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=get_histogram_percentiles(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['percentiles'],
            [],
            stats.metric_config[Histogram]
        )

    def test_custom_invalid_percentile3skip(self):
        configstr = 'aoeuoeu, 2.23, 0.8, 23'
        stats = MetricsAggregator(
            'myhost',
            histogram_percentiles=get_histogram_percentiles(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['percentiles'],
            [0.8],
            stats.metric_config[Histogram]
        )

    def test_custom_aggregate(self):
        configstr = 'median, max'
        stats = MetricsAggregator(
            'myhost',
            histogram_aggregates=get_histogram_aggregates(configstr)
        )

        self.assertEquals(
            sorted(stats.metric_config[Histogram]['aggregates']),
            ['max', 'median'],
            stats.metric_config[Histogram]
        )

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        self.assertEquals(len(metrics), 3, metrics)

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        self.assertEquals(value_by_type['median'], 9, value_by_type)
        self.assertEquals(value_by_type['max'], 19, value_by_type)
        self.assertEquals(value_by_type['95percentile'], 18, value_by_type)

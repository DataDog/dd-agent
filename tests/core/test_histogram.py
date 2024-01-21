# stdlib
import re
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
            ['95percentile', 'avg', 'count', 'max', 'median'],
            value_by_type
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
            [(None, [0.40])],
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
            [(None, [0.4, 0.65, 0.99])],
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
            [(None, [])],
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
            [(None, [])],
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
            [(None, [0.8])],
            stats.metric_config[Histogram]
        )

    def test_custom_aggregate(self):
        configstr = 'median, max, sum'
        stats = MetricsAggregator(
            'myhost',
            histogram_aggregates=get_histogram_aggregates(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['aggregates'],
            [(None, ['median', 'max', 'sum'])],
            stats.metric_config[Histogram]
        )

        for i in xrange(20):
            stats.submit_packets('myhistogram:{0}|h'.format(i))

        metrics = stats.flush()

        self.assertEquals(len(metrics), 4, metrics)

        value_by_type = {}
        for k in metrics:
            value_by_type[k['metric'][len('myhistogram')+1:]] = k['points'][0][1]

        self.assertEquals(value_by_type['median'], 9, value_by_type)
        self.assertEquals(value_by_type['max'], 19, value_by_type)
        self.assertEquals(value_by_type['sum'], 190, value_by_type)
        self.assertEquals(value_by_type['95percentile'], 18, value_by_type)

    def test_custom_aggregate_with_regexes(self):
        configstr = '^my_pre\.fix: median, max, sum; max, median'
        stats = MetricsAggregator(
            'myhost',
            histogram_aggregates=get_histogram_aggregates(configstr)
        )

        self.assertEquals(
            stats.metric_config[Histogram]['aggregates'],
            [(re.compile(r'^my_pre\.fix'), ['median', 'max', 'sum']), (None, ['max', 'median'])],
            stats.metric_config[Histogram]
        )

        for i in xrange(20):
            stats.submit_packets('my_pre.fix_metric:{0}|h'.format(i))
            stats.submit_packets('not_my_pre.fix_metric:{0}|h'.format(-i))

        metrics = stats.flush()

        self.assertEquals(len(metrics), 7, metrics)

        value_by_type_for_my_prefix = {}
        value_by_type_for_not_my_prefix = {}
        for k in metrics:
            if k['metric'].startswith('my_pre.fix_metric'):
                value_by_type_for_my_prefix[k['metric'][len('my_pre.fix_metric')+1:]] = k['points'][0][1]
            else:
                value_by_type_for_not_my_prefix[k['metric'][len('not_my_pre.fix_metric')+1:]] = k['points'][0][1]

        self.assertEquals(value_by_type_for_my_prefix['median'], 9, value_by_type_for_my_prefix)
        self.assertEquals(value_by_type_for_my_prefix['max'], 19, value_by_type_for_my_prefix)
        self.assertEquals(value_by_type_for_my_prefix['sum'], 190, value_by_type_for_my_prefix)
        self.assertEquals(value_by_type_for_my_prefix['95percentile'], 18, value_by_type_for_my_prefix)

        self.assertEquals(value_by_type_for_not_my_prefix['median'], -10, value_by_type_for_not_my_prefix)
        self.assertEquals(value_by_type_for_not_my_prefix['max'], 0, value_by_type_for_not_my_prefix)
        self.assertEquals(value_by_type_for_not_my_prefix['95percentile'], -1, value_by_type_for_not_my_prefix)

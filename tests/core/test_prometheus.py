# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
from mock import MagicMock, patch, call
import unittest
import os

from checks.prometheus_check import PrometheusCheck
from utils.prometheus import parse_metric_family, metrics_pb2


class TestPrometheusFuncs(unittest.TestCase):
    def test_parse_metric_family(self):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'protobuf.bin')
        with open(f_name, 'rb') as f:
            data = f.read()
            self.assertEqual(len(data), 51855)
            messages = list(parse_metric_family(data))
            self.assertEqual(len(messages), 61)
            self.assertEqual(messages[-1].name, 'process_virtual_memory_bytes')

class TestPrometheusProcessor(unittest.TestCase):

    def setUp(self):
        self.check = PrometheusCheck('prometheus_check', {}, {}, {})
        self.check.gauge = MagicMock()
        self.check.log = logging.getLogger('datadog-prometheus.test')
        self.check.log.debug = MagicMock()
        self.check.metrics_mapper = {'process_virtual_memory_bytes': 'process.vm.bytes'}
        self.check.NAMESPACE = 'prometheus'
        self.protobuf_content_type = 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited'
        # reference gauge metric in the protobuf target class type
        self.ref_gauge = metrics_pb2.MetricFamily()
        self.ref_gauge.name = 'process_virtual_memory_bytes'
        self.ref_gauge.help = 'Virtual memory size in bytes.'
        self.ref_gauge.type = 1 # GAUGE
        _m = self.ref_gauge.metric.add()
        _m.gauge.value = 39211008.0
        # Loading test binary data
        self.bin_data = None
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'protobuf.bin')
        with open(f_name, 'rb') as f:
            self.bin_data = f.read()
            self.assertEqual(len(self.bin_data), 51855)

    def tearDown(self):
        # Cleanup
        self.check = None
        self.bin_data = None
        self.ref_gauge = None

    def test_check(self):
        ''' Should not be implemented as it is the mother class '''
        with self.assertRaises(NotImplementedError):
            self.check.check(None)

    def test_parse_metric_family_protobuf(self):
        messages = list(self.check.parse_metric_family(self.bin_data, self.protobuf_content_type))
        self.assertEqual(len(messages), 61)
        self.assertEqual(messages[-1].name, 'process_virtual_memory_bytes')

    def test_parse_metric_family_text(self):
        ''' Test the high level method for loading metrics from text format '''
        _text_data = None
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'metrics.txt')
        with open(f_name, 'r') as f:
            _text_data = f.read()
            self.assertEqual(len(_text_data), 14488)
        messages = list(self.check.parse_metric_family(_text_data, 'text/plain; version=0.0.4'))
        self.assertEqual(len(messages), 41)
        # Tests correct parsing of counters
        _counter = metrics_pb2.MetricFamily()
        _counter.name = 'skydns_skydns_dns_cachemiss_count_total'
        _counter.help = 'Counter of DNS requests that result in a cache miss.'
        _counter.type = 0 # COUNTER
        _c = _counter.metric.add()
        _c.counter.value = 1359194.0
        _lc = _c.label.add()
        _lc.name = 'cache'
        _lc.value = 'response'
        self.assertIn(_counter, messages)
        # Tests correct parsing of gauges
        _gauge = metrics_pb2.MetricFamily()
        _gauge.name = 'go_memstats_heap_alloc_bytes'
        _gauge.help = 'Number of heap bytes allocated and still in use.'
        _gauge.type = 1 # GAUGE
        _gauge.metric.add().gauge.value = 6396288.0
        self.assertIn(_gauge, messages)
        # Tests correct parsing of summaries
        _summary = metrics_pb2.MetricFamily()
        _summary.name = 'http_response_size_bytes'
        _summary.help = 'The HTTP response sizes in bytes.'
        _summary.type = 2 # SUMMARY
        _sm = _summary.metric.add()
        _lsm = _sm.label.add()
        _lsm.name = 'handler'
        _lsm.value = 'prometheus'
        _sm.summary.sample_count = 25
        _sm.summary.sample_sum = 147728.0
        _sq1 = _sm.summary.quantile.add()
        _sq1.quantile = 0.5
        _sq1.value = 21470.0
        _sq2 = _sm.summary.quantile.add()
        _sq2.quantile = 0.9
        _sq2.value = 21470.0
        _sq3 = _sm.summary.quantile.add()
        _sq3.quantile = 0.99
        _sq3.value = 21470.0
        self.assertIn(_summary, messages)
        # Tests correct parsing of histograms
        _histo = metrics_pb2.MetricFamily()
        _histo.name = 'skydns_skydns_dns_response_size_bytes'
        _histo.help = 'Size of the returns response in bytes.'
        _histo.type = 4 # HISTOGRAM
        _sample_data = [
            {'ct':1359194,'sum':199427281.0, 'lbl': {'system':'auth'},
                'buckets':{0.0: 0, 512.0:1359194, 1024.0:1359194,
                    1500.0:1359194, 2048.0:1359194, float('+Inf'):1359194}},
            {'ct':1359194,'sum':199427281.0, 'lbl': {'system':'recursive'},
                'buckets':{0.0: 0, 512.0:520924, 1024.0:520924, 1500.0:520924,
                    2048.0:520924, float('+Inf'):520924}},
            {'ct':1359194,'sum':199427281.0, 'lbl': {'system':'reverse'},
                'buckets':{0.0: 0, 512.0:67648, 1024.0:67648, 1500.0:67648,
                    2048.0:67648, float('+Inf'):67648}},
        ]
        for _data in _sample_data:
            _h = _histo.metric.add()
            _h.histogram.sample_count = _data['ct']
            _h.histogram.sample_sum = _data['sum']
            for k, v in _data['lbl'].items():
                _lh = _h.label.add()
                _lh.name = k
                _lh.value = v
            for _b in sorted(_data['buckets'].iterkeys()):
                _subh = _h.histogram.bucket.add()
                _subh.upper_bound = _b
                _subh.cumulative_count = _data['buckets'][_b]
        self.assertIn(_histo, messages)

    def test_parse_metric_family_unsupported(self):
        with self.assertRaises(PrometheusCheck.UnknownFormatError):
            list(self.check.parse_metric_family(self.bin_data, 'application/json'))

    def test_process(self):
        endpoint = "http://fake.endpoint:10055/metrics"
        self.check.poll = MagicMock(return_value=[self.protobuf_content_type, self.bin_data])
        self.check.process_metric = MagicMock()
        self.check.process(endpoint, instance=None)
        self.check.poll.assert_called_with(endpoint)
        self.check.process_metric.assert_called_with(self.ref_gauge, instance=None)

    def test_process_metric_gauge(self):
        ''' Gauge ref submission '''
        self.check.process_metric(self.ref_gauge)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0, [])

    def test_process_metric_filtered(self):
        ''' Metric absent from the metrics_mapper '''
        filtered_gauge = metrics_pb2.MetricFamily()
        filtered_gauge.name = "process_start_time_seconds"
        filtered_gauge.help = "Start time of the process since unix epoch in seconds."
        filtered_gauge.type = 1 # GAUGE
        _m = filtered_gauge.metric.add()
        _m.gauge.value = 39211008.0
        self.check.process_metric(filtered_gauge)
        self.check.log.debug.assert_called_with("Unable to handle metric: process_start_time_seconds - error: 'PrometheusCheck' object has no attribute 'process_start_time_seconds'")
        self.check.gauge.assert_not_called()

    @patch('requests.get')
    def test_poll_protobuf(self, mock_get):
        ''' Tests poll using the protobuf format '''
        mock_get.return_value = MagicMock(status_code=200, content=self.bin_data, headers={'Content-Type': self.protobuf_content_type})
        ct, data = self.check.poll("http://fake.endpoint:10055/metrics")
        messages = list(self.check.parse_metric_family(data, ct))
        self.assertEqual(len(messages), 61)
        self.assertEqual(messages[-1].name, 'process_virtual_memory_bytes')

    def test_submit_metric_gauge_with_labels(self):
        ''' submitting metrics that contain labels should result in tags on the gauge call '''
        _l1 = self.ref_gauge.metric[0].label.add()
        _l1.name = 'my_1st_label'
        _l1.value = 'my_1st_label_value'
        _l2 = self.ref_gauge.metric[0].label.add()
        _l2.name = 'my_2nd_label'
        _l2.value = 'my_2nd_label_value'
        self.check._submit_metric(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                ['my_1st_label:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'])

    def test_submit_metric_gauge_with_custom_tags(self):
        ''' Providing custom tags should add them as is on the gauge call '''
        tags = ['env:dev', 'app:my_pretty_app']
        self.check._submit_metric(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                ['env:dev', 'app:my_pretty_app'])

    def test_submit_metric_gauge_with_labels_mapper(self):
        '''
        Submitting metrics that contain labels mappers should result in tags
        on the gauge call with transformed tag names
        '''
        _l1 = self.ref_gauge.metric[0].label.add()
        _l1.name = 'my_1st_label'
        _l1.value = 'my_1st_label_value'
        _l2 = self.ref_gauge.metric[0].label.add()
        _l2.name = 'my_2nd_label'
        _l2.value = 'my_2nd_label_value'
        self.check.labels_mapper = {'my_1st_label': 'transformed_1st', 'non_existent': 'should_not_matter', 'env': 'dont_touch_custom_tags'}
        tags = ['env:dev', 'app:my_pretty_app']
        self.check._submit_metric(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                ['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'])

    def test_submit_metric_gauge_with_exclude_labels(self):
        '''
        Submitting metrics when filtering with exclude_labels should end up with
        a filtered tags list
        '''
        _l1 = self.ref_gauge.metric[0].label.add()
        _l1.name = 'my_1st_label'
        _l1.value = 'my_1st_label_value'
        _l2 = self.ref_gauge.metric[0].label.add()
        _l2.name = 'my_2nd_label'
        _l2.value = 'my_2nd_label_value'
        self.check.labels_mapper = {'my_1st_label': 'transformed_1st', 'non_existent': 'should_not_matter', 'env': 'dont_touch_custom_tags'}
        tags = ['env:dev', 'app:my_pretty_app']
        self.check.exclude_labels = ['my_2nd_label', 'whatever_else', 'env'] # custom tags are not filtered out
        self.check._submit_metric(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                ['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value'])

    def test_submit_metric_counter(self):
        _counter = metrics_pb2.MetricFamily()
        _counter.name = 'my_counter'
        _counter.help = 'Random counter'
        _counter.type = 0 # COUNTER
        _met = _counter.metric.add()
        _met.counter.value = 42
        self.check._submit_metric('custom.counter', _counter)
        self.check.gauge.assert_called_with('prometheus.custom.counter', 42, [])

    def test_submit_metrics_summary(self):
        _sum = metrics_pb2.MetricFamily()
        _sum.name = 'my_summary'
        _sum.help = 'Random summary'
        _sum.type = 2 # SUMMARY
        _met = _sum.metric.add()
        _met.summary.sample_count = 42
        _met.summary.sample_sum = 3.14
        _q1 = _met.summary.quantile.add()
        _q1.quantile = 10
        _q1.value = 3
        _q2 = _met.summary.quantile.add()
        _q2.quantile = 4
        _q2.value = 5
        self.check._submit_metric('custom.summary', _sum)
        self.check.gauge.assert_has_calls([
            call('prometheus.custom.summary.count', 42, []),
            call('prometheus.custom.summary.sum', 3.14, []),
            call('prometheus.custom.summary.quantile', 3, ['quantile:10']),
            call('prometheus.custom.summary.quantile', 5, ['quantile:4'])
        ])

    def test_submit_metric_histogram(self):
        _histo = metrics_pb2.MetricFamily()
        _histo.name = 'my_histogram'
        _histo.help = 'Random histogram'
        _histo.type = 4 # HISTOGRAM
        _met = _histo.metric.add()
        _met.histogram.sample_count = 42
        _met.histogram.sample_sum = 3.14
        _b1 = _met.histogram.bucket.add()
        _b1.upper_bound = 12.7
        _b1.cumulative_count = 33
        _b2 = _met.histogram.bucket.add()
        _b2.upper_bound = 18.2
        _b2.cumulative_count = 666
        self.check._submit_metric('custom.histogram', _histo)
        self.check.gauge.assert_has_calls([
            call('prometheus.custom.histogram.count', 42, []),
            call('prometheus.custom.histogram.sum', 3.14, []),
            call('prometheus.custom.histogram.count', 33, ['upper_bound:12.7']),
            call('prometheus.custom.histogram.count', 666, ['upper_bound:18.2'])
        ])

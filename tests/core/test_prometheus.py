# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
import os
import unittest

from mock import MagicMock, patch, call

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
        self.ref_gauge.type = 1  # GAUGE
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
        # check type overriding is working
        # original type:
        self.assertEqual(messages[1].name, 'go_goroutines')
        self.assertEqual(messages[1].type, 1)  # gauge
        # override the type:
        self.check.type_overrides = {"go_goroutines": "summary"}
        messages = list(self.check.parse_metric_family(self.bin_data, self.protobuf_content_type))
        self.assertEqual(len(messages), 61)
        self.assertEqual(messages[1].name, 'go_goroutines')
        self.assertEqual(messages[1].type, 2)  # summary

    def test_parse_metric_family_text(self):
        ''' Test the high level method for loading metrics from text format '''
        _text_data = None
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'metrics.txt')
        with open(f_name, 'r') as f:
            _text_data = f.read()
            self.assertEqual(len(_text_data), 14494)
        messages = list(self.check.parse_metric_family(_text_data, 'text/plain; version=0.0.4'))
        # total metrics are 41 but one is typeless and we expect it not to be
        # parsed...
        self.assertEqual(len(messages), 40)
        # ...unless the check ovverrides the type manually
        self.check.type_overrides = {"go_goroutines": "gauge"}
        messages = list(self.check.parse_metric_family(_text_data, 'text/plain; version=0.0.4'))
        self.assertEqual(len(messages), 41)
        # Tests correct parsing of counters
        _counter = metrics_pb2.MetricFamily()
        _counter.name = 'skydns_skydns_dns_cachemiss_count_total'
        _counter.help = 'Counter of DNS requests that result in a cache miss.'
        _counter.type = 0  # COUNTER
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
        _gauge.type = 1  # GAUGE
        _gauge.metric.add().gauge.value = 6396288.0
        self.assertIn(_gauge, messages)
        # Tests correct parsing of summaries
        _summary = metrics_pb2.MetricFamily()
        _summary.name = 'http_response_size_bytes'
        _summary.help = 'The HTTP response sizes in bytes.'
        _summary.type = 2  # SUMMARY
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
        _histo.type = 4  # HISTOGRAM
        _sample_data = [
            {'ct': 1359194, 'sum': 199427281.0, 'lbl': {'system': 'auth'},
             'buckets': {0.0: 0, 512.0: 1359194, 1024.0: 1359194,
                         1500.0: 1359194, 2048.0: 1359194, float('+Inf'): 1359194}},
            {'ct': 1359194, 'sum': 199427281.0, 'lbl': {'system': 'recursive'},
             'buckets': {0.0: 0, 512.0: 520924, 1024.0: 520924, 1500.0: 520924,
                         2048.0: 520924, float('+Inf'): 520924}},
            {'ct': 1359194, 'sum': 199427281.0, 'lbl': {'system': 'reverse'},
             'buckets': {0.0: 0, 512.0: 67648, 1024.0: 67648, 1500.0: 67648,
                         2048.0: 67648, float('+Inf'): 67648}},
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
        self.check.process_metric.assert_called_with(self.ref_gauge, custom_tags=[], instance=None,
                                                     send_histograms_buckets=True)

    def test_process_send_histograms_buckets(self):
        """ Cheks that the send_histograms_buckets parameter is passed along """
        endpoint = "http://fake.endpoint:10055/metrics"
        self.check.poll = MagicMock(return_value=[self.protobuf_content_type, self.bin_data])
        self.check.process_metric = MagicMock()
        self.check.process(endpoint, send_histograms_buckets=False, instance=None)
        self.check.poll.assert_called_with(endpoint)
        self.check.process_metric.assert_called_with(self.ref_gauge, custom_tags=[], instance=None,
                                                     send_histograms_buckets=False)

    def test_process_instance_with_tags(self):
        """ Checks that an instances with tags passes them as custom tag """
        endpoint = "http://fake.endpoint:10055/metrics"
        self.check.poll = MagicMock(return_value=[self.protobuf_content_type, self.bin_data])
        self.check.process_metric = MagicMock()
        instance = {'endpoint': 'IgnoreMe', 'tags': ['tag1:tagValue1', 'tag2:tagValue2']}
        self.check.process(endpoint, instance=instance)
        self.check.poll.assert_called_with(endpoint)
        self.check.process_metric.assert_called_with(self.ref_gauge, custom_tags=['tag1:tagValue1', 'tag2:tagValue2'],
                                                     instance=instance, send_histograms_buckets=True)

    def test_process_metric_gauge(self):
        ''' Gauge ref submission '''
        self.check.process_metric(self.ref_gauge)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0, [])

    def test_process_metric_filtered(self):
        ''' Metric absent from the metrics_mapper '''
        filtered_gauge = metrics_pb2.MetricFamily()
        filtered_gauge.name = "process_start_time_seconds"
        filtered_gauge.help = "Start time of the process since unix epoch in seconds."
        filtered_gauge.type = 1  # GAUGE
        _m = filtered_gauge.metric.add()
        _m.gauge.value = 39211008.0
        self.check.process_metric(filtered_gauge)
        self.check.log.debug.assert_called_with(
            "Unable to handle metric: process_start_time_seconds - error: 'PrometheusCheck' object has no attribute 'process_start_time_seconds'")
        self.check.gauge.assert_not_called()

    @patch('requests.get')
    def test_poll_protobuf(self, mock_get):
        ''' Tests poll using the protobuf format '''
        mock_get.return_value = MagicMock(status_code=200, content=self.bin_data,
                                          headers={'Content-Type': self.protobuf_content_type})
        ct, data = self.check.poll("http://fake.endpoint:10055/metrics")
        messages = list(self.check.parse_metric_family(data, ct))
        self.assertEqual(len(messages), 61)
        self.assertEqual(messages[-1].name, 'process_virtual_memory_bytes')

    def test_submit_gauge_with_labels(self):
        ''' submitting metrics that contain labels should result in tags on the gauge call '''
        _l1 = self.ref_gauge.metric[0].label.add()
        _l1.name = 'my_1st_label'
        _l1.value = 'my_1st_label_value'
        _l2 = self.ref_gauge.metric[0].label.add()
        _l2.name = 'my_2nd_label'
        _l2.value = 'my_2nd_label_value'
        self.check._submit(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                                            ['my_1st_label:my_1st_label_value', 'my_2nd_label:my_2nd_label_value'])

    def test_labels_not_added_as_tag_once_for_each_metric(self):
        _l1 = self.ref_gauge.metric[0].label.add()
        _l1.name = 'my_1st_label'
        _l1.value = 'my_1st_label_value'
        _l2 = self.ref_gauge.metric[0].label.add()
        _l2.name = 'my_2nd_label'
        _l2.value = 'my_2nd_label_value'
        tags = ['test']
        self.check._submit(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        # Call a second time to check that the labels were not added once more to the tags list and
        # avoid regression on https://github.com/DataDog/dd-agent/pull/3359
        self.check._submit(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                                            ['test', 'my_1st_label:my_1st_label_value',
                                             'my_2nd_label:my_2nd_label_value'])

    def test_submit_gauge_with_custom_tags(self):
        ''' Providing custom tags should add them as is on the gauge call '''
        tags = ['env:dev', 'app:my_pretty_app']
        self.check._submit(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                                            ['env:dev', 'app:my_pretty_app'])

    def test_submit_gauge_with_labels_mapper(self):
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
        self.check.labels_mapper = {'my_1st_label': 'transformed_1st', 'non_existent': 'should_not_matter',
                                    'env': 'dont_touch_custom_tags'}
        tags = ['env:dev', 'app:my_pretty_app']
        self.check._submit(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                                            ['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value',
                                             'my_2nd_label:my_2nd_label_value'])

    def test_submit_gauge_with_exclude_labels(self):
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
        self.check.labels_mapper = {'my_1st_label': 'transformed_1st', 'non_existent': 'should_not_matter',
                                    'env': 'dont_touch_custom_tags'}
        tags = ['env:dev', 'app:my_pretty_app']
        self.check.exclude_labels = ['my_2nd_label', 'whatever_else', 'env']  # custom tags are not filtered out
        self.check._submit(self.check.metrics_mapper[self.ref_gauge.name], self.ref_gauge, custom_tags=tags)
        self.check.gauge.assert_called_with('prometheus.process.vm.bytes', 39211008.0,
                                            ['env:dev', 'app:my_pretty_app', 'transformed_1st:my_1st_label_value'])

    def test_submit_counter(self):
        _counter = metrics_pb2.MetricFamily()
        _counter.name = 'my_counter'
        _counter.help = 'Random counter'
        _counter.type = 0  # COUNTER
        _met = _counter.metric.add()
        _met.counter.value = 42
        self.check._submit('custom.counter', _counter)
        self.check.gauge.assert_called_with('prometheus.custom.counter', 42, [])

    def test_submits_summary(self):
        _sum = metrics_pb2.MetricFamily()
        _sum.name = 'my_summary'
        _sum.help = 'Random summary'
        _sum.type = 2  # SUMMARY
        _met = _sum.metric.add()
        _met.summary.sample_count = 42
        _met.summary.sample_sum = 3.14
        _q1 = _met.summary.quantile.add()
        _q1.quantile = 10.0
        _q1.value = 3
        _q2 = _met.summary.quantile.add()
        _q2.quantile = 4.0
        _q2.value = 5
        self.check._submit('custom.summary', _sum)
        self.check.gauge.assert_has_calls([
            call('prometheus.custom.summary.count', 42, []),
            call('prometheus.custom.summary.sum', 3.14, []),
            call('prometheus.custom.summary.quantile', 3, ['quantile:10.0']),
            call('prometheus.custom.summary.quantile', 5, ['quantile:4.0'])
        ])

    def test_submit_histogram(self):
        _histo = metrics_pb2.MetricFamily()
        _histo.name = 'my_histogram'
        _histo.help = 'Random histogram'
        _histo.type = 4  # HISTOGRAM
        _met = _histo.metric.add()
        _met.histogram.sample_count = 42
        _met.histogram.sample_sum = 3.14
        _b1 = _met.histogram.bucket.add()
        _b1.upper_bound = 12.7
        _b1.cumulative_count = 33
        _b2 = _met.histogram.bucket.add()
        _b2.upper_bound = 18.2
        _b2.cumulative_count = 666
        self.check._submit('custom.histogram', _histo)
        self.check.gauge.assert_has_calls([
            call('prometheus.custom.histogram.count', 42, []),
            call('prometheus.custom.histogram.sum', 3.14, []),
            call('prometheus.custom.histogram.count', 33, ['upper_bound:12.7']),
            call('prometheus.custom.histogram.count', 666, ['upper_bound:18.2'])
        ])


class TestPrometheusTextParsing(unittest.TestCase):
    def setUp(self):
        self.check = PrometheusCheck('prometheus_check', {}, {}, {})

    def test_parse_one_gauge(self):
        """
        name: "etcd_server_has_leader"
        help: "Whether or not a leader exists. 1 is existence, 0 is not."
        type: GAUGE
        metric {
          gauge {
            value: 1.0
          }
        }
        """
        text_data = \
            "# HELP etcd_server_has_leader Whether or not a leader exists. 1 is existence, 0 is not.\n" \
            "# TYPE etcd_server_has_leader gauge\n" \
            "etcd_server_has_leader 1\n"

        expected_etcd_metric = metrics_pb2.MetricFamily()
        expected_etcd_metric.help = "Whether or not a leader exists. 1 is existence, 0 is not."
        expected_etcd_metric.name = "etcd_server_has_leader"
        expected_etcd_metric.type = 1
        expected_etcd_metric.metric.add().gauge.value = 1

        # Iter on the generator to get all metrics
        metrics = [k for k in self.check.parse_metric_family(text_data, 'text/plain; version=0.0.4')]

        self.assertEqual(1, len(metrics))
        current_metric = metrics[0]
        self.assertEqual(expected_etcd_metric, current_metric)

        # Remove the old metric and add a new one with a different value
        expected_etcd_metric.metric.pop()
        expected_etcd_metric.metric.add().gauge.value = 0
        self.assertNotEqual(expected_etcd_metric, current_metric)

        # Re-add the expected value but as different type: it should works
        expected_etcd_metric.metric.pop()
        expected_etcd_metric.metric.add().gauge.value = 1.0
        self.assertEqual(expected_etcd_metric, current_metric)

    def test_parse_one_counter(self):
        """
        name: "go_memstats_mallocs_total"
        help: "Total number of mallocs."
        type: COUNTER
        metric {
          counter {
            value: 18713.0
          }
        }
        """
        text_data = \
            "# HELP go_memstats_mallocs_total Total number of mallocs.\n" \
            "# TYPE go_memstats_mallocs_total counter\n" \
            "go_memstats_mallocs_total 18713\n"

        expected_etcd_metric = metrics_pb2.MetricFamily()
        expected_etcd_metric.help = "Total number of mallocs."
        expected_etcd_metric.name = "go_memstats_mallocs_total"
        expected_etcd_metric.type = 0
        expected_etcd_metric.metric.add().counter.value = 18713

        # Iter on the generator to get all metrics
        metrics = [k for k in self.check.parse_metric_family(text_data, 'text/plain; version=0.0.4')]

        self.assertEqual(1, len(metrics))
        current_metric = metrics[0]
        self.assertEqual(expected_etcd_metric, current_metric)

        # Remove the old metric and add a new one with a different value
        expected_etcd_metric.metric.pop()
        expected_etcd_metric.metric.add().counter.value = 18714
        self.assertNotEqual(expected_etcd_metric, current_metric)

    def test_parse_one_histogram(self):
        """
        name: "etcd_disk_wal_fsync_duration_seconds"
        help: "The latency distributions of fsync called by wal."
        type: HISTOGRAM
        metric {
          histogram {
            sample_count: 4
            sample_sum: 0.026131671
            bucket {
              cumulative_count: 2
              upper_bound: 0.001
            }
            bucket {
              cumulative_count: 2
              upper_bound: 0.002
            }
            bucket {
              cumulative_count: 2
              upper_bound: 0.004
            }
            bucket {
              cumulative_count: 2
              upper_bound: 0.008
            }
            bucket {
              cumulative_count: 4
              upper_bound: 0.016
            }
            bucket {
              cumulative_count: 4
              upper_bound: 0.032
            }
            bucket {
              cumulative_count: 4
              upper_bound: 0.064
            }
            bucket {
              cumulative_count: 4
              upper_bound: 0.128
            }
            bucket {
              cumulative_count: 4
              upper_bound: 0.256
            }
            bucket {
              cumulative_count: 4
              upper_bound: 0.512
            }
            bucket {
              cumulative_count: 4
              upper_bound: 1.024
            }
            bucket {
              cumulative_count: 4
              upper_bound: 2.048
            }
            bucket {
              cumulative_count: 4
              upper_bound: 4.096
            }
            bucket {
              cumulative_count: 4
              upper_bound: 8.192
            }
            bucket {
              cumulative_count: 4
              upper_bound: inf
            }
          }
        }
        """
        text_data = \
            '# HELP etcd_disk_wal_fsync_duration_seconds The latency distributions of fsync called by wal.\n' \
            '# TYPE etcd_disk_wal_fsync_duration_seconds histogram\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.001"} 2\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.002"} 2\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.004"} 2\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.008"} 2\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.016"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.032"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.064"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.128"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.256"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="0.512"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="1.024"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="2.048"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="4.096"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="8.192"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_bucket{le="+Inf"} 4\n' \
            'etcd_disk_wal_fsync_duration_seconds_sum 0.026131671\n' \
            'etcd_disk_wal_fsync_duration_seconds_count 4\n'

        expected_etcd_metric = metrics_pb2.MetricFamily()
        expected_etcd_metric.help = "The latency distributions of fsync called by wal."
        expected_etcd_metric.name = "etcd_disk_wal_fsync_duration_seconds"
        expected_etcd_metric.type = 4

        histogram_metric = expected_etcd_metric.metric.add()
        for upper_bound, cumulative_count in [
            (0.001, 2),
            (0.002, 2),
            (0.004, 2),
            (0.008, 2),
            (0.016, 4),
            (0.032, 4),
            (0.064, 4),
            (0.128, 4),
            (0.256, 4),
            (0.512, 4),
            (1.024, 4),
            (2.048, 4),
            (4.096, 4),
            (8.192, 4),
            (float('inf'), 4),
        ]:
            bucket = histogram_metric.histogram.bucket.add()
            bucket.upper_bound = upper_bound
            bucket.cumulative_count = cumulative_count

        # Root histogram sample
        histogram_metric.histogram.sample_count = 4
        histogram_metric.histogram.sample_sum = 0.026131671

        # Iter on the generator to get all metrics
        metrics = [k for k in self.check.parse_metric_family(text_data, 'text/plain; version=0.0.4')]

        self.assertEqual(1, len(metrics))
        current_metric = metrics[0]
        self.assertEqual(expected_etcd_metric, current_metric)

    def test_parse_one_summary(self):
        """
        name: "http_response_size_bytes"
        help: "The HTTP response sizes in bytes."
        type: SUMMARY
        metric {
          label {
            name: "handler"
            value: "prometheus"
          }
          summary {
            sample_count: 5
            sample_sum: 120512.0
            quantile {
              quantile: 0.5
              value: 24547.0
            }
            quantile {
              quantile: 0.9
              value: 25763.0
            }
            quantile {
              quantile: 0.99
              value: 25763.0
            }
          }
        }
        """
        text_data = \
            '# HELP http_response_size_bytes The HTTP response sizes in bytes.\n' \
            '# TYPE http_response_size_bytes summary\n' \
            'http_response_size_bytes{handler="prometheus",quantile="0.5"} 24547\n' \
            'http_response_size_bytes{handler="prometheus",quantile="0.9"} 25763\n' \
            'http_response_size_bytes{handler="prometheus",quantile="0.99"} 25763\n' \
            'http_response_size_bytes_sum{handler="prometheus"} 120512\n' \
            'http_response_size_bytes_count{handler="prometheus"} 5\n'

        expected_etcd_metric = metrics_pb2.MetricFamily()
        expected_etcd_metric.help = "The HTTP response sizes in bytes."
        expected_etcd_metric.name = "http_response_size_bytes"
        expected_etcd_metric.type = 2

        summary_metric = expected_etcd_metric.metric.add()

        # Label for prometheus handler
        summary_label = summary_metric.label.add()
        summary_label.name, summary_label.value = "handler", "prometheus"

        # Root summary sample
        summary_metric.summary.sample_count = 5
        summary_metric.summary.sample_sum = 120512

        # Create quantiles 0.5, 0.9, 0.99
        quantile_05 = summary_metric.summary.quantile.add()
        quantile_05.quantile = 0.5
        quantile_05.value = 24547

        quantile_09 = summary_metric.summary.quantile.add()
        quantile_09.quantile = 0.9
        quantile_09.value = 25763

        quantile_099 = summary_metric.summary.quantile.add()
        quantile_099.quantile = 0.99
        quantile_099.value = 25763

        # Iter on the generator to get all metrics
        metrics = [k for k in self.check.parse_metric_family(text_data, 'text/plain; version=0.0.4')]

        self.assertEqual(1, len(metrics))

        current_metric = metrics[0]
        self.assertEqual(expected_etcd_metric, current_metric)

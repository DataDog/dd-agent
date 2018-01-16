# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import unittest

from mock import MagicMock, patch, call
from prometheus_client import generate_latest, CollectorRegistry, Gauge

from checks.generic_prometheus_check import GenericPrometheusCheck

class TestGenericPrometheusCheck(unittest.TestCase):

    def setUp(self):
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'generic_conf.yaml')
        self.check, self.instances = GenericPrometheusCheck.from_yaml(f_name)

    def test_init(self):
        self.assertEqual(2, len(self.check.check_map))
        check1 = self.check.check_map['http://service/prometheus']
        check2 = self.check.check_map['http://foobar/endpoint']
        self.assertEqual(check1.NAMESPACE, "service")
        self.assertEqual(check2.NAMESPACE, "foobar")
        self.assertEqual(check1.label_to_hostname, "node")
        self.assertDictEqual(
            check1.metrics_mapper,
            {'processor': 'cpu', 'memory': 'mem', 'io': 'io'}
        )
        self.assertDictEqual(
            check2.metrics_mapper,
            {'bar': 'bar', 'foo': 'foo', 'foobar': 'fb'}
        )
        self.assertDictEqual(
            check1.label_joins,
            {
                'target_metric':
                {
                    'label_to_match': 'matched_label',
                    'labels_to_get': ['extra_label_1', 'extra_label_2']
                }
            }
        )
        self.assertDictEqual(check1.labels_mapper, {'flavor': 'origin'})
        self.assertListEqual(check1.exclude_labels, ['timestamp'])

    @patch('requests.get')
    def test_multiple_checks(self, mock_get):
        registry1 = CollectorRegistry()
        # pylint: disable=E1123,E1120
        g = Gauge('processor', 'processor usage', registry=registry1)
        g.set(4.2)
        data1 = generate_latest(registry1)

        registry2 = CollectorRegistry()
        g = Gauge('foo', 'foo usage', registry=registry2)
        g.set(1337)
        g = Gauge('foobar', 'foo usage', registry=registry2)
        g.set(42)
        data2 = generate_latest(registry2)

        def get_side_effect(*args, **kwargs):
            if args[0] == 'http://service/prometheus':
                return MagicMock(status_code=200,
                    iter_lines=lambda **kwargs: data1.split("\n"),
                    headers={'Content-Type': "text/plain"})
            if args[0] == 'http://foobar/endpoint':
                return MagicMock(status_code=500,
                    iter_lines=lambda **kwargs: data2.split("\n"),
                    headers={'Content-Type': "text/plain"})

        mock_get.side_effect = get_side_effect

        check1 = self.check.check_map['http://service/prometheus']
        instance = self.instances[0]
        check1.gauge = MagicMock()
        # label_joins is set so there's a dry run
        self.check.check(instance)
        self.check.check(instance)
        check1.gauge.assert_has_calls([
            call('service.cpu', 4.2, ['foo:bar'], hostname=None),
        ], any_order=True)

        check2 = self.check.check_map['http://foobar/endpoint']
        instance = self.instances[1]
        check2.gauge = MagicMock()
        self.check.check(instance)
        check2.gauge.assert_has_calls([
            call('foobar.foo', 1337.0, [], hostname=None),
            call('foobar.fb', 42.0, [], hostname=None),
        ], any_order=True)

    @patch('requests.get')
    def test_advanced_conf_check(self, mock_get):
        registry = CollectorRegistry()
        # pylint: disable=E1123,E1120
        g1 = Gauge('processor', 'processor usage', ['matched_label', 'node', 'flavor'], registry=registry)
        g1.labels(matched_label="foobar", node="localhost", flavor="test").set(99.9)
        g2 = Gauge('memory', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
        g2.labels(matched_label="foobar", node="localhost", timestamp="123").set(12.2)
        g3 = Gauge('target_metric', 'Metric holding labels', ['matched_label', 'extra_label_1', 'extra_label_2'], registry=registry)
        g3.labels(matched_label="foobar", extra_label_1="extra1", extra_label_2="extra2").inc()

        data = generate_latest(registry)

        def get_side_effect(*args, **kwargs):
            if args[0] == 'http://service/prometheus':
                return MagicMock(status_code=200,
                    iter_lines=lambda **kwargs: data.split("\n"),
                    headers={'Content-Type': "text/plain"})

        mock_get.side_effect = get_side_effect

        check1 = self.check.check_map['http://service/prometheus']
        instance = self.instances[0]
        check1.gauge = MagicMock()
        # label_joins is set so there's a dry run
        self.check.check(instance)
        self.check.check(instance)
        check1.gauge.assert_has_calls([
            call('service.cpu', 99.9, ['foo:bar', 'node:localhost', 'origin:test', 'matched_label:foobar', 'extra_label_1:extra1', 'extra_label_2:extra2'], hostname="localhost"),
            call('service.mem', 12.2, ['foo:bar', 'node:localhost', 'matched_label:foobar', 'extra_label_1:extra1', 'extra_label_2:extra2'], hostname="localhost"),
        ], any_order=True)

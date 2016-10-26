# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import unittest
import os

from utils.kubernetes import KubeStateProcessor, NAMESPACE
from utils.prometheus import parse_metric_family

import mock


class TestKubeStateProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Preload all protobuf messages in a dict so we can use during
        unit tests without cycling every time the binary buffer.
        """
        cls.messages = {}
        f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'prometheus', 'protobuf.bin')
        with open(f_name, 'rb') as f:
            for msg in parse_metric_family(f.read()):
                cls.messages[msg.name] = msg

    def setUp(self):
        self.check = mock.MagicMock()
        self.processor = KubeStateProcessor(self.check)

    def test_process(self):
        metric = mock.MagicMock()
        metric.name = 'foo'
        self.processor.process(metric)  # this should never fail

        metric.name = 'a_metric'
        method = mock.MagicMock()
        setattr(self.processor, 'a_metric', method)
        self.processor.process(metric)
        method.assert_called_once()

    def test__eval_metric_condition(self):
        metric = mock.MagicMock(label=list(), gauge=mock.MagicMock(value=1.0))

        # empty label list
        self.assertEqual(self.processor._eval_metric_condition(metric), (None, None))

        # no 'condition' label present
        for name, value in (('foo', 'bar'), ('bar', 'baz')):
            l = mock.MagicMock(value=value)
            l.name = name  # name is a reserved kw in MagicMock constructor
            metric.label.append(l)
        self.assertEqual(self.processor._eval_metric_condition(metric), (None, None))

        # add a condition label
        l = mock.MagicMock(value='true')
        l.name = 'condition'
        metric.label.append(l)
        self.assertEqual(self.processor._eval_metric_condition(metric), ('true', True))

    def test__extract_label_value(self):
        self.assertIsNone(self.processor._extract_label_value('foo', []))

        l1 = mock.MagicMock(value=1)
        l1.name = 'foo'
        l2 = mock.MagicMock(value=2)
        l2.name = 'bar'
        l3 = mock.MagicMock(value=3)
        l3.name = 'bar'
        labels = [l1, l2, l3]
        # in case of labels with the same name (shouldn't happen) return the first occurence
        self.assertEqual(self.processor._extract_label_value('bar', labels), 2)

    def test_kube_node_status_capacity_cpu_cores(self):
        msg = self.messages['kube_node_status_capacity_cpu_cores']
        self.processor.kube_node_status_capacity_cpu_cores(msg)

        expected = [
            (NAMESPACE + '.node.cpu_capacity', 1.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa']),
            (NAMESPACE + '.node.cpu_capacity', 1.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4']),
            (NAMESPACE + '.node.cpu_capacity', 1.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_node_status_capacity_memory_bytes(self):
        msg = self.messages['kube_node_status_capacity_memory_bytes']
        self.processor.kube_node_status_capacity_memory_bytes(msg)

        expected = [
            (NAMESPACE + '.node.memory_capacity', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa']),
            (NAMESPACE + '.node.memory_capacity', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4']),
            (NAMESPACE + '.node.memory_capacity', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_node_status_capacity_pods(self):
        msg = self.messages['kube_node_status_capacity_memory_bytes']
        self.processor.kube_node_status_capacity_pods(msg)

        expected = [
            (NAMESPACE + '.node.pods_capacity', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa']),
            (NAMESPACE + '.node.pods_capacity', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4']),
            (NAMESPACE + '.node.pods_capacity', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_node_status_allocateable_cpu_cores(self):
        msg = self.messages['kube_node_status_allocatable_cpu_cores']
        self.processor.kube_node_status_allocatable_cpu_cores(msg)

        expected = [
            (NAMESPACE + '.node.cpu_allocatable', 1.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa']),
            (NAMESPACE + '.node.cpu_allocatable', 1.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4']),
            (NAMESPACE + '.node.cpu_allocatable', 1.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_node_status_allocateable_memory_bytes(self):
        msg = self.messages['kube_node_status_allocatable_memory_bytes']
        self.processor.kube_node_status_allocatable_memory_bytes(msg)

        expected = [
            (NAMESPACE + '.node.memory_allocatable', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa']),
            (NAMESPACE + '.node.memory_allocatable', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4']),
            (NAMESPACE + '.node.memory_allocatable', 3892240384.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_node_status_allocateable_pods(self):
        msg = self.messages['kube_node_status_allocatable_pods']
        self.processor.kube_node_status_allocatable_pods(msg)

        expected = [
            (NAMESPACE + '.node.pods_allocatable', 110.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa']),
            (NAMESPACE + '.node.pods_allocatable', 110.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4']),
            (NAMESPACE + '.node.pods_allocatable', 110.0, ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_deployment_status_replicas_available(self):
        msg = self.messages['kube_deployment_status_replicas_available']
        self.processor.kube_deployment_status_replicas_available(msg)

        expected = [
            (NAMESPACE + '.deployment.replicas_available', 1.0, ['deployment:heapster-v1.1.0', 'namespace:kube-system']),
            (NAMESPACE + '.deployment.replicas_available', 1.0, ['deployment:hello-node', 'namespace:default']),
            (NAMESPACE + '.deployment.replicas_available', 1.0, ['deployment:kube-state-metrics-deployment', 'namespace:default']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_deployment_status_replicas_unavailable(self):
        msg = self.messages['kube_deployment_status_replicas_unavailable']
        self.processor.kube_deployment_status_replicas_unavailable(msg)

        expected = [
            (NAMESPACE + '.deployment.replicas_unavailable', 0.0, ['deployment:heapster-v1.1.0', 'namespace:kube-system']),
            (NAMESPACE + '.deployment.replicas_unavailable', 0.0, ['deployment:hello-node', 'namespace:default']),
            (NAMESPACE + '.deployment.replicas_unavailable', 0.0, ['deployment:kube-state-metrics-deployment', 'namespace:default']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_deployment_status_replicas_updated(self):
        msg = self.messages['kube_deployment_status_replicas_updated']
        self.processor.kube_deployment_status_replicas_updated(msg)

        expected = [
            (NAMESPACE + '.deployment.replicas_updated', 1.0, ['deployment:heapster-v1.1.0', 'namespace:kube-system']),
            (NAMESPACE + '.deployment.replicas_updated', 1.0, ['deployment:hello-node', 'namespace:default']),
            (NAMESPACE + '.deployment.replicas_updated', 1.0, ['deployment:kube-state-metrics-deployment', 'namespace:default']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_deployment_spec_replicas(self):
        msg = self.messages['kube_deployment_spec_replicas']
        self.processor.kube_deployment_spec_replicas(msg)

        expected = [
            (NAMESPACE + '.deployment.replicas_desired', 1.0, ['deployment:heapster-v1.1.0', 'namespace:kube-system']),
            (NAMESPACE + '.deployment.replicas_desired', 1.0, ['deployment:hello-node', 'namespace:default']),
            (NAMESPACE + '.deployment.replicas_desired', 1.0, ['deployment:kube-state-metrics-deployment', 'namespace:default']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

    def test_kube_node_status_ready(self):
        msg = self.messages['kube_node_status_ready']
        self.processor.kube_node_status_ready(msg)

        expected = [
            ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa'],
            ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4'],
            ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk'],
        ]

        calls = self.check.service_check.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args, kwargs = call[1], call[2]
            self.assertEqual(args[0], NAMESPACE + '.node.ready')
            self.assertEqual(args[1], self.processor.kube_check.OK)
            self.assertEqual(kwargs['tags'], expected[i])

    def test_kube_node_status_out_of_disk(self):
        msg = self.messages['kube_node_status_out_of_disk']
        self.processor.kube_node_status_out_of_disk(msg)

        expected = [
            ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa'],
            ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4'],
            ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk'],
        ]

        calls = self.check.service_check.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args, kwargs = call[1], call[2]
            self.assertEqual(args[0], NAMESPACE + '.node.out_of_disk')
            self.assertEqual(args[1], self.processor.kube_check.OK)
            self.assertEqual(kwargs['tags'], expected[i])

    def test_kube_node_spec_unschedulable(self):
        msg = self.messages['kube_node_spec_unschedulable']
        self.processor.kube_node_spec_unschedulable(msg)

        expected = [
            (NAMESPACE + '.node.unschedulable', 1,
             ['node:gke-cluster-massi-agent59-default-pool-6087cc76-9cfa', 'status:available']),
            (NAMESPACE + '.node.unschedulable', 1,
             ['node:gke-cluster-massi-agent59-default-pool-6087cc76-aah4', 'status:available']),
            (NAMESPACE + '.node.unschedulable', 1,
             ['node:gke-cluster-massi-agent59-default-pool-6087cc76-fgnk', 'status:available']),
        ]

        calls = self.check.gauge.mock_calls
        self.assertEqual(len(calls), 3)
        for i, call in enumerate(calls):
            args = call[1]
            self.assertEqual(args, expected[i])

# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from tests.checks.common import AgentCheckTest
from utils.kubernetes import NAMESPACE

import mock


class TestKubernetesState(AgentCheckTest):

    CHECK_NAME = 'kubernetes_state'

    def test__get_kube_state(self):
        headers = {
            'accept': 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited',
            'accept-encoding': 'gzip',
        }
        url = 'https://example.com'

        self.load_check({'instances': [{'host': 'foo'}]})
        with mock.patch('{}.requests'.format(self.check.__module__)) as r:
            self.check._get_kube_state(url)
            r.get.assert_called_once_with(url, headers=headers)

    def test_kube_state(self):
        mocked = mock.MagicMock()
        mocks = {
            '_perform_kubelet_checks': mock.MagicMock(),
            '_update_metrics': mock.MagicMock(),
            '_update_kube_state_metrics': mocked,
        }
        config = {'instances': [{'host': 'foo', 'kube_state_url': 'https://example.com:12345'}]}
        self.run_check(config, force_reload=True, mocks=mocks)
        mocked.assert_called_once()

    def test__update_kube_state_metrics(self):
        f_name = os.path.join(os.path.dirname(__file__), '..', '..', 'core', 'fixtures', 'prometheus', 'protobuf.bin')
        mocked = mock.MagicMock()
        with open(f_name, 'rb') as f:
            mocked.return_value = f.read()

        mocks = {
            '_perform_kubelet_checks': mock.MagicMock(),
            '_update_metrics': mock.MagicMock(),
            'kubeutil': mock.MagicMock(),
            '_get_kube_state': mocked,
        }

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
            }]
        }

        self.run_check(config, mocks=mocks)

        self.assertServiceCheck(NAMESPACE + '.node.ready', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.out_of_disk', self.check.OK)

        self.assertMetric(NAMESPACE + '.node.cpu_capacity')
        self.assertMetric(NAMESPACE + '.node.memory_capacity')
        self.assertMetric(NAMESPACE + '.node.pods_capacity')
        self.assertMetric(NAMESPACE + '.node.cpu_allocatable')
        self.assertMetric(NAMESPACE + '.node.memory_allocatable')
        self.assertMetric(NAMESPACE + '.node.pods_allocatable')
        self.assertMetric(NAMESPACE + '.node.unschedulable')
        self.assertMetric(NAMESPACE + '.deployment.replicas_available')
        self.assertMetric(NAMESPACE + '.deployment.replicas_unavailable')
        self.assertMetric(NAMESPACE + '.deployment.replicas_desired')
        self.assertMetric(NAMESPACE + '.deployment.replicas_updated')

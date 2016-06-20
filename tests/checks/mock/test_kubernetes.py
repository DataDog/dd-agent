# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# stdlib
import mock
import unittest
import os

# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck
from utils.kubeutil import KubeUtil, is_k8s, get_procfs_netroute

CPU = "CPU"
MEM = "MEM"
FS = "fs"
NET = "net"
NET_ERRORS = "net_errors"
DISK = "disk"
DISK_USAGE = "disk_usage"
PODS = "pods"
LIM = "limits"
REQ = "requests"

METRICS = [
    ('kubernetes.memory.usage', MEM),
    ('kubernetes.filesystem.usage', FS),
    ('kubernetes.filesystem.usage_pct', FS),
    ('kubernetes.cpu.usage.total', CPU),
    ('kubernetes.network.tx_bytes', NET),
    ('kubernetes.network.rx_bytes', NET),
    ('kubernetes.network_errors', NET_ERRORS),
    ('kubernetes.diskio.io_service_bytes.stats.total', DISK),
    ('kubernetes.filesystem.usage_pct', DISK_USAGE),
    ('kubernetes.filesystem.usage', DISK_USAGE),
    ('kubernetes.pods.running', PODS),
    ('kubernetes.cpu.limits', LIM),
    ('kubernetes.cpu.requests', REQ),
    ('kubernetes.memory.limits', LIM),
    ('kubernetes.memory.requests', REQ),
]


class TestKubernetes(AgentCheckTest):

    CHECK_NAME = 'kubernetes'

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.1.json")))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False)))
    def test_fail_1_1(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo"}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)
        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL, tags=None, count=1)

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.1.json")))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False)))
    def test_metrics_1_1(self, *args):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_perform_kubelet_checks': lambda x: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False
                }
            ]
        }
        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        expected_tags = [
            (['container_name:/kubelet', 'pod_name:no_pod'], [MEM, CPU, NET, DISK]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'container_name:k8s_POD.e4cc795_propjoe-dhdzk_default_ba151259-36e0-11e5-84ce-42010af01c62_ef0ed5f9', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:/kube-proxy', 'pod_name:no_pod'], [MEM, CPU, NET]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_POD.2688308a_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_295f14ff', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:/docker-daemon', 'pod_name:no_pod'], [MEM, CPU, DISK, NET]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_etcd.2e44beff_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_e3e504ad', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:fluentd-cloud-logging-kubernetes-minion', 'kube_namespace:kube-system', 'container_name:k8s_POD.e4cc795_fluentd-cloud-logging-kubernetes-minion-mu4w_kube-system_d0feac1ad02da9e97c4bf67970ece7a1_49dd977d', 'pod_name:kube-system/fluentd-cloud-logging-kubernetes-minion-mu4w'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_skydns.1e752dc0_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_7c1345a1', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:/', 'pod_name:no_pod'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['container_name:/system/docker', 'pod_name:no_pod'], [MEM, CPU, DISK, NET]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'container_name:k8s_propjoe.21f63023_propjoe-dhdzk_default_ba151259-36e0-11e5-84ce-42010af01c62_19879457', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:/system', 'pod_name:no_pod'], [MEM, CPU, NET, DISK]),
            (['kube_replication_controller:kube-ui-v1', 'kube_namespace:kube-system', 'container_name:k8s_POD.3b46e8b9_kube-ui-v1-sv2sq_kube-system_b7e8f250-3619-11e5-84ce-42010af01c62_209ed1dc', 'pod_name:kube-system/kube-ui-v1-sv2sq'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'container_name:k8s_kube2sky.1afa6a47_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_624bc34c', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'container_name:k8s_POD.e4cc795_propjoe-lkc3l_default_3a9b1759-4055-11e5-84ce-42010af01c62_45d1185b', 'pod_name:default/propjoe-lkc3l'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:haproxy-6db79c7bbcac01601ac35bcdb18868b3', 'kube_namespace:default', 'container_name:k8s_POD.e4cc795_haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la_default_86527bf8-36cd-11e5-84ce-42010af01c62_5ad59bf3', 'pod_name:default/haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:haproxy-6db79c7bbcac01601ac35bcdb18868b3', 'kube_namespace:default', 'container_name:k8s_haproxy.69b6303b_haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la_default_86527bf8-36cd-11e5-84ce-42010af01c62_a35b9731', 'pod_name:default/haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-ui-v1','kube_namespace:kube-system', 'container_name:k8s_kube-ui.c17839c_kube-ui-v1-sv2sq_kube-system_b7e8f250-3619-11e5-84ce-42010af01c62_d2b9aa90', 'pod_name:kube-system/kube-ui-v1-sv2sq'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe','kube_namespace:default', 'container_name:k8s_propjoe.21f63023_propjoe-lkc3l_default_3a9b1759-4055-11e5-84ce-42010af01c62_9fe8b7b0', 'pod_name:default/propjoe-lkc3l'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8','kube_namespace:kube-system', 'container_name:k8s_healthz.4469a25d_kube-dns-v8-smhcb_kube-system_b80ffab3-3619-11e5-84ce-42010af01c62_241c34d1', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:fluentd-cloud-logging-kubernetes-minion','kube_namespace:kube-system', 'container_name:k8s_fluentd-cloud-logging.7721935b_fluentd-cloud-logging-kubernetes-minion-mu4w_kube-system_d0feac1ad02da9e97c4bf67970ece7a1_2c3c0879', 'pod_name:kube-system/fluentd-cloud-logging-kubernetes-minion-mu4w'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['container_name:dd-agent', 'pod_name:no_pod'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:l7-lb-controller'], [PODS]),
            (['kube_replication_controller:redis-slave'], [PODS]),
            (['kube_replication_controller:frontend'], [PODS]),
            (['kube_replication_controller:heapster-v11'], [PODS]),
        ]
        for m, _type in METRICS:
            for tags, types in expected_tags:
                if _type in types:
                    self.assertMetric(m, count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.1.json")))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False)))
    def test_historate_1_1(self, *args):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_perform_kubelet_checks': lambda x: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False,
                    "use_histogram": True,
                }
            ]
        }
        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_tags = [
            (['pod_name:no_pod'], [MEM, CPU, NET, DISK, DISK_USAGE, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:fluentd-cloud-logging-kubernetes-minion', 'kube_namespace:kube-system', 'pod_name:kube-system/fluentd-cloud-logging-kubernetes-minion-mu4w'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['kube_replication_controller:kube-dns-v8', 'kube_namespace:kube-system', 'pod_name:kube-system/kube-dns-v8-smhcb'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'pod_name:default/propjoe-dhdzk'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:kube-ui-v1','kube_namespace:kube-system', 'pod_name:kube-system/kube-ui-v1-sv2sq'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:propjoe', 'kube_namespace:default', 'pod_name:default/propjoe-lkc3l'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:haproxy-6db79c7bbcac01601ac35bcdb18868b3', 'kube_namespace:default', 'pod_name:default/haproxy-6db79c7bbcac01601ac35bcdb18868b3-rr7la'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['kube_replication_controller:l7-lb-controller'], [PODS]),
            (['kube_replication_controller:redis-slave'], [PODS]),
            (['kube_replication_controller:frontend'], [PODS]),
            (['kube_replication_controller:heapster-v11'], [PODS]),
        ]

        for m, _type in METRICS:
            for m_suffix in metric_suffix:
                for tags, types in expected_tags:
                    if _type in types:
                        self.assertMetric("{0}.{1}".format(m, m_suffix), count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.2.json")))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False)))
    def test_fail_1_2(self, *args):
        # To avoid the disparition of some gauges during the second check
        config = {
            "instances": [{"host": "foo"}]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check(config, force_reload=True)
        self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL)

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.2.json")))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False)))
    def test_metrics_1_2(self, *args):
        mocks = {
            '_perform_kubelet_checks': lambda x: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False
                }
            ]
        }
        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        expected_tags = [
            (['container_name:/kubelet', 'pod_name:no_pod'], [MEM, CPU, NET, DISK]),
            (['container_name:k8s_POD.35220667_dd-agent-1rxlh_default_12c7be82-33ca-11e6-ac8f-42010af00003_f5cf585f',
              'pod_name:default/dd-agent-1rxlh', 'kube_namespace:default', 'kube_app:dd-agent',
              'kube_replication_controller:dd-agent'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:/', 'pod_name:no_pod'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['container_name:/system', 'pod_name:no_pod'], [MEM, CPU, NET, DISK]),
            (['container_name:k8s_dd-agent.7b520f3f_dd-agent-1rxlh_default_12c7be82-33ca-11e6-ac8f-42010af00003_321fecb4',
              'pod_name:default/dd-agent-1rxlh', 'kube_namespace:default', 'kube_app:dd-agent',
              'kube_replication_controller:dd-agent'], [LIM, REQ, MEM, CPU, NET, DISK, DISK_USAGE]),
            (['kube_replication_controller:dd-agent'], [PODS]),
            ([], [LIM, REQ])  # container from kubernetes api doesn't have a corresponding entry in Cadvisor
        ]

        for m, _type in METRICS:
            for tags, types in expected_tags:
                if _type in types:
                    self.assertMetric(m, count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics',
                side_effect=lambda: json.loads(Fixtures.read_file("metrics_1.2.json")))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False)))
    def test_historate_1_2(self, *args):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_perform_kubelet_checks': lambda x: None,
        }
        config = {
            "instances": [
                {
                    "host": "foo",
                    "enable_kubelet_checks": False,
                    "use_histogram": True,
                }
            ]
        }

        # Can't use run_check_twice due to specific metrics
        self.run_check_twice(config, mocks=mocks, force_reload=True)

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_tags = [
            (['pod_name:default/dd-agent-1rxlh', 'kube_namespace:default', 'kube_app:dd-agent',
              'kube_replication_controller:dd-agent'], [MEM, CPU, NET, DISK, NET_ERRORS]),
        ]

        for m, _type in METRICS:
            for m_suffix in metric_suffix:
                for tags, types in expected_tags:
                    if _type in types:
                        self.assertMetric("{0}.{1}".format(m, m_suffix), count=1, tags=tags)

        self.coverage_report()

    @mock.patch('utils.kubeutil.KubeUtil.get_node_info',
                side_effect=lambda: ('Foo', 'Bar'))
    @mock.patch('utils.kubeutil.KubeUtil.filter_pods_list',
                side_effect=lambda x, y: x)
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_json_auth',
                side_effect=lambda x,y: json.loads(Fixtures.read_file("events.json", string_escape=False)))
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_metrics')
    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list',
                side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False)))
    def test_events(self, *args):
        # default value for collect_events is False
        config = {'instances': [{'host': 'foo'}]}
        self.run_check(config)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=0, exact_match=False)

        # again, with the feature enabled
        config = {'instances': [{'host': 'bar', 'collect_events': True}]}
        self.run_check(config, force_reload=True)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=1, exact_match=False)

        # again, now the timestamp is set and the event is discarded b/c too old
        self.run_check(config)
        self.assertEvent('hello-node-47289321-91tfd Scheduled on Bar', count=0, exact_match=False)


class TestKubeutil(unittest.TestCase):
    def setUp(self):
        self.kubeutil = KubeUtil()

    @mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=['foo'])
    @mock.patch('utils.kubeutil.KubeUtil.extract_kube_labels')
    def test_get_kube_labels(self, extract_kube_labels, retrieve_pods_list):
        self.kubeutil.get_kube_labels(excluded_keys='bar')
        retrieve_pods_list.assert_called_once()
        extract_kube_labels.assert_called_once_with('foo', excluded_keys='bar')

    def test_extract_kube_labels(self):
        """
        Test with both 1.1 and 1.2 version payloads
        """
        res = self.kubeutil.extract_kube_labels({}, ['foo'])
        self.assertEqual(len(res), 0)

        pods = json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))
        res = self.kubeutil.extract_kube_labels(pods, ['foo'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 8)
        res = self.kubeutil.extract_kube_labels(pods, ['k8s-app'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 6)

        pods = json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))
        res = self.kubeutil.extract_kube_labels(pods, ['foo'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 5)
        res = self.kubeutil.extract_kube_labels(pods, ['k8s-app'])
        labels = set(inn for out in res.values() for inn in out)
        self.assertEqual(len(labels), 3)

    def test_extract_meta(self):
        """
        Test with both 1.1 and 1.2 version payloads
        """
        res = self.kubeutil.extract_meta({}, 'foo')
        self.assertEqual(len(res), 0)

        pods = json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))
        res = self.kubeutil.extract_meta(pods, 'foo')
        self.assertEqual(len(res), 0)
        res = self.kubeutil.extract_meta(pods, 'uid')
        self.assertEqual(len(res), 6)

        pods = json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))
        res = self.kubeutil.extract_meta(pods, 'foo')
        self.assertEqual(len(res), 0)
        res = self.kubeutil.extract_meta(pods, 'uid')
        self.assertEqual(len(res), 4)

    @mock.patch('utils.kubeutil.retrieve_json')
    def test_retrieve_pods_list(self, retrieve_json):
        self.kubeutil.retrieve_pods_list()
        retrieve_json.assert_called_once_with(self.kubeutil.pods_list_url)

    @mock.patch('utils.kubeutil.retrieve_json')
    def test_retrieve_metrics(self, retrieve_json):
        self.kubeutil.retrieve_metrics()
        retrieve_json.assert_called_once_with(self.kubeutil.metrics_url)

    def test_filter_pods_list(self):
        """
        Test with both 1.1 and 1.2 version payloads
        """
        res = self.kubeutil.filter_pods_list({}, 'foo')
        self.assertEqual(len(res.get('items')), 0)

        pods = json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))
        res = self.kubeutil.filter_pods_list(pods, '10.240.0.9')
        self.assertEqual(len(res.get('items')), 5)

        pods = json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))
        res = self.kubeutil.filter_pods_list(pods, 'foo')
        self.assertEqual(len(res.get('items')), 0)

        pods = json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))
        res = self.kubeutil.filter_pods_list(pods, '10.142.0.4')
        self.assertEqual(len(res.get('items')), 2)

        pods = json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))
        res = self.kubeutil.filter_pods_list(pods, 'foo')
        self.assertEqual(len(res.get('items')), 0)

    @mock.patch('utils.kubeutil.requests')
    def test_retrieve_json_auth(self, r):
        self.kubeutil.retrieve_json_auth('url', 'foo_tok')
        r.get.assert_called_once_with('url', verify=False, timeout=10, headers={'Authorization': 'Bearer foo_tok'})

        self.kubeutil.CA_CRT_PATH = __file__
        self.kubeutil.retrieve_json_auth('url', 'foo_tok')
        r.get.assert_called_with('url', verify=__file__, timeout=10, headers={'Authorization': 'Bearer foo_tok'})

    def test_get_node_info(self):
        with mock.patch('utils.kubeutil.KubeUtil._fetch_host_data') as f:
            self.kubeutil.get_node_info()
            f.assert_called_once()

            f.reset_mock()

            self.kubeutil._node_ip = 'foo'
            self.kubeutil._node_name = 'bar'
            ip, name = self.kubeutil.get_node_info()
            self.assertEqual(ip, 'foo')
            self.assertEqual(name, 'bar')
            f.assert_not_called()

    def test__fetch_host_data(self):
        """
        Test with both 1.1 and 1.2 version payloads
        """
        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list') as mock_pods:
            self.kubeutil.host_name = 'kube-dns-v11-63tae'

            mock_pods.return_value = json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))
            self.kubeutil._fetch_host_data()
            self.assertEqual(self.kubeutil._node_ip, '10.142.0.4')
            self.assertEqual(self.kubeutil._node_name, 'gke-cluster-remi-62c0dd29-node-29lx')

            mock_pods.return_value = json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))
            self.kubeutil._fetch_host_data()
            self.assertEqual(self.kubeutil._node_ip, '10.142.0.4')
            self.assertEqual(self.kubeutil._node_name, 'gke-cluster-remi-62c0dd29-node-29lx')

    def test__get_default_router(self):
        with mock.patch('utils.kubeutil.get_procfs_netroute') as mock_procfs:
            mock_procfs.return_value = Fixtures.file('proc_net_route.txt')
            self.assertEqual(KubeUtil._get_default_router(), '10.8.2.1')

    def test_get_auth_token(self):
        KubeUtil.AUTH_TOKEN_PATH = '/foo/bar'
        self.assertIsNone(KubeUtil.get_auth_token())
        KubeUtil.AUTH_TOKEN_PATH = Fixtures.file('proc_net_route.txt')  # any file could do the trick
        self.assertIsNotNone(KubeUtil.get_auth_token())

    def test_is_k8s(self):
        os.unsetenv('KUBERNETES_PORT')
        self.assertFalse(is_k8s())
        os.environ['KUBERNETES_PORT'] = '999'
        self.assertTrue(is_k8s())

    def test_get_procfs_netroute(self):
        self.assertEqual(get_procfs_netroute(), '/proc/net/route')

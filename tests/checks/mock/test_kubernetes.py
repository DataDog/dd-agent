# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# stdlib
import mock

# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck

CPU = "CPU"
MEM = "MEM"
FS = "fs"
NET = "net"
NET_ERRORS = "net_errors"
DISK = "disk"
DISK_USAGE = "disk_usage"
PODS = "pods"

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
]


class TestKubernetes(AgentCheckTest):

    CHECK_NAME = 'kubernetes'

    def test_fail_1_1(self):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_retrieve_metrics': lambda x: json.loads(Fixtures.read_file("metrics_1.1.json")),
        }
        config = {
            "instances": [{"host": "foo"}]
        }

        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))):
            with mock.patch('utils.dockerutil.DockerUtil.get_hostname', side_effect=lambda: 'foo'):
                # Can't use run_check_twice due to specific metrics
                self.run_check(config, mocks=mocks, force_reload=True)
                self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL, tags=None, count=1)

    def test_metrics_1_1(self):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_retrieve_metrics': lambda x: json.loads(Fixtures.read_file("metrics_1.1.json")),
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
        # parts of the json returned by the kubelet api is escaped, keep it untouched
        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))):
            with mock.patch('utils.dockerutil.DockerUtil.get_hostname', side_effect=lambda: 'foo'):
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

    def test_historate_1_1(self):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_retrieve_metrics': lambda x: json.loads(Fixtures.read_file("metrics_1.1.json")),
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

        # parts of the json returned by the kubelet api is escaped, keep it untouched
        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.1.json", string_escape=False))):
            with mock.patch('utils.dockerutil.DockerUtil.get_hostname', side_effect=lambda: 'foo'):
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


    def test_fail_1_2(self):
        # To avoid the disparition of some gauges during the second check
        mocks = {'_retrieve_metrics': lambda x: json.loads(Fixtures.read_file("metrics_1.2.json"))}
        config = {
            "instances": [{"host": "foo"}]
        }

        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))):
            with mock.patch('utils.dockerutil.DockerUtil.get_hostname', side_effect=lambda: 'foo'):
                # Can't use run_check_twice due to specific metrics
                self.run_check(config, mocks=mocks, force_reload=True)
                self.assertServiceCheck("kubernetes.kubelet.check", status=AgentCheck.CRITICAL)


    def test_metrics_1_2(self):
        mocks = {
            '_retrieve_metrics': lambda x: json.loads(Fixtures.read_file("metrics_1.2.json")),
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
        # parts of the json returned by the kubelet api is escaped, keep it untouched
        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))):
            with mock.patch('utils.dockerutil.DockerUtil.get_hostname', side_effect=lambda: 'foo'):
                # Can't use run_check_twice due to specific metrics
                self.run_check_twice(config, mocks=mocks, force_reload=True)

        expected_tags = [
            (['container_name:/kubelet', 'pod_name:no_pod'], [MEM, CPU, NET, DISK]),
            (['container_name:k8s_POD.e2764897_kube-dns-v11-63tae_kube-system_5754714c-0054-11e6-9a89-42010af00098_c33e4b64', 'pod_name:kube-system/kube-dns-v11-63tae', 'kube_namespace:kube-system', 'kube_k8s-app:kube-dns', 'kube_version:v11', 'kube_kubernetes.io/cluster-service:true', 'kube_replication_controller:kube-dns-v11'], [MEM, CPU, FS, NET, NET_ERRORS]),
            (['container_name:k8s_dd-agent.67c1e3c5_dd-agent-idydc_default_adecdd57-f5c3-11e5-8f7c-42010af00098_5154bb06', 'pod_name:default/dd-agent-idydc', 'kube_namespace:default', 'kube_app:dd-agent', 'kube_replication_controller:dd-agent'], [MEM, CPU, FS, NET, DISK]),
            (['container_name:/', 'pod_name:no_pod'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            (['container_name:/docker-daemon', 'pod_name:no_pod'], [MEM, CPU, DISK, NET]),
            (['container_name:k8s_skydns.7ad23ad1_kube-dns-v11-63tae_kube-system_5754714c-0054-11e6-9a89-42010af00098_b082387b', 'pod_name:kube-system/kube-dns-v11-63tae', 'kube_namespace:kube-system', 'kube_k8s-app:kube-dns', 'kube_version:v11', 'kube_kubernetes.io/cluster-service:true', 'kube_replication_controller:kube-dns-v11'], [MEM, CPU, FS, NET]),

            ([u'container_name:/system', 'pod_name:no_pod'], [MEM, CPU, NET, DISK]),

            ([u'kube_k8s-app:kube-dns', u'kube_namespace:kube-system', u'kube_kubernetes.io/cluster-service:true', u'kube_replication_controller:kube-dns-v11', u'pod_name:kube-system/kube-dns-v11-63tae', u'kube_version:v11', u'container_name:k8s_kube2sky.8cbc016c_kube-dns-v11-63tae_kube-system_5754714c-0054-11e6-9a89-42010af00098_d6df3862'], [MEM, CPU, FS, NET]),
            ([u'kube_namespace:default', u'kube_app:dd-agent', u'kube_replication_controller:dd-agent', u'container_name:k8s_POD.35220667_dd-agent-idydc_default_adecdd57-f5c3-11e5-8f7c-42010af00098_e2c005a0', u'pod_name:default/dd-agent-idydc'], [MEM, CPU, FS, NET, NET_ERRORS]),
            ([u'kube_k8s-app:kube-dns', u'kube_namespace:kube-system', u'kube_kubernetes.io/cluster-service:true', u'kube_replication_controller:kube-dns-v11', u'pod_name:kube-system/kube-dns-v11-63tae', u'kube_version:v11', u'container_name:k8s_etcd.81a33530_kube-dns-v11-63tae_kube-system_5754714c-0054-11e6-9a89-42010af00098_e811864e'], [MEM, CPU, FS, DISK, NET]),
            ([u'kube_namespace:kube-system', u'pod_name:kube-system/kube-proxy-gke-cluster-remi-62c0dd29-node-29lx', u'container_name:k8s_kube-proxy.cf23f4be_kube-proxy-gke-cluster-remi-62c0dd29-node-29lx_kube-system_f70c43857a22d5495bf204918d5ab984_4e315ef3', u'kube_replication_controller:kube-proxy-gke-cluster-remi-62c0dd29-node'], [MEM, CPU, FS, NET, DISK]),
            ([u'kube_namespace:kube-system', u'pod_name:kube-system/fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node-29lx', u'kube_k8s-app:fluentd-logging', u'container_name:k8s_fluentd-cloud-logging.fe59dd68_fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node-29lx_kube-system_da7e41ef0372c29c65a24b417b5dd69f_3cacfb32', u'kube_replication_controller:fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node'], [MEM, CPU, FS, NET]),
            ([u'kube_namespace:kube-system', u'container_name:k8s_POD.6059dfa2_kube-proxy-gke-cluster-remi-62c0dd29-node-29lx_kube-system_f70c43857a22d5495bf204918d5ab984_e17ace7a', u'pod_name:kube-system/kube-proxy-gke-cluster-remi-62c0dd29-node-29lx', u'kube_replication_controller:kube-proxy-gke-cluster-remi-62c0dd29-node'], [MEM, CPU, FS, NET, NET_ERRORS]),
            ([u'kube_k8s-app:kube-dns', u'kube_namespace:kube-system', u'kube_kubernetes.io/cluster-service:true', u'container_name:k8s_healthz.4039147e_kube-dns-v11-63tae_kube-system_5754714c-0054-11e6-9a89-42010af00098_d8e1d132', u'kube_replication_controller:kube-dns-v11', u'pod_name:kube-system/kube-dns-v11-63tae', u'kube_version:v11'], [MEM, CPU, FS, NET]),
            ([u'kube_namespace:kube-system', u'pod_name:kube-system/fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node-29lx', u'kube_k8s-app:fluentd-logging', u'container_name:k8s_POD.6059dfa2_fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node-29lx_kube-system_da7e41ef0372c29c65a24b417b5dd69f_b4d7ed62', u'kube_replication_controller:fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node'], [MEM, CPU, FS, NET, NET_ERRORS]),

            (['kube_replication_controller:kube-dns-v11'], [PODS]),
            (['kube_replication_controller:dd-agent'], [PODS]),
        ]

        for m, _type in METRICS:
            for tags, types in expected_tags:
                if _type in types:
                    self.assertMetric(m, count=1, tags=tags)


        self.coverage_report()

    def test_historate_1_2(self):
        # To avoid the disparition of some gauges during the second check
        mocks = {
            '_retrieve_metrics': lambda x: json.loads(Fixtures.read_file("metrics_1.2.json")),
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

        # parts of the json returned by the kubelet api is escaped, keep it untouched
        with mock.patch('utils.kubeutil.KubeUtil.retrieve_pods_list', side_effect=lambda: json.loads(Fixtures.read_file("pods_list_1.2.json", string_escape=False))):
            with mock.patch('utils.dockerutil.DockerUtil.get_hostname', side_effect=lambda: 'foo'):
                # Can't use run_check_twice due to specific metrics
                self.run_check_twice(config, mocks=mocks, force_reload=True)

        metric_suffix = ["count", "avg", "median", "max", "95percentile"]

        expected_tags = [
            (['pod_name:kube-system/kube-dns-v11-63tae', 'kube_namespace:kube-system', 'kube_k8s-app:kube-dns', 'kube_version:v11', 'kube_kubernetes.io/cluster-service:true', 'kube_replication_controller:kube-dns-v11'], [MEM, CPU, FS, DISK, NET, NET_ERRORS]),
            (['pod_name:default/dd-agent-idydc', 'kube_namespace:default', 'kube_app:dd-agent', 'kube_replication_controller:dd-agent'], [MEM, CPU, FS, NET, DISK]),
            (['pod_name:no_pod'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),

            ([u'kube_namespace:default', u'kube_app:dd-agent', u'kube_replication_controller:dd-agent', u'pod_name:default/dd-agent-idydc'], [MEM, CPU, FS, NET, NET_ERRORS]),
            ([u'kube_namespace:kube-system', u'pod_name:kube-system/kube-proxy-gke-cluster-remi-62c0dd29-node-29lx', u'kube_replication_controller:kube-proxy-gke-cluster-remi-62c0dd29-node'], [MEM, CPU, FS, NET, NET_ERRORS, DISK]),
            ([u'kube_namespace:kube-system', u'pod_name:kube-system/fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node-29lx', u'kube_k8s-app:fluentd-logging', u'kube_replication_controller:fluentd-cloud-logging-gke-cluster-remi-62c0dd29-node'], [MEM, CPU, FS, NET, NET_ERRORS]),

            (['kube_replication_controller:kube-dns-v11'], [PODS]),
            (['kube_replication_controller:dd-agent'], [PODS]),
        ]

        for m, _type in METRICS:
            for m_suffix in metric_suffix:
                for tags, types in expected_tags:
                    if _type in types:
                        self.assertMetric("{0}.{1}".format(m, m_suffix), count=1, tags=tags)

        self.coverage_report()

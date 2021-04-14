# stdlib
import json
import os.path
import unittest

# 3rd party
from mock import patch

# project
from utils.kubernetes import KubeUtil
from .test_orchestrator import MockResponse


class KubeTestCase(unittest.TestCase):
    # Patch _locate_kubelet that is used by KubeUtil.__init__
    def setUp(self):
        with patch.object(KubeUtil, '_locate_kubelet', return_value='http://localhost:10255'):
            self.kube = KubeUtil()
            self.kube.__init__()  # It's a singleton, force re-init

    def tearDown(self):
        self.kube = None

    @classmethod
    def _load_json_array(cls, names):
        json_array = []
        for filename in names:
            path = os.path.join(os.path.dirname(__file__), 'fixtures', 'kubeutil', filename)
            with open(path) as data_file:
                json_array.append(json.load(data_file))
        return json_array

    @classmethod
    def _load_resp_array(cls, names):
        json_array = cls._load_json_array(names)
        return map(lambda x: MockResponse(x, 200), json_array)


class TestKubeUtilInit(KubeTestCase):
    @patch.dict(os.environ, {'KUBERNETES_POD_NAME': 'test'})
    def test_pod_name(self):
        with patch.object(KubeUtil, '_locate_kubelet', return_value='http://localhost:10255'):
            kube = KubeUtil()
            kube.__init__()
            self.assertEqual('test', kube.pod_name)


class TestKubeUtilDeploymentTag(KubeTestCase):
    def test_deployment_name_nominal(self):
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-2891696001'))
        self.assertEqual('front-end', self.kube.get_deployment_for_replicaset('front-end-2891696001'))

    def test_deployment_illegal_name(self):
        self.assertIsNone(self.kube.get_deployment_for_replicaset('frontend2891696001'))
        self.assertIsNone(self.kube.get_deployment_for_replicaset('-frontend2891696001'))
        self.assertIsNone(self.kube.get_deployment_for_replicaset('manually-created'))
        # New 1.8+ names are consonants + numbers suffix, undetermined lenght. Let's take 2 as the cutoff lenght
        self.assertIsNone(self.kube.get_deployment_for_replicaset('frontend-5f'))
        # Vowels are not allowed in 1.8+ format
        self.assertIsNone(self.kube.get_deployment_for_replicaset('frontend-56a89cfff7'))

    def test_deployment_name_k8s_1_8(self):
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-56c89cfff7'))
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-56c'))
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-56c89cff'))
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-56c89cfff7c2'))

        self.assertEqual('front-end', self.kube.get_deployment_for_replicaset('front-end-768dd754b7'))


class TestKubeUtilCreatorTags(KubeTestCase):
    """
    Creator Tags tests for k8 version < 1.9: getting them from the annotation
    """
    @classmethod
    def _fake_pod(cls, creator_kind, creator_name):
        payload = '{"reference": {"kind":"%s", "name":"%s"}}' % (creator_kind, creator_name)
        return {'annotations': {'kubernetes.io/created-by': payload}}

    def test_with_replicaset(self):
        self.assertEqual(['kube_replica_set:test-5432', 'kube_deployment:test'],
                         self.kube.get_pod_creator_tags(self._fake_pod("ReplicaSet", "test-5432")))

    def test_with_statefulset(self):
        self.assertEqual(['kube_stateful_set:test-5432'],
                         self.kube.get_pod_creator_tags(self._fake_pod("StatefulSet", "test-5432")))

    def test_with_legacy_repcontroller(self):
        self.assertEqual(['kube_daemon_set:test', 'kube_replication_controller:test'],
                         self.kube.get_pod_creator_tags(self._fake_pod("DaemonSet", "test"), True))

    def test_with_unknown(self):
        self.assertEqual([], self.kube.get_pod_creator_tags(self._fake_pod("Unknown", "test")))

    def test_invalid_input(self):
        self.assertEqual([], self.kube.get_pod_creator_tags({}))


class TestKubeUtilCreatorTagsNoAnnotation(KubeTestCase):
    """
    Creator Tags tests for k8 version >= 1.9: getting them from the metadata 'ownerReferences'
    """
    @classmethod
    def _fake_pod(cls, creator_kind, creator_name):
        owner_references_entry = [{'kind': creator_kind, 'name': creator_name}]
        return {'ownerReferences': owner_references_entry}

    def test_with_replicaset(self):
        self.assertEqual(['kube_replica_set:test-5432', 'kube_deployment:test'],
                         self.kube.get_pod_creator_tags(self._fake_pod("ReplicaSet", "test-5432")))

    def test_with_statefulset(self):
        self.assertEqual(['kube_stateful_set:test-5432'],
                         self.kube.get_pod_creator_tags(self._fake_pod("StatefulSet", "test-5432")))

    def test_with_legacy_repcontroller(self):
        self.assertEqual(['kube_daemon_set:test', 'kube_replication_controller:test'],
                         self.kube.get_pod_creator_tags(self._fake_pod("DaemonSet", "test"), True))

    def test_with_unknown(self):
        self.assertEqual([], self.kube.get_pod_creator_tags(self._fake_pod("Unknown", "test")))

    def test_invalid_input(self):
        self.assertEqual([], self.kube.get_pod_creator_tags({}))


class TestKubeGetNodeInfo(KubeTestCase):
    @staticmethod
    def mocked_requests_get_without_agent_but_ok(*args, **kwargs):
        return MockResponse({
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {},
            "items": [
                # Static Pod
                {
                    "metadata": {
                        "name": "nginx0-cluster-pool-2-66d4cbf5-z9d1",
                        "namespace": "default",
                    },
                    "spec": {
                        "nodeName": "cluster-pool-2-66d4cbf5-z9d1",
                    },
                    "status": {
                        "phase": "Running",
                        "podIP": "10.20.5.13",
                    }
                },
                # apiserver Pod on hostNetwork
                {
                    "metadata": {
                        "name": "fluentd-gcp-v2.0.9-07l3b",
                        "generateName": "fluentd-gcp-v2.0.9-",
                        "namespace": "kube-system",
                    },
                    "spec": {
                        "nodeName": "cluster-pool-2-66d4cbf5-z9d1",
                        "hostNetwork": True,
                    },
                    "status": {
                        "phase": "Running",
                        "hostIP": "10.132.0.22",
                        "podIP": "10.132.0.22",
                    }
                },
                # apiserver Pod
                {
                    "metadata": {
                        "name": "t1-2306965351-dg611",
                        "generateName": "t1-2306965351-",
                        "namespace": "default",
                    },
                    "spec": {
                        "nodeName": "cluster-pool-2-66d4cbf5-z9d1",
                    },
                    "status": {
                        "phase": "Running",
                        "hostIP": "10.132.0.22",
                        "podIP": "10.20.5.12",
                    }
                }
            ]
        }, 200)

    @staticmethod
    def mocked_requests_get_empty(*args, **kwargs):
        return MockResponse({
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {},
            "items": []}, 200)

    @staticmethod
    def mocked_requests_get_without_agent_but_only_node_name(*args, **kwargs):
        return MockResponse({
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {},
            "items": [
                # Static Pod
                {
                    "metadata": {
                        "name": "nginx0-cluster-pool-2-66d4cbf5-z9d1",
                        "namespace": "default",
                    },
                    "spec": {
                        "nodeName": "cluster-pool-2-66d4cbf5-z9d1",
                    },
                    "status": {
                        "phase": "Running",
                        "podIP": "10.20.5.13",
                    }
                }]}, 200)

    @staticmethod
    def mocked_requests_get_with_agent(*args, **kwargs):
        return MockResponse({
            "kind": "PodList",
            "apiVersion": "v1",
            "metadata": {},
            "items": [
                # apiserver Pod
                {
                    "metadata": {
                        "name": "t1-2306965351-dg611",
                        "generateName": "t1-2306965351-",
                        "namespace": "default",
                    },
                    "spec": {
                        "nodeName": "ip-172-31-66-124.eu-east-1.compute.internal",
                    },
                    "status": {
                        "phase": "Running",
                        "hostIP": "172.31.66.124",
                        "podIP": "100.112.119.9",
                    }
                },
                # apiserver Pod -> datadog agent
                {
                    "metadata": {
                        "name": "dd-agent-r38l3",
                        "generateName": "dd-agent-",
                        "namespace": "default",
                    },
                    "spec": {
                        "serviceAccountName": "dd-agent",
                        "serviceAccount": "dd-agent",
                        "nodeName": "ip-172-31-66-124.eu-east-1.compute.internal",
                    },
                    "status": {
                        "phase": "Running",
                        "hostIP": "172.31.66.124",
                        "podIP": "100.112.119.8",
                    }
                }
            ]}, 200)

    def test_get_node_info_ok(self):
        with patch('utils.kubernetes.kubeutil.requests.get',
                   side_effect=TestKubeGetNodeInfo.mocked_requests_get_without_agent_but_ok):
            r = self.kube.get_node_info()
            self.assertEqual(("10.132.0.22", "cluster-pool-2-66d4cbf5-z9d1"), r)

    def test_get_node_info_empty(self):
        with patch('utils.kubernetes.kubeutil.requests.get',
                   side_effect=TestKubeGetNodeInfo.mocked_requests_get_empty):
            r = self.kube.get_node_info()
            self.assertEqual((None, None), r)

    def test_get_node_info_only_node_name(self):
        with patch('utils.kubernetes.kubeutil.requests.get',
                   side_effect=TestKubeGetNodeInfo.mocked_requests_get_without_agent_but_only_node_name):
            r = self.kube.get_node_info()
            self.assertEqual((None, 'cluster-pool-2-66d4cbf5-z9d1'), r)

    @patch.dict(os.environ, {'KUBERNETES_POD_NAME': 'dd-agent-r38l3'})
    def test_get_node_info_with_agent(self):
        with patch('utils.kubernetes.kubeutil.requests.get',
                   side_effect=TestKubeGetNodeInfo.mocked_requests_get_with_agent):
            self.kube.__init__()
            r = self.kube.get_node_info()
            self.assertEqual(('172.31.66.124', 'ip-172-31-66-124.eu-east-1.compute.internal'), r)

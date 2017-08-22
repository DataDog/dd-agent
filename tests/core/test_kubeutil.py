# stdlib
import unittest
import os.path

# 3rd party
from mock import patch
import json

# project
from utils.kubernetes import KubeUtil
from .test_orchestrator import MockResponse

class KubeTestCase(unittest.TestCase):
    # Patch _locate_kubelet that is used by KubeUtil.__init__
    def setUp(self):
        with patch.object(KubeUtil, '_locate_kubelet', return_value='http://localhost:10255'):
            self.kube = KubeUtil()
            self.kube.__init__()    # It's a singleton, force re-init

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

class TestKubeUtilDeploymentTag(KubeTestCase):
    def test_deployment_name_nominal(self):
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-2891696001'))
        self.assertEqual('front-end', self.kube.get_deployment_for_replicaset('front-end-2891696001'))

    def test_deployment_illegal_name(self):
        self.assertIsNone(self.kube.get_deployment_for_replicaset('frontend2891696001'))
        self.assertIsNone(self.kube.get_deployment_for_replicaset('-frontend2891696001'))
        self.assertIsNone(self.kube.get_deployment_for_replicaset('manually-created'))

class TestKubeUtilCreatorTags(KubeTestCase):
    @classmethod
    def _fake_pod(cls,creator_kind, creator_name):
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

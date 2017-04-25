# stdlib
import unittest
import os.path

# 3rd party
from mock import patch
import json

# project
from utils.kubernetes import KubeUtil

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


class TestKubeUtilDeploymentTag(KubeTestCase):
    def test_deployment_name_nominal(self):
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-2891696001'))
        self.assertEqual('front-end', self.kube.get_deployment_for_replicaset('front-end-28916aq96001'))

    def test_deployment_illegal_name(self):
        self.assertIsNone(self.kube.get_deployment_for_replicaset('frontend2891696001'))
        self.assertIsNone(self.kube.get_deployment_for_replicaset('-frontend2891696001'))

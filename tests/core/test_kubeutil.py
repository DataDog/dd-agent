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
    @patch.object(KubeUtil, '_locate_kubelet', return_value='http://localhost:10255')
    def setUp(self, unused_mock_locate):
        self.kube = KubeUtil()
        self.kube.__init__()    # It's a singleton, force re-init

    def tearDown(self):
        self.kube = None


class TestKubeUtilServiceTag(KubeTestCase):
    @classmethod
    def _load_json_array(cls, names):
        json_array = []
        for filename in names:
            path = os.path.join(os.path.dirname(__file__), 'fixtures', 'kubeutil', filename)
            with open(path) as data_file:
                json_array.append(json.load(data_file))
        return json_array

    @classmethod
    def _build_pod_metadata(cls, labels=None):
        c = {}
        if labels is not None:
            c['labels'] = labels
        return c

    def test_service_cache_init(self):
        self.assertIsNone(self.kube._services_cache)
        self.assertEqual(-1, self.kube._services_cache_last_resourceversion)

    def test_service_cache_fill(self):
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.kube._fill_services_cache()
        self.assertIsNotNone(self.kube._services_cache)
        # Kubernetes service not imported because no selector
        self.assertEqual(sorted([u'redis-hello', u'frontend-hello', u'all-hello']),
            sorted(self.kube._services_cache.keys()))

        redis = self.kube._services_cache['redis-hello']
        self.assertEqual(2, len(redis))
        self.assertEqual('hello', redis['app'])
        self.assertEqual('db', redis['tier'])

        self.assertEqual(2709, self.kube._services_cache_last_resourceversion)

    def test_service_cache_invalidation_true(self):
        jsons = self._load_json_array(['service_cache_events1.json', 'service_cache_services1.json', 'service_cache_events2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.kube._fill_services_cache()
            self.assertEqual(2707, self.kube._services_cache_last_resourceversion)
            self.kube.check_services_cache_freshness()
            self.assertIsNone(self.kube._services_cache)
            self.assertEqual(2709, self.kube._services_cache_last_resourceversion)

    def test_service_cache_invalidation_false(self):
        jsons = self._load_json_array(['service_cache_events1.json', 'service_cache_services1.json', 'service_cache_events1.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.kube._fill_services_cache()
            self.assertEqual(2707, self.kube._services_cache_last_resourceversion)
            self.kube.check_services_cache_freshness()
            self.assertIsNotNone(self.kube._services_cache)
            self.assertEqual(2707, self.kube._services_cache_last_resourceversion)

    def test_pod_to_service_no_match(self):
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.kube._fill_services_cache()
            no_match = self._build_pod_metadata({'app': 'unknown'})
            self.assertEqual(0, len(self.kube.match_services_for_pod(no_match)))

    def test_pod_to_service_two_matches(self):
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.kube._fill_services_cache()
            two_matches = self._build_pod_metadata({'app': 'hello', 'tier': 'db'})
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                sorted(self.kube.match_services_for_pod(two_matches)))


class TestKubeUtilDeploymentTag(KubeTestCase):
    def test_deployment_name_nominal(self):
        self.assertEqual('frontend', self.kube.get_deployment_for_replicaset('frontend-2891696001'))
        self.assertEqual('front-end', self.kube.get_deployment_for_replicaset('front-end-28916aq96001'))

    def test_deployment_illegal_name(self):
        self.assertIsNone(self.kube.get_deployment_for_replicaset('frontend2891696001'))
        self.assertIsNone(self.kube.get_deployment_for_replicaset('-frontend2891696001'))

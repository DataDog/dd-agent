# 3rd party
from mock import patch, Mock
import requests

# project
from utils.kubernetes import PodServiceMapper
from utils.kubernetes.pod_service_mapper import MAX_403_RETRIES
from tests.core.test_kubeutil import KubeTestCase

ALL_HELLO_UID = "94813607-1aad-11e7-8b67-42010a840226"
REDIS_HELLO_UID = "9474d98a-1aad-11e7-8b67-42010a840226"


class TestKubePodServiceMapper(KubeTestCase):
    @classmethod
    def _build_pod_metadata(cls, uid, labels=None):
        c = {'uid': uid}
        if labels is not None:
            c['labels'] = labels
        return c

    def setUp(self):
        KubeTestCase.setUp(self)

    def tearDown(self):
        KubeTestCase.tearDown(self)

    def test_init(self):
        mapper = PodServiceMapper(self.kube)
        self.assertEqual(0, len(mapper._service_cache_selectors))
        self.assertEqual(0, len(mapper._service_cache_names))
        self.assertEqual(True, mapper._service_cache_invalidated)
        self.assertEqual(0, len(mapper._pod_labels_cache))
        self.assertEqual(0, len(mapper._pod_services_mapping))

    def test_service_cache_fill(self):
        jsons = self._load_resp_array(['service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            mapper = PodServiceMapper(self.kube)
            mapper._fill_services_cache()
        # Kubernetes service not imported because no selector
        self.assertEqual(3, len(mapper._service_cache_selectors))
        self.assertEqual(3, len(mapper._service_cache_names))

        self.assertEqual('redis-hello', mapper._service_cache_names['9474d98a-1aad-11e7-8b67-42010a840226'])
        redis = mapper._service_cache_selectors['9474d98a-1aad-11e7-8b67-42010a840226']
        self.assertEqual(2, len(redis))
        self.assertEqual('hello', redis['app'])
        self.assertEqual('db', redis['tier'])

    def test_pod_to_service_no_match(self):
        jsons = self._load_resp_array(['service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            mapper = PodServiceMapper(self.kube)
            mapper._fill_services_cache()
            no_match = self._build_pod_metadata(0, {'app': 'unknown'})
            self.assertEqual(0, len(mapper.match_services_for_pod(no_match)))

    def test_pod_to_service_two_matches(self):
        jsons = self._load_resp_array(['service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            mapper = PodServiceMapper(self.kube)
            two_matches = self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'})
            self.assertEqual(sorted(['9474d98a-1aad-11e7-8b67-42010a840226',
                                     '94813607-1aad-11e7-8b67-42010a840226']),
                             sorted(mapper.match_services_for_pod(two_matches)))
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                             sorted(mapper.match_services_for_pod(two_matches, names=True)))

    def test_pod_to_service_cache(self):
        jsons = self._load_resp_array(['service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            mapper = PodServiceMapper(self.kube)
            two_matches = self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'})
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                             sorted(mapper.match_services_for_pod(two_matches, names=True)))
            # Mapper should find the uid in the cache and return without label matching
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                             sorted(mapper.match_services_for_pod({'uid': 0}, names=True)))

    def test_pods_for_service(self):
        jsons = self._load_resp_array(['service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):

            # Fill pod label cache
            mapper = PodServiceMapper(self.kube)
            mapper.match_services_for_pod(self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))
            mapper.match_services_for_pod(self._build_pod_metadata(1, {'app': 'hello', 'tier': 'db'}))
            mapper.match_services_for_pod(self._build_pod_metadata(2, {'app': 'nope', 'tier': 'db'}))
            mapper.match_services_for_pod(self._build_pod_metadata(3, {'app': 'hello', 'tier': 'nope'}))

            self.assertEqual([0, 1, 3], sorted(mapper.search_pods_for_service(ALL_HELLO_UID)))
            self.assertEqual([0, 1], sorted(mapper.search_pods_for_service(REDIS_HELLO_UID)))
            self.assertEqual([], sorted(mapper.search_pods_for_service("invalid")))

    def test_403_disable(self):
        exception403 = requests.exceptions.HTTPError()
        exception403.response = Mock()
        exception403.response.status_code = 403
        self.assertEquals(403, exception403.response.status_code)
        self.assertTrue(isinstance(exception403, requests.exceptions.HTTPError))

        with patch.object(self.kube, 'retrieve_json_auth', side_effect=exception403) as request_mock:
            # Fill pod label cache
            mapper = PodServiceMapper(self.kube)
            self.assertEqual(0, mapper._403_errors)

            for i in range(0, MAX_403_RETRIES):
                self.assertFalse(mapper._403_disable)
                mapper._fill_services_cache()

            self.assertTrue(mapper._403_disable)

            # No new requests to the apiserver
            request_mock.assert_called()
            request_mock.reset_mock()
            mapper._fill_services_cache()
            request_mock.assert_not_called()

    def _prepare_events_tests(self, jsonfiles):
        jsons = self._load_resp_array(jsonfiles)
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            mapper = PodServiceMapper(self.kube)
            # Fill pod label cache
            mapper.match_services_for_pod(self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))
            mapper.match_services_for_pod(self._build_pod_metadata(1, {'app': 'hello', 'tier': 'db'}))
            mapper.match_services_for_pod(self._build_pod_metadata(2, {'app': 'nope', 'tier': 'db'}))
            mapper.match_services_for_pod(self._build_pod_metadata(3, {'app': 'hello', 'tier': 'nope'}))

            return mapper

    def test_event_pod_invalidation(self):
        mapper = self._prepare_events_tests(['service_cache_services2.json'])
        self.assertTrue(0 in mapper._pod_labels_cache)
        self.assertTrue(0 in mapper._pod_services_mapping)
        self.assertTrue(1 in mapper._pod_labels_cache)
        self.assertTrue(1 in mapper._pod_services_mapping)

        event = {'involvedObject': {'kind': 'Pod', 'uid': 0}, 'reason': 'Killing'}
        self.assertEqual(0, len(mapper.process_events([event])))

        self.assertFalse(0 in mapper._pod_labels_cache)
        self.assertFalse(0 in mapper._pod_services_mapping)
        self.assertTrue(1 in mapper._pod_labels_cache)
        self.assertTrue(1 in mapper._pod_services_mapping)

    def test_event_service_deleted_invalidation(self):
        mapper = self._prepare_events_tests(['service_cache_services2.json'])
        self.assertEqual(2, len(mapper.match_services_for_pod({'uid': 0})))

        event = {'involvedObject': {'kind': 'Service', 'uid': REDIS_HELLO_UID},
                 'reason': 'DeletedLoadBalancer'}
        # Two pods must be reloaded
        self.assertEqual(set([0, 1]), mapper.process_events([event]))
        # redis-hello service removed from pod mapping
        self.assertEqual(1, len(mapper.match_services_for_pod({'uid': 0})))

    def test_event_service_created_invalidation(self):
        mapper = self._prepare_events_tests(['service_cache_services1.json'])
        self.assertEqual(1, len(mapper.match_services_for_pod(
            self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))))

        event = {'involvedObject': {'kind': 'Service', 'uid': ALL_HELLO_UID},
                 'reason': 'CreatedLoadBalancer'}
        jsons = self._load_resp_array(['service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            # Three pods must be reloaded
            self.assertEqual(set([0, 1, 3]), mapper.process_events([event]))
            # all-hello service added to pod mapping
            self.assertEqual(2, len(mapper.match_services_for_pod(
                self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))))

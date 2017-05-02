# 3rd party
from mock import patch

# project
from utils.kubernetes import PodServiceMapper
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
        self.mapper = PodServiceMapper(self.kube)

    def tearDown(self):
        self.mapper = None
        KubeTestCase.tearDown(self)

    def test_init(self):
        self.assertEqual(0, len(self.mapper._service_cache_selectors))
        self.assertEqual(0, len(self.mapper._service_cache_names))
        self.assertEqual(True, self.mapper._service_cache_invalidated)
        self.assertEqual(-1, self.mapper._service_cache_last_event_resversion)
        self.assertEqual(0, len(self.mapper._pod_labels_cache))
        self.assertEqual(0, len(self.mapper._pod_services_mapping))

    def test_service_cache_fill(self):
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.mapper._fill_services_cache()
        # Kubernetes service not imported because no selector
        self.assertEqual(3, len(self.mapper._service_cache_selectors))
        self.assertEqual(3, len(self.mapper._service_cache_names))
        self.assertEqual(False, self.mapper._service_cache_invalidated)
        self.assertEqual(2709, self.mapper._service_cache_last_event_resversion)

        self.assertEqual(
            'redis-hello', self.mapper._service_cache_names['9474d98a-1aad-11e7-8b67-42010a840226'])
        redis = self.mapper._service_cache_selectors['9474d98a-1aad-11e7-8b67-42010a840226']
        self.assertEqual(2, len(redis))
        self.assertEqual('hello', redis['app'])
        self.assertEqual('db', redis['tier'])

    def test_service_cache_invalidation_true(self):
        jsons = self._load_json_array(
            ['service_cache_events1.json', 'service_cache_services1.json', 'service_cache_events2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.mapper._fill_services_cache()
            self.assertEqual(2707, self.mapper._service_cache_last_event_resversion)
            self.mapper.check_services_cache_freshness()
            self.assertEqual(True, self.mapper._service_cache_invalidated)
            self.assertEqual(2709, self.mapper._service_cache_last_event_resversion)

    def test_service_cache_invalidation_false(self):
        jsons = self._load_json_array(
            ['service_cache_events1.json', 'service_cache_services1.json', 'service_cache_events1.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.mapper._fill_services_cache()
            self.assertEqual(2707, self.mapper._service_cache_last_event_resversion)
            self.mapper.check_services_cache_freshness()
            self.assertEqual(False, self.mapper._service_cache_invalidated)
            self.assertEqual(2707, self.mapper._service_cache_last_event_resversion)

    def test_pod_to_service_no_match(self):
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            self.mapper._fill_services_cache()
            no_match = self._build_pod_metadata(0, {'app': 'unknown'})
            self.assertEqual(0, len(self.mapper.match_services_for_pod(no_match)))

    def test_pod_to_service_two_matches(self):
        self.assertEqual(0, len(self.mapper._pod_services_mapping))
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            two_matches = self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'})
            self.assertEqual(sorted(['9474d98a-1aad-11e7-8b67-42010a840226',
                                     '94813607-1aad-11e7-8b67-42010a840226']),
                             sorted(self.mapper.match_services_for_pod(two_matches)))
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                             sorted(self.mapper.match_services_for_pod(two_matches, names=True)))

    def test_pod_to_service_cache(self):
        self.assertEqual(0, len(self.mapper._pod_services_mapping))
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            two_matches = self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'})
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                             sorted(self.mapper.match_services_for_pod(two_matches, names=True)))
            # Mapper should find the uid in the cache and return without label matching
            self.assertEqual(sorted(['redis-hello', 'all-hello']),
                             sorted(self.mapper.match_services_for_pod({'uid': 0}, names=True)))

    def test_pods_for_service(self):
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            # Fill pod label cache
            self.mapper.match_services_for_pod(self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))
            self.mapper.match_services_for_pod(self._build_pod_metadata(1, {'app': 'hello', 'tier': 'db'}))
            self.mapper.match_services_for_pod(self._build_pod_metadata(2, {'app': 'nope', 'tier': 'db'}))
            self.mapper.match_services_for_pod(self._build_pod_metadata(3, {'app': 'hello', 'tier': 'nope'}))

            self.assertEqual([0, 1, 3], sorted(self.mapper.search_pods_for_service(ALL_HELLO_UID)))
            self.assertEqual([0, 1], sorted(self.mapper.search_pods_for_service(REDIS_HELLO_UID)))
            self.assertEqual([], sorted(self.mapper.search_pods_for_service("invalid")))

    def _prepare_for_events_tests(self, jsonfiles):
        jsons = self._load_json_array(jsonfiles)
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            # Fill pod label cache
            self.mapper.match_services_for_pod(self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))
            self.mapper.match_services_for_pod(self._build_pod_metadata(1, {'app': 'hello', 'tier': 'db'}))
            self.mapper.match_services_for_pod(self._build_pod_metadata(2, {'app': 'nope', 'tier': 'db'}))
            self.mapper.match_services_for_pod(self._build_pod_metadata(3, {'app': 'hello', 'tier': 'nope'}))

    def test_event_pod_invalidation(self):
        self._prepare_for_events_tests(['service_cache_events2.json', 'service_cache_services2.json'])
        self.assertTrue(0 in self.mapper._pod_labels_cache)
        self.assertTrue(0 in self.mapper._pod_services_mapping)
        self.assertTrue(1 in self.mapper._pod_labels_cache)
        self.assertTrue(1 in self.mapper._pod_services_mapping)

        event = {'involvedObject': {'kind': 'Pod', 'uid': 0}, 'reason': 'Killing'}
        self.assertEqual(0, len(self.mapper.process_events([event])))

        self.assertFalse(0 in self.mapper._pod_labels_cache)
        self.assertFalse(0 in self.mapper._pod_services_mapping)
        self.assertTrue(1 in self.mapper._pod_labels_cache)
        self.assertTrue(1 in self.mapper._pod_services_mapping)

    def test_event_service_deleted_invalidation(self):
        self._prepare_for_events_tests(['service_cache_events2.json', 'service_cache_services2.json'])
        self.assertEqual(2, len(self.mapper.match_services_for_pod({'uid': 0})))

        event = {'involvedObject': {'kind': 'Service', 'uid': REDIS_HELLO_UID},
                 'reason': 'DeletedLoadBalancer'}
        # Two pods must be reloaded
        self.assertEqual(set([0, 1]), self.mapper.process_events([event]))
        # redis-hello service removed from pod mapping
        self.assertEqual(1, len(self.mapper.match_services_for_pod({'uid': 0})))

    def test_event_service_created_invalidation(self):
        self._prepare_for_events_tests(['service_cache_events1.json', 'service_cache_services1.json'])
        self.assertEqual(1, len(self.mapper.match_services_for_pod(
            self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))))

        event = {'involvedObject': {'kind': 'Service', 'uid': ALL_HELLO_UID},
                 'reason': 'CreatedLoadBalancer'}
        jsons = self._load_json_array(['service_cache_events2.json', 'service_cache_services2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            # Three pods must be reloaded
            self.assertEqual(set([0, 1, 3]), self.mapper.process_events([event]))
            # all-hello service added to pod mapping
            self.assertEqual(2, len(self.mapper.match_services_for_pod(
                self._build_pod_metadata(0, {'app': 'hello', 'tier': 'db'}))))

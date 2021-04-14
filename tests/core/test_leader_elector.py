# stdlib
import datetime
import time

# 3rd party
import mock

# project
from tests.core.test_kubeutil import KubeTestCase
from utils.kubernetes.leader_elector import LeaderElector, \
    ACQUIRE_TIME_ANNOTATION, CREATOR_ANNOTATION, CM_NAME


class TestLeaderElector(KubeTestCase):
    def test_is_cm_mine(self):
        elector = LeaderElector(self.kube)
        self.kube._node_name = 'foo'

        error_cm = [
            ({}, KeyError),
            ({'metadata': {}}, KeyError),
        ]
        for cm, ex in error_cm:
            self.assertRaises(ex, elector._is_cm_mine, cm)

        cm = {'metadata': {'annotations': {CREATOR_ANNOTATION: 'foo'}}}
        self.assertEqual(elector._is_cm_mine(cm), True)
        cm = {'metadata': {'annotations': {}}}
        self.assertEqual(elector._is_cm_mine(cm), False)
        cm = {'metadata': {'annotations': {CREATOR_ANNOTATION: 'bar'}}}
        self.assertEqual(elector._is_cm_mine(cm), False)

    def test_build_update_cm_payload(self):
        now = datetime.datetime.utcnow()
        self.kube._node_name = 'foo'
        elector = LeaderElector(self.kube)

        cm = {
            'kind': 'ConfigMap',
            'apiVersion': 'v1',
            'data': {},
            'metadata': {
                'name': 'datadog-leader-elector',
                'namespace': 'default',
                'resourceVersion': '5563782',
                'creationTimestamp': '2017-08-21T17:37:32Z',
                'annotations': {'acquired_time': datetime.datetime.strftime(now, "%Y-%m-%dT%H:%M:%S.%f"),
                                'creator': 'dd-agent-284pl'
                                },
                'selfLink': '/api/v1/namespaces/default/configmaps/datadog-leader-elector',
                'uid': '697b957c-8697-11e7-b62f-42010af002d4'
            },
        }
        time.sleep(1)
        pl = elector._build_update_cm_payload(cm)
        self.assertEqual(pl['data'], cm['data'])
        self.assertEqual(pl['metadata']['name'], cm['metadata']['name'])
        self.assertEqual(pl['metadata']['namespace'], cm['metadata']['namespace'])
        self.assertEqual(pl['metadata']['annotations'][CREATOR_ANNOTATION], cm['metadata']['annotations'][CREATOR_ANNOTATION])
        self.assertTrue(pl['metadata']['annotations'][ACQUIRE_TIME_ANNOTATION] > cm['metadata']['annotations'][ACQUIRE_TIME_ANNOTATION])

    def test_build_create_cm_payload(self):
        now = datetime.datetime.utcnow()
        self.kube._node_name = 'foo'
        elector = LeaderElector(self.kube)

        cm = {
            'data': {},
            'metadata': {
                'name': CM_NAME,
                'namespace': 'default',
                'annotations': {
                    CREATOR_ANNOTATION: 'foo',
                    ACQUIRE_TIME_ANNOTATION: datetime.datetime.strftime(now, "%Y-%m-%dT%H:%M:%S.%f")
                }
            }
        }
        pl = elector._build_create_cm_payload()
        self.assertEqual(pl['data'], cm['data'])
        self.assertEqual(pl['metadata']['name'], cm['metadata']['name'])
        self.assertEqual(pl['metadata']['namespace'], cm['metadata']['namespace'])
        self.assertEqual(pl['metadata']['annotations'][CREATOR_ANNOTATION], cm['metadata']['annotations'][CREATOR_ANNOTATION])
        self.assertTrue(pl['metadata']['annotations'][ACQUIRE_TIME_ANNOTATION] >= cm['metadata']['annotations'][ACQUIRE_TIME_ANNOTATION])

    def test_is_lock_expired(self):
        elector = LeaderElector(self.kube)

        cm = {
            'kind': 'ConfigMap',
            'apiVersion': 'v1',
            'data': {},
            'metadata': {
                'name': 'datadog-leader-elector',
                'namespace': 'default',
                'resourceVersion': '5563782',
                'creationTimestamp': '2017-08-21T17:37:32Z',
                'annotations': {'acquired_time': '2017-08-21T17:37:32.514660',
                                'creator': 'dd-agent-284pl'
                                },
                'selfLink': '/api/v1/namespaces/default/configmaps/datadog-leader-elector',
                'uid': '697b957c-8697-11e7-b62f-42010af002d4'
            }
        }

        self.assertTrue(elector._is_lock_expired(cm))
        cm['metadata']['annotations'][ACQUIRE_TIME_ANNOTATION] = '3017-08-21T17:37:32.514660'
        self.assertFalse(elector._is_lock_expired(cm))

    @mock.patch.object(LeaderElector, '_get_cm', return_value=None)
    @mock.patch.object(LeaderElector, '_try_lock_cm', return_value=False)
    @mock.patch.object(LeaderElector, '_is_cm_mine', return_value=False)
    @mock.patch.object(LeaderElector, '_is_lock_expired', return_value=True)
    @mock.patch.object(LeaderElector, '_try_refresh_cm', return_value=True)
    def test_try_refresh(self, m_refresh_cm, m_lock_expired, m_cm_mine, m_lock_cm, m_get_cm):
        elector = LeaderElector(self.kube)

        # First test uses the decorator return values
        self.assertFalse(elector._try_refresh())

        m_get_cm.return_value = {'some': 'thing'}

        m_lock_expired.return_value = True
        self.assertFalse(elector._try_refresh())

        m_lock_cm.return_value = True
        self.assertTrue(elector._try_refresh())

        m_cm_mine.return_value = True
        self.assertTrue(elector._try_refresh())

        m_get_cm.return_value = None
        m_lock_cm.return_value = False
        m_refresh_cm.return_value = False
        self.assertFalse(elector._try_refresh())

    @mock.patch.object(LeaderElector, '_get_cm', return_value=None)
    @mock.patch.object(LeaderElector, '_try_lock_cm', return_value=False)
    @mock.patch.object(LeaderElector, '_is_cm_mine', return_value=False)
    @mock.patch.object(LeaderElector, '_is_lock_expired', return_value=True)
    def test_try_acquire(self, m_lock_expired, m_cm_mine, m_lock_cm, m_get_cm):
        elector = LeaderElector(self.kube)

        # First test uses the decorator return values
        self.assertFalse(elector._try_acquire())

        m_get_cm.return_value = {'some': 'thing'}
        m_lock_cm.return_value = True
        self.assertTrue(elector._try_acquire())

        m_lock_cm.return_value = False
        self.assertFalse(elector._try_acquire())

        m_get_cm.return_value = None
        m_lock_expired.return_value = True
        self.assertFalse(elector._try_refresh())

        m_lock_cm.return_value = True
        self.assertTrue(elector._try_refresh())

        m_lock_cm.return_value = True
        self.assertTrue(elector._try_refresh())

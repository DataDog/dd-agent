# stdlib
import time  # noqa: F401

# 3rd party
from mock import patch

# project
from utils.kubernetes import KubeEventRetriever
from tests.core.test_kubeutil import KubeTestCase
from .test_orchestrator import MockResponse


class TestKubeEventRetriever(KubeTestCase):
    @classmethod
    def _build_events(cls, specs):
        """
        Returns an eventlist from specs in the form [(namespace, kind)]
        """
        lastTimestamp = 0
        items = []
        for ns, kind in specs:
            i = {}
            i['lastTimestamp'] = "2017-04-06T09:44:17Z"
            i['metadata'] = {'resourceVersion': lastTimestamp, 'namespace': ns}
            i['involvedObject'] = {'kind': kind, 'namespace': ns}
            items.append(i)
        return {'items': items}

    def test_events_lasttimestamp_filtering(self):
        jsons = self._load_resp_array(
            ['service_cache_events1.json', 'service_cache_events2.json', 'service_cache_events2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            retr = KubeEventRetriever(self.kube)

            events = retr.get_event_array()
            self.assertEquals(3, len(events))
            self.assertEquals(1491471904, retr.lastTimestamp)
            events = retr.get_event_array()
            self.assertEquals(2, len(events))   # 5 events total
            self.assertEquals(1491471953, retr.lastTimestamp)
            events = retr.get_event_array()
            self.assertEquals(0, len(events))   # No new event
            self.assertEquals(1491471953, retr.lastTimestamp)

    @patch('time.time')
    def test_events_delay(self, mock_time):
        jsons = self._load_resp_array(
            ['service_cache_events1.json', 'service_cache_events2.json'])
        with patch.object(self.kube, 'retrieve_json_auth', side_effect=jsons):
            retr = KubeEventRetriever(self.kube, delay=500)

            mock_time.return_value = 10000
            events = retr.get_event_array()
            self.assertEquals(3, len(events))
            self.assertEquals(1491471904, retr.lastTimestamp)

            # Must skip request
            mock_time.return_value = 10400
            events = retr.get_event_array()
            self.assertEquals(0, len(events))
            self.assertEquals(1491471904, retr.lastTimestamp)

            # Must retrieve events
            mock_time.return_value = 10600
            events = retr.get_event_array()
            self.assertEquals(2, len(events))
            self.assertEquals(1491471953, retr.lastTimestamp)

    def test_namespace_serverside_filtering(self):
        with patch.object(self.kube, 'retrieve_json_auth', return_value=MockResponse({}, 200)) as mock_method:
            retr = KubeEventRetriever(self.kube, namespaces=['testns'])
            retr.get_event_array()
        mock_method.assert_called_once_with('https://kubernetes:443/api/v1/namespaces/testns/events', params={})

    def test_namespace_clientside_filtering(self):
        val = self._build_events([('ns1', 'k1'), ('ns2', 'k1'), ('testns', 'k1')])
        with patch.object(self.kube, 'retrieve_json_auth', return_value=MockResponse(val, 200)) as mock_method:
            retr = KubeEventRetriever(self.kube, namespaces=['testns', 'ns2'])
            events = retr.get_event_array()
            self.assertEquals(2, len(events))
        mock_method.assert_called_once_with('https://kubernetes:443/api/v1/events', params={})

    def test_kind_serverside_filtering(self):
        with patch.object(self.kube, 'retrieve_json_auth', return_value=MockResponse({}, 200)) as mock_method:
            retr = KubeEventRetriever(self.kube, kinds=['k1'])
            retr.get_event_array()
        mock_method.assert_called_once_with('https://kubernetes:443/api/v1/events',
                                            params={'fieldSelector': 'involvedObject.kind=k1'})

    def test_kind_clientside_filtering(self):
        val = self._build_events([('ns1', 'k1'), ('ns1', 'k1'), ('ns1', 'k2'), ('ns1', 'k3')])
        with patch.object(self.kube, 'retrieve_json_auth', return_value=MockResponse(val, 200)) as mock_method:
            retr = KubeEventRetriever(self.kube, kinds=['k1', 'k2'])
            events = retr.get_event_array()
            self.assertEquals(3, len(events))
        mock_method.assert_called_once_with('https://kubernetes:443/api/v1/events', params={})

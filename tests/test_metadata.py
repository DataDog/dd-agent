import unittest

# project
from checks import AgentCheck
from checks.collector import AgentPayload

# 3p
from mock import Mock


class TestAgentPayload(unittest.TestCase):
    def test_add_rem_elem(self):
        payload = AgentPayload()

        # Is initially empty
        self.assertEquals(len(payload), 0)

        # Set a new value
        payload['something'] = "value"
        self.assertEquals(len(payload), 1)

        # can access it
        self.assertEquals(payload['something'], "value")

        # can update it
        payload['something'] = "other value"
        self.assertEquals(len(payload), 1)
        self.assertEquals(payload['something'], "other value")

        # delete it
        del payload['something']
        self.assertEquals(len(payload), 0)

    def test_split_metrics_and_meta(self):
        # Some not metadata keys
        DATA_KEYS = ['Key1', 'Key2', 'Key3', 'Key4']

        payload = AgentPayload()

        # Adding metadata values
        for key in AgentPayload.METADATA_KEYS:
            payload[key] = "value"
        len_payload1 = len(payload)
        self.assertEquals(len_payload1, len(AgentPayload.METADATA_KEYS))
        self.assertEquals(len_payload1, len(payload.payload_meta))
        self.assertEquals(len(payload.payload_data), 0)

        # Adding non metadata values
        for key in DATA_KEYS:
            payload[key] = "value"
        len_payload2 = len(payload)
        self.assertEquals(len_payload2, len_payload1 + len(DATA_KEYS))
        self.assertEquals(len_payload2 - len_payload1, len(payload.payload_data))
        self.assertEquals(len(payload.payload_meta), len_payload1)
        fake_emitter = Mock()
        fake_emitter.__name__ = None
        payload.emit(None, None, [fake_emitter], True)
        fake_emitter.assert_any_call(payload.payload_data, None, None, "metrics")
        fake_emitter.assert_any_call(payload.payload_meta, None, None, "metadata")


class TestIntegrationMetadata(unittest.TestCase):
    """Focus on testing metadata"""
    class FakeCheck(AgentCheck):
        """ This check will generate metadata depending on the instance """
        def check(self, instance):
            metadata = instance.get('metadata')
            if metadata:
                self._collect_metadata()

        def _collect_metadata(self):
            self.svc_metadata({'version': 1})

    def test_metadata_length(self):
        # Fake config. Instance 2 will notto generate any meta
        config = {'instances': [{'metadata': True}, {}]}

        instances = config.get('instances')
        check = TestIntegrationMetadata.FakeCheck("fake_check", config, {}, instances)
        check.run()
        service_metadata = check.get_service_metadata()
        service_metadata_count = len(service_metadata)

        self.assertEquals(service_metadata_count, 2)
        self.assertEquals(service_metadata[0], {'version': 1})
        self.assertEquals(service_metadata[1], {})

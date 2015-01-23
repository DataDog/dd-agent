# Core modules
import unittest

# Datadog Agent
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

    def test_split_metrics_and_metrics(self):
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

# stdlib
import unittest

#  3p
from mock import Mock

# project
from checks.collector import AgentPayload


class TestAgentPayload(unittest.TestCase):
    """
    Test the agent payload logic
    """
    def test_add_rem_elem(self):
        """
        Can set, read, update and delete data in the agent_payload
        """
        agent_payload = AgentPayload()

        # Is initially empty
        self.assertEquals(len(agent_payload), 0)

        # Set a new value
        agent_payload['something'] = "value"
        self.assertEquals(len(agent_payload), 1)

        # Can access it
        self.assertEquals(agent_payload['something'], "value")

        # Can update it
        agent_payload['something'] = "other value"
        self.assertEquals(len(agent_payload), 1)
        self.assertEquals(agent_payload['something'], "other value")

        # Delete it
        del agent_payload['something']
        self.assertEquals(len(agent_payload), 0)

    def test_payload_property(self):
        """
        `agent_payload` property returns a single agent_payload
        with the content of data and metadata payloads.
        """
        agent_payload = AgentPayload()
        payload = {}

        DATA_KEYS = ['key1', 'key2']
        META_KEYS = list(AgentPayload.METADATA_KEYS)[:2]
        DUP_KEYS = list(AgentPayload.DUPLICATE_KEYS)[:2]

        # Addind data, meta and duplicate values to agent_payload and payload
        for k in DATA_KEYS + META_KEYS + DUP_KEYS:
            agent_payload[k] = "value"
            payload[k] = "value"

        self.assertEquals(agent_payload.payload, payload, agent_payload)

    def test_split_metrics_and_meta(self):
        """
        Split data and metadata payloads. Submit to the right endpoint.
        """
        # Some not metadata keys
        DATA_KEYS = ['key1', 'key2', 'key3', 'key4']

        agent_payload = AgentPayload()

        # Adding metadata values
        for key in AgentPayload.METADATA_KEYS:
            agent_payload[key] = "value"
        len_payload1 = len(agent_payload)
        self.assertEquals(len_payload1, len(AgentPayload.METADATA_KEYS))
        self.assertEquals(len_payload1, len(agent_payload.meta_payload))
        self.assertEquals(len(agent_payload.data_payload), 0)

        # Adding data values
        for key in DATA_KEYS:
            agent_payload[key] = "value"
        len_payload2 = len(agent_payload)
        self.assertEquals(len_payload2, len_payload1 + len(DATA_KEYS))
        self.assertEquals(len_payload2 - len_payload1, len(agent_payload.data_payload))
        self.assertEquals(len(agent_payload.meta_payload), len_payload1)

        # Adding common values
        for key in AgentPayload.DUPLICATE_KEYS:
            agent_payload[key] = "value"
        len_payload3 = len(agent_payload)
        self.assertEquals(len_payload3, len_payload2 + 2 * len(AgentPayload.DUPLICATE_KEYS))
        self.assertEquals(len_payload1 + len(AgentPayload.DUPLICATE_KEYS),
                          len(agent_payload.meta_payload))
        self.assertEquals(len_payload2 - len_payload1 + len(AgentPayload.DUPLICATE_KEYS),
                          len(agent_payload.data_payload))

    def test_emit_payload(self):
        """
        Submit each payload to its specific endpoint.
        """
        agent_payload = AgentPayload()

        fake_emitter = Mock()
        fake_emitter.__name__ = None

        # Different payloads, different endpoints
        agent_payload.emit(None, None, [fake_emitter], True, merge_payloads=False)
        fake_emitter.assert_any_call(agent_payload.data_payload, None, None, "metrics")
        fake_emitter.assert_any_call(agent_payload.meta_payload, None, None, "metadata")

        # One payload, one endpoint
        agent_payload.emit(None, None, [fake_emitter], True)
        fake_emitter.assert_any_call(agent_payload.payload, None, None, "")

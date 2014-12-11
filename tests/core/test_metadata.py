import unittest

# project
from checks import AgentCheck
from checks.collector import Collector


class TestMetadata(unittest.TestCase):
    """
    Test the metadata collection logic.
    """
    class FakeCheck(AgentCheck):
        """ This check will generate metadata depending on the instance """
        def check(self, instance):
            metadata = instance.get('metadata')
            if metadata:
                self._collect_metadata()

        def _collect_metadata(self):
            self.svc_metadata({'version': 1})

    def test_hostname_metadata(self):
        """
        Collect hostname metadata.
        """
        c = Collector({"collect_instance_metadata": True}, None, {}, "foo")
        metadata = c._get_hostname_metadata()
        assert "hostname" in metadata
        assert "socket-fqdn" in metadata
        assert "socket-hostname" in metadata

    def test_metadata_length(self):
        """
        Fill up checks that do not generate any metadata
        """
        # Instance 2 will not generate any metadata
        config = {'instances': [{'metadata': True}, {}, {'metadata': True}]}

        instances = config.get('instances')
        check = TestMetadata.FakeCheck("fake_check", config, {}, instances)
        check.run()
        service_metadata = check.get_service_metadata()
        service_metadata_count = len(service_metadata)

        self.assertEquals(service_metadata_count, 3)
        self.assertEquals(service_metadata[0], {'version': 1})
        self.assertEquals(service_metadata[1], {})
        self.assertEquals(service_metadata[2], {'version': 1})

# -*- coding: utf-8 -*-
import mock
import unittest

# project
from checks import AgentCheck
from checks.collector import Collector


class TestMetadata(unittest.TestCase):
    """
    Test the metadata collection logic.
    """
    class FakeCheck(AgentCheck):
        """
        This check will generate more or less metadata depending on the instance
        """
        def check(self, instance):
            if instance.get('metadata'):
                self._collect_metadata(instance.get('more_meta'))

        def _collect_metadata(self, more_meta):
            self.service_metadata('foo', "bar")
            if more_meta:
                self.service_metadata('baz', "qux")

    def test_hostname_metadata(self):
        """
        Collect hostname metadata
        """
        c = Collector({"collect_instance_metadata": True}, None, {}, "foo")
        metadata = c._get_hostname_metadata()
        assert "hostname" in metadata
        assert "socket-fqdn" in metadata
        assert "socket-hostname" in metadata

    def test_instance_metadata_rollup(self):
        """
        Roll-up instance metadata
        """
        config = {'instances': [{'metadata': True, 'more_meta': True}]}
        instances = config.get('instances')
        check = TestMetadata.FakeCheck("fake_check", config, {}, instances)
        check.run()

        service_metadata = check.get_service_metadata()
        service_metadata_count = len(service_metadata)

        self.assertEquals(service_metadata_count, 1)
        self.assertEquals(service_metadata[0], {'foo': "bar", 'baz': "qux"})

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
        self.assertEquals(service_metadata[0], {'foo': "bar"})
        self.assertEquals(service_metadata[1], {})
        self.assertEquals(service_metadata[2], {'foo': "bar"})

    @mock.patch('utils.platform.Platform.is_windows', return_value=True)
    def test_decode_tzname(self, mock_platform):
        # Examples of expected inputs/outputs

        # Korean systems
        with mock.patch('locale.getpreferredencoding', return_value='cp949'):
            self.assertEquals(
                Collector._decode_tzname(('\xb4\xeb\xc7\xd1\xb9\xce\xb1\xb9 \xc7\xa5\xc1\xd8\xbd\xc3', '\xb4\xeb\xc7\xd1\xb9\xce\xb1\xb9 \xc0\xcf\xb1\xa4 \xc0\xfd\xbe\xe0 \xbd\xc3\xb0\xa3')),
                (u'대한민국 표준시', u'대한민국 일광 절약 시간')
            )
        # Japanese systems
        with mock.patch('locale.getpreferredencoding', return_value='cp932'):
            self.assertEquals(
                Collector._decode_tzname(('\x93\x8c\x8b\x9e (\x95W\x8f\x80\x8e\x9e)', '\x93\x8c\x8b\x9e (\x89\xc4\x8e\x9e\x8a\xd4)')),
                (u'東京 (標準時)', u'東京 (夏時間)')
            )
        # if the preferred encoding were to be invalid, return empty timezone
        with mock.patch('locale.getpreferredencoding', return_value='invalidencoding'):
            self.assertEquals(
                Collector._decode_tzname(('\x93\x8c\x8b\x9e (\x95W\x8f\x80\x8e\x9e)', '\x93\x8c\x8b\x9e (\x89\xc4\x8e\x9e\x8a\xd4)')),
                ('', '')
            )

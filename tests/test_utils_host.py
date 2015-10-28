from unittest import TestCase
from utils.host import HostTagger
from mock import Mock


class MockLogger(object):
    def __init__(self):
        self.warnings = []

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))


class HostTaggerTest(TestCase):
    def setUp(self):
        self.host_tagger = HostTagger("some_api_key", MockLogger())


    def _clear_known_hosts(self):
        self.host_tagger._known_hosts = {}

    def test_are_tags_equivalent(self):
        self.host_tagger._known_hosts = {
            "hostA": ["tag:val", "other_tag:val"]
        }

        self.assertFalse(self.host_tagger._are_tags_equivalent("hostA", ["tag:other_val"]))
        self.assertTrue(self.host_tagger._are_tags_equivalent("hostA", ["other_tag:val", "tag:val"]))

    def test_queue_tag_update(self):
        self.host_tagger._queue_tag_update("hostA", ["tag:val", "other_tag:val"])
        self.assertEqual(len(self.host_tagger._request_queue), 1)
        self.assertTrue(isinstance(self.host_tagger._request_queue[0], HostTagger.TagRequest))

        req = self.host_tagger._request_queue[0]
        self.assertEqual(req.hostname, "hostA")
        self.assertEqual(req.tags, ["tag:val", "other_tag:val"])

    def test_create_host_tags(self):
        # Test blocking
        self.host_tagger.dd_api.Tag.create = Mock()

        self.host_tagger.create_host_tags("hostA", ["other_tag:val", "tag:val"], blocking=True)
        args, kwargs = self.host_tagger.dd_api.Tag.create.call_args

        self.assertEqual(args[0], "hostA")
        self.assertEqual(set(kwargs['tags']), set(["other_tag:val", "tag:val"]))

        # Test non-blocking (default)
        self._clear_known_hosts()
        self.host_tagger._queue_tag_update = Mock()

        self.host_tagger.create_host_tags("hostA", ["other_tag:val", "tag:val"], blocking=False)
        call_args, _ = self.host_tagger._queue_tag_update.call_args

        self.assertEqual(call_args[0], "hostA")
        self.assertEqual(set(call_args[1]), set(["other_tag:val", "tag:val"]))
        self.assertEqual(set(self.host_tagger._known_hosts["hostA"]), set(["other_tag:val", "tag:val"]))

    def test_flush(self):
        def _host_format(num):
            return "host_{0}".format(num)

        # Store the flush method before we temporarily mock it out
        _flush = self.host_tagger.flush
        self.host_tagger.flush = Mock()

        # Queue one less host tag update than the buffer size
        for i in range(self.host_tagger.MAX_QUEUE_LEN - 1):
            self.host_tagger.create_host_tags(
               _host_format(i), ["some_tag:some_val"], blocking=False
            )

        # We shouldn't have flushed anything yet
        self.assertFalse(self.host_tagger.flush.called)

        # The next update should trigger a flush
        self.host_tagger.create_host_tags(
           _host_format(i+1), ["some_tag:some_val"], blocking=False
        )

        self.assertTrue(self.host_tagger.flush.called)

        # Set flush back to normal
        self.host_tagger.flush = _flush
        self._clear_known_hosts()
        self.host_tagger._request_queue = []

        self.host_tagger.dd_api.Tag.create = Mock()

        # Queue enough updates to trigger a flush
        for i in range(self.host_tagger.MAX_QUEUE_LEN):
            self.host_tagger.create_host_tags(
               _host_format(i), ["some_tag:some_val"], blocking=False
            )

        self.assertEqual(self.host_tagger.dd_api.Tag.create.call_count, self.host_tagger.MAX_QUEUE_LEN)
        self.assertEqual(len(self.host_tagger._request_queue), 0)

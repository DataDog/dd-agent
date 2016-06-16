# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# stdlib
import mock
import unittest

from utils.dockerutil import DockerUtil


class TestDockerutil(unittest.TestCase):
    def setUp(self):
        self.dockerutil = DockerUtil()

    @mock.patch('utils.dockerutil.DockerUtil.client')
    def test_get_events(self, mocked_client):
        mocked_client.events.return_value = [
            {'status': 'stop', 'id': '1234567890', 'from': '1234567890', 'time': 1423247867}
        ]
        events_generator, _ = self.dockerutil.get_events()
        self.assertEqual(len(events_generator), 1)

        # bug in dockerpy, we should be resilient
        mocked_client.events.return_value = [u'an error from Docker API here']
        events_generator, _ = self.dockerutil.get_events()
        self.assertEqual(len(list(events_generator)), 0)

import sys

import mock
import requests

from checks import AgentCheck
from tests.checks.common import AgentCheckTest, get_checksd_path, get_os


class TestRabbitMQ(AgentCheckTest):

    CHECK_NAME = 'rabbitmq'

    @classmethod
    def setUpClass(cls):
        sys.path.append(get_checksd_path(get_os()))

    @classmethod
    def tearDownClass(cls):
        sys.path.pop()

    def test__get_data(self):
        with mock.patch('rabbitmq.requests') as r:
            from rabbitmq import RabbitMQ, RabbitMQException  # pylint: disable=import-error
            check = RabbitMQ('rabbitmq', {}, {"instances": [{"rabbitmq_api_url": "http://example.com"}]})
            r.get.side_effect = [requests.exceptions.HTTPError, ValueError]
            self.assertRaises(RabbitMQException, check._get_data, '')
            self.assertRaises(RabbitMQException, check._get_data, '')

    def test_status_check(self):
        self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
        self.assertEqual(len(self.service_checks), 1)
        sc = self.service_checks[0]
        self.assertEqual(sc['check'], 'rabbitmq.status')
        self.assertEqual(sc['status'], AgentCheck.CRITICAL)

        self.check._get_data = mock.MagicMock()
        self.run_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
        self.assertEqual(len(self.service_checks), 1)
        sc = self.service_checks[0]
        self.assertEqual(sc['check'], 'rabbitmq.status')
        self.assertEqual(sc['status'], AgentCheck.OK)

    def test__check_aliveness(self):
        self.load_check({"instances": [{"rabbitmq_api_url": "http://example.com"}]})
        self.check._get_data = mock.MagicMock()

        # only one vhost should be OK
        self.check._get_data.side_effect = [{"status": "ok"}, {}]
        self.check._check_aliveness('', vhosts=['foo', 'bar'])
        sc = self.check.get_service_checks()

        self.assertEqual(len(sc), 2)
        self.assertEqual(sc[0]['check'], 'rabbitmq.aliveness')
        self.assertEqual(sc[0]['status'], AgentCheck.OK)
        self.assertEqual(sc[1]['check'], 'rabbitmq.aliveness')
        self.assertEqual(sc[1]['status'], AgentCheck.CRITICAL)

        # in case of connection errors, this check should stay silent
        from rabbitmq import RabbitMQException  # pylint: disable=import-error
        self.check._get_data.side_effect = RabbitMQException
        self.assertRaises(RabbitMQException, self.check._check_aliveness, '')

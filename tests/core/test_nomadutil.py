# stdlib
import unittest

# 3rd party
import mock

# project
from utils.orchestrator import NomadUtil

ENV = ['NOMAD_TASK_NAME=test-task',
       'NOMAD_JOB_NAME=test-job',
       'NOMAD_ALLOC_NAME=test-task.test-group[0]']
EXPECTED_TAGS = ['nomad_task:test-task', 'nomad_job:test-job', 'nomad_group:test-group']
CO_ID = 1234


class TestNomadUtil(unittest.TestCase):
    @mock.patch('docker.Client.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_extract_tags(self, mock_init, mock_inspect):
        nomad = NomadUtil()

        mock_inspect.return_value = {'Config': {'Env': ENV}}
        mock_init.return_value = None
        co = {'Id': CO_ID, 'Created': 1}

        tags = nomad.extract_container_tags(co)

        self.assertEqual(sorted(EXPECTED_TAGS), sorted(tags))

    @mock.patch('docker.Client.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_cache_invalidation_created_timestamp(self, mock_init, mock_inspect):
        nomad = NomadUtil()

        mock_inspect.return_value = {'Config': {'Env': ENV}}
        mock_init.return_value = None
        co = {'Id': CO_ID, 'Created': 1}
        nomad.extract_container_tags(co)

        self.assertTrue(CO_ID in nomad._container_tags_cache)
        mock_inspect.assert_called_once()

        # Cache is used
        nomad.extract_container_tags(co)
        mock_inspect.assert_called_once()

        # Different timestamp: cache is invalidated
        nomad.extract_container_tags({'Id': CO_ID, 'Created': 2})
        self.assertEqual(2, mock_inspect.call_count)

    @mock.patch('docker.Client.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_cache_invalidation_event(self, mock_init, mock_inspect):
        nomad = NomadUtil()

        mock_inspect.return_value = {'Config': {'Env': ENV}}
        mock_init.return_value = None
        co = {'Id': CO_ID, 'Created': 1}
        nomad.extract_container_tags(co)

        self.assertTrue(CO_ID in nomad._container_tags_cache)

        EVENT = {'status': 'die', 'id': CO_ID}
        nomad.invalidate_cache([EVENT])

        self.assertFalse(CO_ID in nomad._container_tags_cache)

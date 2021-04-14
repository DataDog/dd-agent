# stdlib
import unittest
import os

# 3rd party
import mock

# project
from utils.orchestrator import NomadUtil

# MockResponse class
from .test_orchestrator import MockResponse

ENV = ['NOMAD_TASK_NAME=test-task',
       'NOMAD_JOB_NAME=test-job',
       'NOMAD_ALLOC_NAME=test-task.test-group[0]']
EXPECTED_TAGS = ['nomad_task:test-task', 'nomad_job:test-job', 'nomad_group:test-group']
CO_ID = 1234


class TestNomadUtil(unittest.TestCase):
    @mock.patch('docker.Client.__init__')
    def test_extract_tags(self, mock_init):
        mock_init.return_value = None
        nomad = NomadUtil()

        co = {'Id': CO_ID, 'Config': {'Env': ENV}}

        tags = nomad._get_cacheable_tags(CO_ID, co=co)
        self.assertEqual(sorted(EXPECTED_TAGS), sorted(tags))

    @mock.patch.dict(os.environ, {'NOMAD_ALLOC_ID': "test"})
    def test_detect(self):
        self.assertTrue(NomadUtil.is_detected())

    @mock.patch.dict(os.environ, {})
    def test_no_detect(self):
        self.assertFalse(NomadUtil.is_detected())

    @mock.patch('requests.get')
    @mock.patch('docker.Client.__init__')
    def test_host_metadata(self, mock_init, mock_get):
        mock_get.return_value = MockResponse({"config": {"Datacenter": "dc1", "Region": "global",
                                                         "Version": "0.5.4"}}, 200)
        mock_init.return_value = None

        util = NomadUtil()
        util.__init__()
        metadata = util.get_host_metadata()

        self.assertEqual({'nomad_version': '0.5.4', 'nomad_region': 'global', 'nomad_datacenter': 'dc1'}, metadata)

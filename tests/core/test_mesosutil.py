# stdlib
import unittest
import os

# 3rd party
import mock

# project
from utils.orchestrator import MesosUtil

# MockResponse class
from .test_orchestrator import MockResponse, CO_ID


class TestMesosUtil(unittest.TestCase):
    @mock.patch('docker.Client.__init__')
    def test_extract_tags(self, mock_init):
        mock_init.return_value = None
        mesos = MesosUtil()

        env = ["CHRONOS_JOB_NAME=app1_process-orders",
               "CHRONOS_JOB_OWNER=qa",
               "MARATHON_APP_ID=/system/dd-agent",
               "MESOS_TASK_ID=system_dd-agent.dcc75b42-4b87-11e7-9a62-70b3d5800001"]

        tags = ['marathon_app:/system/dd-agent',
                'chronos_job_owner:qa',
                'chronos_job:app1_process-orders']
        # Removed 'mesos_task:' because of high cardinality

        container = {'Config': {'Env': env}}

        self.assertEqual(sorted(tags), sorted(mesos._get_cacheable_tags(CO_ID, co=container)))

    @mock.patch('docker.Client.__init__')
    def test_dont_extract_empty_owner(self, mock_init):
        mock_init.return_value = None
        mesos = MesosUtil()

        env = ["CHRONOS_JOB_NAME=app1_process-orders",
               "CHRONOS_JOB_OWNER=",
               "MARATHON_APP_ID=/system/dd-agent"]

        tags = ['marathon_app:/system/dd-agent',
                'chronos_job:app1_process-orders']
        container = {'Config': {'Env': env}}

        self.assertEqual(sorted(tags), sorted(mesos._get_cacheable_tags(CO_ID, co=container)))

    @mock.patch.dict(os.environ, {"MESOS_TASK_ID": "test"})
    def test_detect(self):
        self.assertTrue(MesosUtil.is_detected())

    @mock.patch.dict(os.environ, {})
    def test_no_detect(self):
        self.assertFalse(MesosUtil.is_detected())

    @mock.patch.dict(os.environ, {"LIBPROCESS_IP": "a", "HOST": "b", "HOSTNAME": "c"})
    @mock.patch('requests.get')
    @mock.patch('docker.Client.__init__')
    def test_agents_detection(self, mock_init, mock_get):
        mock_get.side_effect = [
            MockResponse({}, 404),  # LIBPROCESS_IP fails
            MockResponse({'badfield': 'fail'}, 200),  # HOST is invalid reply
            MockResponse({'version': '1.2.1'}, 200),  # HOSTNAME is valid reply
            MockResponse({'dcos_version': '1.9.0'}, 200),  # LIBPROCESS_IP works for DCOS
            # _detect_agent might run twice if first MesosUtil instance, duplicating test data
            MockResponse({}, 404),  # LIBPROCESS_IP fails
            MockResponse({'badfield': 'fail'}, 200),  # HOST is invalid reply
            MockResponse({'version': '1.2.1'}, 200),  # HOSTNAME is valid reply
            MockResponse({'dcos_version': '1.9.0'}, 200),  # LIBPROCESS_IP works for DCOS
        ]
        mock_init.return_value = None

        mesos, dcos = MesosUtil()._detect_agents()
        self.assertEqual('http://c:5051/version', mesos)
        self.assertEqual('http://a:61001/system/health/v1', dcos)

    @mock.patch.dict(os.environ, {"LIBPROCESS_IP": "a"})
    @mock.patch('requests.get')
    @mock.patch('docker.Client.__init__')
    def test_host_metadata(self, mock_init, mock_get):
        mock_get.side_effect = [
            MockResponse({'version': '1.2.1'}, 200),
            MockResponse({'dcos_version': '1.9.0'}, 200),
            MockResponse({'version': '1.2.1'}, 200),
            MockResponse({'dcos_version': '1.9.0'}, 200),
            # _detect_agent might run twice if first MesosUtil instance, duplicating test data
            MockResponse({'version': '1.2.1'}, 200),
            MockResponse({'dcos_version': '1.9.0'}, 200),
        ]
        mock_init.return_value = None

        util = MesosUtil()
        util.__init__()
        metadata = util.get_host_metadata()

        self.assertEqual({'mesos_version': '1.2.1', 'dcos_version': '1.9.0'}, metadata)

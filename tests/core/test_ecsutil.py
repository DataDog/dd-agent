# stdlib
import unittest

# 3rd party
import mock

# project
from utils.orchestrator import ECSUtil

# MockResponse class
from .test_orchestrator import MockResponse

CO_ID = "123456789123456789"


class TestECSUtil(unittest.TestCase):
    @mock.patch('requests.get')
    @mock.patch('docker.Client.__init__')
    def test_extract_tags(self, mock_init, mock_get):
        mock_get.return_value = MockResponse({}, 404)
        mock_init.return_value = None
        util = ECSUtil()
        util.agent_url = 'http://dummy'

        mock_get.reset_mock()
        mock_get.return_value = MockResponse({"Tasks": [{"Family": "dd-agent-latest", "Version": "12",
                                                         "Containers": [{"DockerId": CO_ID}]}]}, 200)

        tags = util._get_cacheable_tags(CO_ID)
        self.assertEqual(['task_name:dd-agent-latest', 'task_version:12'], tags)
        mock_get.assert_called_once_with('http://dummy/v1/tasks', timeout=1)

    @mock.patch('requests.get')
    @mock.patch('utils.dockerutil.DockerUtil.get_gateway')
    @mock.patch('utils.dockerutil.DockerUtil.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_detect_agent(self, mock_init, mock_inspect, mock_gw, mock_get):
        mock_get.return_value = MockResponse({}, 404)
        mock_init.return_value = None
        mock_gw.return_value = "10.0.2.2"

        mock_inspect.return_value = {'NetworkSettings': {'Networks': {'bridge': {'IPAddress': '10.0.0.42'}},
                                                         'Ports': {'1234/tcp': '1234/tcp'}}}

        probe_calls = [mock.call('http://10.0.0.42:1234/', timeout=1),
                       mock.call('http://10.0.2.2:51678/', timeout=1),
                       mock.call('http://localhost:51678/', timeout=1)]

        util = ECSUtil()

        mock_get.reset_mock()
        util._detect_agent()
        mock_get.assert_has_calls(probe_calls)

    @mock.patch('requests.get')
    @mock.patch('utils.dockerutil.DockerUtil.inspect_container')
    @mock.patch('docker.Client.__init__')
    def test_host_metadata(self, mock_init, mock_inspect, mock_get):
        mock_inspect.return_value = {}
        mock_get.return_value = MockResponse({"Cluster": "default-xvello",
                                              "Version": "Amazon ECS Agent - v1.14.1 (467c3d7)"}, 200)
        mock_init.return_value = None

        util = ECSUtil()
        util.agent_url = 'http://dummy'

        mock_get.reset_mock()
        meta = util.get_host_metadata()
        self.assertEqual({'ecs_version': '1.14.1'}, meta)
        mock_get.assert_called_once_with('http://dummy/v1/metadata', timeout=1)

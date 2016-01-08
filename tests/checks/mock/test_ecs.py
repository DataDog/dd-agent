# 3rd party
import mock
import json

from tests.checks.common import AgentCheckTest, load_check

MOCK_CONFIG = {
    'init_config': {},
    'instances' : [{
        'region': 'us-east-1'
    }]
}

def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, data, status_code):
            self.data = data
            self.status_code = status_code

        def json(self):
            return self.data

        def raise_for_status(self):
            return True

    return MockResponse({
        'Cluster': 'default',
        'ContainerInstanceArn': 'arn:aws:ecs:us-east-1:012345678910:container-instance/c9c9a6f2-8766-464b-8805-9c57b9368fb0',
    }, 200)

class MockECSClient:
    def __init__(self, container_instances):
        self.container_instances = container_instances

    def describe_container_instances(self, container_instances, cluster=None):
        return {
                'containerInstances': self.container_instances,
                'failures': [] }

class TestCheckECS(AgentCheckTest):
    CHECK_NAME = 'ecs'

    def mock_agent_connected(self, instance):
        return MockECSClient([{ 'agentConnected': True, }])

    def mock_agent_disconnected(self, instance):
        return MockECSClient([{ 'agentConnected': False, }])

    def mock_agent_not_found(self, instance):
        return MockECSClient([])

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_agent_connected(self, mock_requests):
        self.run_check(MOCK_CONFIG, mocks={'connect_to_region': self.mock_agent_connected})
        self.assertServiceCheckOK('ecs.agent_connected')

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_agent_disconnected(self, mock_requests):
        self.run_check(MOCK_CONFIG, mocks={'connect_to_region': self.mock_agent_disconnected})
        self.assertServiceCheckWarning('ecs.agent_connected')

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_agent_not_found(self, mock_requests):
        self.run_check(MOCK_CONFIG, mocks={'connect_to_region': self.mock_agent_not_found})
        self.assertServiceCheckUnknown('ecs.agent_connected')

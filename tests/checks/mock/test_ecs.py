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

def mock_metadata_response(*args, **kwargs):
    response = mock.Mock()
    response.status_code = 200
    response.json.return_value = {
        'Cluster': 'default',
        'ContainerInstanceArn': 'arn:aws:ecs:us-east-1:012345678910:container-instance/c9c9a6f2-8766-464b-8805-9c57b9368fb0' }
    return response

def mock_connection_refused(*args, **kwargs):
    raise TestFailed

class TestFailed(Exception):
    pass

def mock_ecs_client(agent_connected=None):
    container_instances = []
    if agent_connected is not None:
        container_instances.append({ 'agentConnected': agent_connected })
    mock_client = mock.Mock()
    mock_client.describe_container_instances.return_value = {
            'DescribeContainerInstancesResponse': {
                'DescribeContainerInstancesResult': {
                    'containerInstances': container_instances }}}
    return mock_client

class TestCheckECS(AgentCheckTest):
    CHECK_NAME = 'ecs'

    def mock_agent_connected(self, instance):
        return mock_ecs_client(agent_connected=True)

    def mock_agent_disconnected(self, instance):
        return mock_ecs_client(agent_connected=False)

    def mock_agent_not_found(self, instance):
        return mock_ecs_client()

    @mock.patch('requests.get', side_effect=mock_metadata_response)
    def test_agent_connected(self, mock_requests):
        self.run_check(MOCK_CONFIG, mocks={ 'connect_to_region': self.mock_agent_connected })
        self.assertServiceCheckOK('ecs.agent_connected')

    @mock.patch('requests.get', side_effect=mock_metadata_response)
    def test_agent_disconnected(self, mock_requests):
        self.run_check(MOCK_CONFIG, mocks={ 'connect_to_region': self.mock_agent_disconnected })
        self.assertServiceCheckWarning('ecs.agent_connected')

    @mock.patch('requests.get', side_effect=mock_metadata_response)
    def test_agent_not_found(self, mock_requests):
        self.run_check(MOCK_CONFIG, mocks={ 'connect_to_region': self.mock_agent_not_found })
        self.assertServiceCheckUnknown('ecs.agent_connected')

    @mock.patch('requests.get', side_effect=mock_connection_refused)
    def test_agent_not_running(self, mock_requests):
        self.assertRaises(TestFailed, lambda: self.run_check(MOCK_CONFIG))
        self.assertServiceCheckCritical('ecs.agent_connected')

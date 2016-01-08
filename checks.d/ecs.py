# stdlib
import requests

# 3rd party
from boto.regioninfo import get_regions
from boto.ec2containerservice.layer1 import EC2ContainerServiceConnection

# project
from checks import AgentCheck

# URL for the ECS introspection API: http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-agent-introspection.html
METADATA_URL = 'http://127.0.0.1:51678/v1/metadata'

# The name of the service check we'll use to report agent connection status.
SERVICE_CHECK = 'ecs.agent_connected'


class ECS(AgentCheck):
    """Tracks agent connection status
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        ecs = self.connect_to_region(instance.get('region'))

        metadata = requests.get(METADATA_URL).json()
        cluster = metadata.get('Cluster')
        container_instance = metadata.get('ContainerInstanceArn')

        desc = ecs.describe_container_instances(container_instance, cluster)
        container_instances = desc.get('containerInstances')

        if len(container_instances) == 0:
            return self.service_check(SERVICE_CHECK, AgentCheck.UNKNOWN)
        if container_instances[0].get('agentConnected') == True:
            return self.service_check(SERVICE_CHECK, AgentCheck.OK)
        else:
            return self.service_check(SERVICE_CHECK, AgentCheck.WARNING)

    def connect_to_region(region_name, **kw_params):
        for region in regions():
            if region.name == region_name:
                return region.connect(**kw_params)
        return None

# Unfortunately, the stable release of boto doesn't include https://github.com/boto/boto/pull/3143.
def regions():
    return get_regions('ec2containerservice', connection_cls=EC2ContainerServiceConnection)


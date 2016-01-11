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


# Unfortunately, the stable release of boto doesn't include https://github.com/boto/boto/pull/3143.
def regions():
    return get_regions('ec2containerservice', connection_cls=EC2ContainerServiceConnection)

class ECS(AgentCheck):
    """Tracks agent connection status
    """

    def check(self, instance):
        try:
            state = self.state(instance)
            self.service_check(SERVICE_CHECK, state)
        except:
            self.service_check(SERVICE_CHECK, AgentCheck.CRITICAL)
            raise

    def state(self, instance):
        ecs = self.connect_to_region(instance.get('region'))

        metadata = requests.get(METADATA_URL).json()
        cluster = metadata.get('Cluster')
        container_instance = metadata['ContainerInstanceArn']

        desc = ecs.describe_container_instances(container_instance, cluster)
        container_instances = desc['DescribeContainerInstancesResponse']['DescribeContainerInstancesResult']['containerInstances']

        if not container_instances:
            return AgentCheck.UNKNOWN
        if container_instances[0].get('agentConnected'):
            return AgentCheck.OK
        else:
            return AgentCheck.WARNING

    def connect_to_region(self, region_name, **kwargs):
        for region in regions():
            if region.name == region_name:
                return region.connect(**kwargs)
        return None

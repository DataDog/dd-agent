# stdlib
from urlparse import urljoin

# 3rd party
import mock
import json

from tests.checks.common import AgentCheckTest, Fixtures

# IDs
CLUSTER_NAME = 'SparkCluster'

# Resource manager URI
RM_ADDRESS = 'http://localhost:8088'

# Service URLs
YARN_CLUSTER_METRICS_URL = urljoin(RM_ADDRESS, '/ws/v1/cluster/metrics')
YARN_APPS_URL = urljoin(RM_ADDRESS, '/ws/v1/cluster/apps') + '?states=RUNNING'
YARN_NODES_URL = urljoin(RM_ADDRESS, '/ws/v1/cluster/nodes')


def requests_get_mock(*args, **kwargs):

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == YARN_CLUSTER_METRICS_URL:
        with open(Fixtures.file('cluster_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_APPS_URL:
        with open(Fixtures.file('apps_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_NODES_URL:
        with open(Fixtures.file('nodes_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)


class YARNCheck(AgentCheckTest):
    CHECK_NAME = 'yarn'

    YARN_CONFIG = {
        'resourcemanager_uri': 'http://localhost:8088',
        'cluster_name': CLUSTER_NAME
    }

    YARN_CLUSTER_METRICS_VALUES = {
        'yarn.metrics.apps_submitted': 0,
        'yarn.metrics.apps_completed': 0,
        'yarn.metrics.apps_pending': 0,
        'yarn.metrics.apps_running': 0,
        'yarn.metrics.apps_failed': 0,
        'yarn.metrics.apps_killed': 0,
        'yarn.metrics.reserved_mb': 0,
        'yarn.metrics.available_mb': 17408,
        'yarn.metrics.allocated_mb': 0,
        'yarn.metrics.total_mb': 17408,
        'yarn.metrics.reserved_virtual_cores': 0,
        'yarn.metrics.available_virtual_cores': 7,
        'yarn.metrics.allocated_virtual_cores': 1,
        'yarn.metrics.total_virtual_cores': 8,
        'yarn.metrics.containers_allocated': 0,
        'yarn.metrics.containers_reserved': 0,
        'yarn.metrics.containers_pending': 0,
        'yarn.metrics.total_nodes': 1,
        'yarn.metrics.active_nodes': 1,
        'yarn.metrics.lost_nodes': 0,
        'yarn.metrics.unhealthy_nodes': 0,
        'yarn.metrics.decommissioned_nodes': 0,
        'yarn.metrics.rebooted_nodes': 0,
    }

    YARN_CLUSTER_METRICS_TAGS = ['cluster_name:%s' % CLUSTER_NAME]

    YARN_APP_METRICS_VALUES = {
        'yarn.apps.progress': 100,
        'yarn.apps.started_time': 1326815573334,
        'yarn.apps.finished_time': 1326815598530,
        'yarn.apps.elapsed_time': 25196,
        'yarn.apps.allocated_mb': 0,
        'yarn.apps.allocated_vcores': 0,
        'yarn.apps.running_containers': 0,
        'yarn.apps.memory_seconds': 151730,
        'yarn.apps.vcore_seconds': 103,
    }

    YARN_APP_METRICS_TAGS = [
        'cluster_name:%s' % CLUSTER_NAME,
        'app_name:word count'
    ]

    YARN_NODE_METRICS_VALUES = {
        'yarn.node.last_health_update': 1324056895432,
        'yarn.node.used_memory_mb': 0,
        'yarn.node.avail_memory_mb': 8192,
        'yarn.node.used_virtual_cores': 0,
        'yarn.node.available_virtual_cores': 8,
        'yarn.node.num_containers': 0,
    }

    YARN_NODE_METRICS_TAGS = [
        'cluster_name:%s' % CLUSTER_NAME,
        'node_id:h2:1235'
    ]

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_check(self, mock_requests):
        config = {
            'instances': [self.YARN_CONFIG]
        }

        self.run_check(config)

        # Check the YARN Cluster Metrics
        for metric, value in self.YARN_CLUSTER_METRICS_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.YARN_CLUSTER_METRICS_TAGS)

        # Check the YARN App Metrics
        for metric, value in self.YARN_APP_METRICS_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.YARN_APP_METRICS_TAGS)

        # Check the YARN Node Metrics
        for metric, value in self.YARN_NODE_METRICS_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.YARN_NODE_METRICS_TAGS)

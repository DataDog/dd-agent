# stdlib
from urlparse import urljoin

# 3rd party
import mock
import json

from tests.checks.common import AgentCheckTest, Fixtures

# IDs
YARN_APP_ID = 'application_1459362484344_0011'
SPARK_APP_ID = 'app_001'
CLUSTER_NAME = 'SparkCluster'
APP_NAME = 'PySparkShell'

# Resource manager URI
RM_URI = 'http://localhost:8088'

# URL Paths
YARN_APPS_PATH = 'ws/v1/cluster/apps'
SPARK_REST_PATH = 'api/v1/applications'

# Service Check Names
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'


def join_url_dir(url, *args):
    '''
    Join a URL with multiple directories
    '''
    for path in args:
        url = url.rstrip('/') + '/'
        url = urljoin(url, path.lstrip('/'))

    return url

# Service URLs
YARN_APP_URL = urljoin(RM_URI, YARN_APPS_PATH) + '?states=RUNNING&applicationTypes=SPARK'
SPARK_APP_URL = join_url_dir(RM_URI, 'proxy', YARN_APP_ID, SPARK_REST_PATH)
SPARK_JOB_URL = join_url_dir(RM_URI, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'jobs')
SPARK_STAGE_URL = join_url_dir(RM_URI, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'stages')
SPARK_EXECUTOR_URL = join_url_dir(RM_URI, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'executors')
SPARK_RDD_URL = join_url_dir(RM_URI, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')


def requests_get_mock(*args, **kwargs):

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == YARN_APP_URL:
        with open(Fixtures.file('apps_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == SPARK_APP_URL:
        with open(Fixtures.file('spark_apps'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == SPARK_JOB_URL:
        with open(Fixtures.file('job_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == SPARK_STAGE_URL:
        with open(Fixtures.file('stage_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == SPARK_EXECUTOR_URL:
        with open(Fixtures.file('executor_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == SPARK_RDD_URL:
        with open(Fixtures.file('rdd_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)


class SparkCheck(AgentCheckTest):
    CHECK_NAME = 'spark'

    SPARK_CONFIG = {
        'resourcemanager_uri': 'http://localhost:8088',
        'cluster_name': CLUSTER_NAME
    }

    SPARK_JOB_RUNNING_METRIC_VALUES = {
        'spark.job.count': 2,
        'spark.job.num_tasks': 20,
        'spark.job.num_active_tasks': 30,
        'spark.job.num_completed_tasks': 40,
        'spark.job.num_skipped_tasks': 50,
        'spark.job.num_failed_tasks': 60,
        'spark.job.num_active_stages': 70,
        'spark.job.num_completed_stages': 80,
        'spark.job.num_skipped_stages': 90,
        'spark.job.num_failed_stages': 100
    }

    SPARK_JOB_RUNNING_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:running',
    ]

    SPARK_JOB_SUCCEEDED_METRIC_VALUES = {
        'spark.job.count': 3,
        'spark.job.num_tasks': 1000,
        'spark.job.num_active_tasks': 2000,
        'spark.job.num_completed_tasks': 3000,
        'spark.job.num_skipped_tasks': 4000,
        'spark.job.num_failed_tasks': 5000,
        'spark.job.num_active_stages': 6000,
        'spark.job.num_completed_stages': 7000,
        'spark.job.num_skipped_stages': 8000,
        'spark.job.num_failed_stages': 9000
    }

    SPARK_JOB_SUCCEEDED_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:succeeded',
    ]

    SPARK_STAGE_RUNNING_METRIC_VALUES = {
        'spark.stage.count': 3,
        'spark.stage.num_active_tasks': 3*3,
        'spark.stage.num_complete_tasks': 4*3,
        'spark.stage.num_failed_tasks': 5*3,
        'spark.stage.executor_run_time': 6*3,
        'spark.stage.input_bytes': 7*3,
        'spark.stage.input_records': 8*3,
        'spark.stage.output_bytes': 9*3,
        'spark.stage.output_records': 10*3,
        'spark.stage.shuffle_read_bytes': 11*3,
        'spark.stage.shuffle_read_records': 12*3,
        'spark.stage.shuffle_write_bytes': 13*3,
        'spark.stage.shuffle_write_records': 14*3,
        'spark.stage.memory_bytes_spilled': 15*3,
        'spark.stage.disk_bytes_spilled': 16*3,
    }

    SPARK_STAGE_RUNNING_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:running',
    ]

    SPARK_STAGE_COMPLETE_METRIC_VALUES = {
        'spark.stage.count': 2,
        'spark.stage.num_active_tasks': 100*2,
        'spark.stage.num_complete_tasks': 101*2,
        'spark.stage.num_failed_tasks': 102*2,
        'spark.stage.executor_run_time': 103*2,
        'spark.stage.input_bytes': 104*2,
        'spark.stage.input_records': 105*2,
        'spark.stage.output_bytes': 106*2,
        'spark.stage.output_records': 107*2,
        'spark.stage.shuffle_read_bytes': 108*2,
        'spark.stage.shuffle_read_records': 109*2,
        'spark.stage.shuffle_write_bytes': 110*2,
        'spark.stage.shuffle_write_records': 111*2,
        'spark.stage.memory_bytes_spilled': 112*2,
        'spark.stage.disk_bytes_spilled': 113*2,
    }

    SPARK_STAGE_COMPLETE_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:complete',
    ]

    SPARK_DRIVER_METRIC_VALUES = {
        'spark.driver.rdd_blocks': 99,
        'spark.driver.memory_used': 98,
        'spark.driver.disk_used': 97,
        'spark.driver.active_tasks': 96,
        'spark.driver.failed_tasks': 95,
        'spark.driver.completed_tasks': 94,
        'spark.driver.total_tasks': 93,
        'spark.driver.total_duration': 92,
        'spark.driver.total_input_bytes': 91,
        'spark.driver.total_shuffle_read': 90,
        'spark.driver.total_shuffle_write': 89,
        'spark.driver.max_memory': 278019440,
    }

    SPARK_EXECUTOR_METRIC_VALUES = {
        'spark.executor.count': 2,
        'spark.executor.rdd_blocks': 1,
        'spark.executor.memory_used': 2,
        'spark.executor.disk_used': 3,
        'spark.executor.active_tasks': 4,
        'spark.executor.failed_tasks': 5,
        'spark.executor.completed_tasks': 6,
        'spark.executor.total_tasks': 7,
        'spark.executor.total_duration': 8,
        'spark.executor.total_input_bytes': 9,
        'spark.executor.total_shuffle_read': 10,
        'spark.executor.total_shuffle_write': 11,
        'spark.executor.max_memory': 555755765,
    }

    SPARK_RDD_METRIC_VALUES = {
        'spark.rdd.count': 1,
        'spark.rdd.num_partitions': 2,
        'spark.rdd.num_cached_partitions': 2,
        'spark.rdd.memory_used': 284,
        'spark.rdd.disk_used': 0,
    }

    SPARK_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME
    ]


    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_check(self, mock_requests):
        config = {
            'instances': [self.SPARK_CONFIG]
        }

        self.run_check(config)

        # Check the running job metrics
        for metric, value in self.SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_JOB_RUNNING_METRIC_TAGS)

        # Check the succeeded job metrics
        for metric, value in self.SPARK_JOB_SUCCEEDED_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_JOB_SUCCEEDED_METRIC_TAGS)

        # Check the running stage metrics
        for metric, value in self.SPARK_STAGE_RUNNING_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_STAGE_RUNNING_METRIC_TAGS)

        # Check the complete stage metrics
        for metric, value in self.SPARK_STAGE_COMPLETE_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_STAGE_COMPLETE_METRIC_TAGS)

        # Check the driver metrics
        for metric, value in self.SPARK_DRIVER_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_METRIC_TAGS)

        # Check the executor metrics
        for metric, value in self.SPARK_EXECUTOR_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_METRIC_TAGS)

        # Check the RDD metrics
        for metric, value in self.SPARK_RDD_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_METRIC_TAGS)

        # Check the service tests
        self.assertServiceCheckOK(YARN_SERVICE_CHECK,
            tags=['url:http://localhost:8088'])
        self.assertServiceCheckOK(SPARK_SERVICE_CHECK,
            tags=['url:http://localhost:8088'])

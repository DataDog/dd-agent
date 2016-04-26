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
INFO_PATH = 'ws/v1/cluster/info'

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
CLUSTER_INFO_URL = urljoin(RM_URI, INFO_PATH)
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

    if args[0] == CLUSTER_INFO_URL:
        with open(Fixtures.file('cluster_info'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_APP_URL:
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
        'spark.job.num_tasks.max': 20,
        'spark.job.num_active_tasks.max': 30,
        'spark.job.num_completed_tasks.max': 40,
        'spark.job.num_skipped_tasks.max': 50,
        'spark.job.num_failed_tasks.max': 60,
        'spark.job.num_active_stages.max': 70,
        'spark.job.num_completed_stages.max': 80,
        'spark.job.num_skipped_stages.max': 90,
        'spark.job.num_failed_stages.max': 100
    }

    SPARK_JOB_RUNNING_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:running',
    ]


    SPARK_JOB_SUCCEEDED_METRIC_VALUES = {
        'spark.job.count': 3,
        'spark.job.num_tasks.max': 1000,
        'spark.job.num_active_tasks.max': 2000,
        'spark.job.num_completed_tasks.max': 3000,
        'spark.job.num_skipped_tasks.max': 4000,
        'spark.job.num_failed_tasks.max': 5000,
        'spark.job.num_active_stages.max': 6000,
        'spark.job.num_completed_stages.max': 7000,
        'spark.job.num_skipped_stages.max': 8000,
        'spark.job.num_failed_stages.max': 9000
    }

    SPARK_JOB_SUCCEEDED_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:succeeded',
    ]

    SPARK_STAGE_RUNNING_METRIC_VALUES = {
        'spark.stage.count': 3,
        'spark.stage.num_active_tasks.max': 3,
        'spark.stage.num_complete_tasks.max': 4,
        'spark.stage.num_failed_tasks.max': 5,
        'spark.stage.executor_run_time.max': 6,
        'spark.stage.input_bytes.max': 7,
        'spark.stage.input_records.max': 8,
        'spark.stage.output_bytes.max': 9,
        'spark.stage.output_records.max': 10,
        'spark.stage.shuffle_read_bytes.max': 11,
        'spark.stage.shuffle_read_records.max': 12,
        'spark.stage.shuffle_write_bytes.max': 13,
        'spark.stage.shuffle_write_records.max': 14,
        'spark.stage.memory_bytes_spilled.max': 15,
        'spark.stage.disk_bytes_spilled.max': 16,
    }

    SPARK_STAGE_RUNNING_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'status:running',
    ]

    SPARK_STAGE_COMPLETE_METRIC_VALUES = {
        'spark.stage.count': 2,
        'spark.stage.num_active_tasks.max': 100,
        'spark.stage.num_complete_tasks.max': 101,
        'spark.stage.num_failed_tasks.max': 102,
        'spark.stage.executor_run_time.max': 103,
        'spark.stage.input_bytes.max': 104,
        'spark.stage.input_records.max': 105,
        'spark.stage.output_bytes.max': 106,
        'spark.stage.output_records.max': 107,
        'spark.stage.shuffle_read_bytes.max': 108,
        'spark.stage.shuffle_read_records.max': 109,
        'spark.stage.shuffle_write_bytes.max': 110,
        'spark.stage.shuffle_write_records.max': 111,
        'spark.stage.memory_bytes_spilled.max': 112,
        'spark.stage.disk_bytes_spilled.max': 113,
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
        'spark.executor.rdd_blocks.max': 1,
        'spark.executor.memory_used.max': 2,
        'spark.executor.disk_used.max': 3,
        'spark.executor.active_tasks.max': 4,
        'spark.executor.failed_tasks.max': 5,
        'spark.executor.completed_tasks.max': 6,
        'spark.executor.total_tasks.max': 7,
        'spark.executor.total_duration.max': 8,
        'spark.executor.total_input_bytes.max': 9,
        'spark.executor.total_shuffle_read.max': 10,
        'spark.executor.total_shuffle_write.max': 11,
        'spark.executor.max_memory.max': 555755765,
    }

    SPARK_RDD_METRIC_VALUES = {
        'spark.rdd.count': 1,
        'spark.rdd.num_partitions.max': 2,
        'spark.rdd.num_cached_partitions.max': 2,
        'spark.rdd.memory_used.max': 284,
        'spark.rdd.disk_used.max': 0,
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

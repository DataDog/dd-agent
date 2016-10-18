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

# URLs for cluster managers
SPARK_APP_URL = 'http://localhost:4040'
SPARK_YARN_URL = 'http://localhost:8088'
SPARK_MESOS_URL = 'http://localhost:5050'
STANDALONE_URL = 'http://localhost:8080'

# URL Paths
SPARK_REST_PATH = 'api/v1/applications'
YARN_APPS_PATH = 'ws/v1/cluster/apps'
MESOS_APPS_PATH = 'frameworks'
STANDALONE_APPS_PATH = 'json/'
STANDALONE_APP_PATH_HTML = 'app/'

# Service Check Names
SPARK_SERVICE_CHECK = 'spark.application_master.can_connect'
YARN_SERVICE_CHECK = 'spark.resource_manager.can_connect'
MESOS_SERVICE_CHECK = 'spark.mesos_master.can_connect'
STANDALONE_SERVICE_CHECK = 'spark.standalone_master.can_connect'


def join_url_dir(url, *args):
    '''
    Join a URL with multiple directories
    '''
    for path in args:
        url = url.rstrip('/') + '/'
        url = urljoin(url, path.lstrip('/'))

    return url

# YARN Service URLs
YARN_APP_URL = urljoin(SPARK_YARN_URL, YARN_APPS_PATH) + '?states=RUNNING&applicationTypes=SPARK'
YARN_SPARK_APP_URL = join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH)
YARN_SPARK_JOB_URL = join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'jobs')
YARN_SPARK_STAGE_URL = join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'stages')
YARN_SPARK_EXECUTOR_URL = join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'executors')
YARN_SPARK_RDD_URL = join_url_dir(SPARK_YARN_URL, 'proxy', YARN_APP_ID, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')

# Mesos Service URLs
MESOS_APP_URL = urljoin(SPARK_MESOS_URL, MESOS_APPS_PATH)
MESOS_SPARK_APP_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH)
MESOS_SPARK_JOB_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs')
MESOS_SPARK_STAGE_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages')
MESOS_SPARK_EXECUTOR_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors')
MESOS_SPARK_RDD_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')

# Spark Standalone Service URLs
STANDALONE_APP_URL = urljoin(STANDALONE_URL, STANDALONE_APPS_PATH)
STANDALONE_APP_HTML_URL = urljoin(STANDALONE_URL, STANDALONE_APP_PATH_HTML) + '?appId=' + SPARK_APP_ID
STANDALONE_SPARK_APP_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH)
STANDALONE_SPARK_JOB_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'jobs')
STANDALONE_SPARK_STAGE_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'stages')
STANDALONE_SPARK_EXECUTOR_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'executors')
STANDALONE_SPARK_RDD_URL = join_url_dir(SPARK_APP_URL, SPARK_REST_PATH, SPARK_APP_ID, 'storage/rdd')


def yarn_requests_get_mock(*args, **kwargs):

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == YARN_APP_URL:
        with open(Fixtures.file('yarn_apps'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_SPARK_APP_URL:
        with open(Fixtures.file('spark_apps'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_SPARK_JOB_URL:
        with open(Fixtures.file('job_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_SPARK_STAGE_URL:
        with open(Fixtures.file('stage_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_SPARK_EXECUTOR_URL:
        with open(Fixtures.file('executor_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_SPARK_RDD_URL:
        with open(Fixtures.file('rdd_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

def mesos_requests_get_mock(*args, **kwargs):

    class MockMesosResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == MESOS_APP_URL:
        with open(Fixtures.file('mesos_apps'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif args[0] == MESOS_SPARK_APP_URL:
        with open(Fixtures.file('spark_apps'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif args[0] == MESOS_SPARK_JOB_URL:
        with open(Fixtures.file('job_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif args[0] == MESOS_SPARK_STAGE_URL:
        with open(Fixtures.file('stage_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif args[0] == MESOS_SPARK_EXECUTOR_URL:
        with open(Fixtures.file('executor_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

    elif args[0] == MESOS_SPARK_RDD_URL:
        with open(Fixtures.file('rdd_metrics'), 'r') as f:
            body = f.read()
            return MockMesosResponse(body, 200)

def standalone_requests_get_mock(*args, **kwargs):

    class MockStandaloneResponse:
        text = ''

        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json_data

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == STANDALONE_APP_URL:
        with open(Fixtures.file('spark_standalone_apps'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif args[0] == STANDALONE_APP_HTML_URL:
        with open(Fixtures.file('spark_standalone_app'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif args[0] == STANDALONE_SPARK_APP_URL:
        with open(Fixtures.file('spark_apps'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif args[0] == STANDALONE_SPARK_JOB_URL:
        with open(Fixtures.file('job_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif args[0] == STANDALONE_SPARK_STAGE_URL:
        with open(Fixtures.file('stage_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif args[0] == STANDALONE_SPARK_EXECUTOR_URL:
        with open(Fixtures.file('executor_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

    elif args[0] == STANDALONE_SPARK_RDD_URL:
        with open(Fixtures.file('rdd_metrics'), 'r') as f:
            body = f.read()
            return MockStandaloneResponse(body, 200)

class SparkCheck(AgentCheckTest):
    CHECK_NAME = 'spark'

    YARN_CONFIG = {
        'spark_url': 'http://localhost:8088',
        'cluster_name': CLUSTER_NAME,
        'spark_cluster_mode': 'spark_yarn_mode'
    }

    MESOS_CONFIG = {
        'spark_url': 'http://localhost:5050',
        'cluster_name': CLUSTER_NAME,
        'spark_cluster_mode': 'spark_mesos_mode'
    }

    STANDALONE_CONFIG = {
        'spark_url': 'http://localhost:8080',
        'cluster_name': CLUSTER_NAME,
        'spark_cluster_mode': 'spark_standalone_mode'
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


    @mock.patch('requests.get', side_effect=yarn_requests_get_mock)
    def test_yarn(self, mock_requests):
        config = {
            'instances': [self.YARN_CONFIG]
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


    @mock.patch('requests.get', side_effect=mesos_requests_get_mock)
    def test_mesos(self, mock_requests):
        config = {
            'instances': [self.MESOS_CONFIG]
        }

        self.run_check(config)

        # Check the running job metrics
        for metric, value in self.SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_JOB_RUNNING_METRIC_TAGS)

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
        self.assertServiceCheckOK(MESOS_SERVICE_CHECK,
            tags=['url:http://localhost:5050'])
        self.assertServiceCheckOK(SPARK_SERVICE_CHECK,
            tags=['url:http://localhost:4040'])


    @mock.patch('requests.get', side_effect=standalone_requests_get_mock)
    def test_standalone(self, mock_requests):
        config = {
            'instances': [self.STANDALONE_CONFIG]
        }

        self.run_check(config)

        # Check the running job metrics
        for metric, value in self.SPARK_JOB_RUNNING_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.SPARK_JOB_RUNNING_METRIC_TAGS)

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
        self.assertServiceCheckOK(STANDALONE_SERVICE_CHECK,
            tags=['url:http://localhost:8080'])
        self.assertServiceCheckOK(SPARK_SERVICE_CHECK,
            tags=['url:http://localhost:4040'])

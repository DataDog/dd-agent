# stdlib
from urlparse import urljoin

# 3rd party
import mock
import json

from tests.checks.common import AgentCheckTest, Fixtures

# ID
APP_ID = 'application_1453738555560_0001'
APP_NAME = 'WordCount'
JOB_ID = 'job_1453738555560_0001'
JOB_NAME = 'WordCount'
USER_NAME = 'vagrant'
TASK_ID = 'task_1453738555560_0001_m_000000'
CLUSTER_NAME = 'MapReduceCluster'

# Resource manager URI
RM_URI = 'http://localhost:8088'

# URL Paths
YARN_APPS_PATH = 'ws/v1/cluster/apps'
MAPREDUCE_JOBS_PATH = 'ws/v1/mapreduce/jobs'

# Service Check Names
YARN_SERVICE_CHECK = 'mapreduce.resource_manager.can_connect'
MAPREDUCE_SERVICE_CHECK = 'mapreduce.application_master.can_connect'

def join_url_dir(url, *args):
    '''
    Join a URL with multiple directories
    '''
    for path in args:
        url = url.rstrip('/') + '/'
        url = urljoin(url, path.lstrip('/'))

    return url


# Service URLs
YARN_APPS_URL = urljoin(RM_URI, YARN_APPS_PATH) + '?states=RUNNING&applicationTypes=MAPREDUCE'
MR_JOBS_URL = join_url_dir(RM_URI, 'proxy', APP_ID, MAPREDUCE_JOBS_PATH)
MR_JOB_COUNTERS_URL = join_url_dir(MR_JOBS_URL, JOB_ID, 'counters')
MR_TASKS_URL = join_url_dir(MR_JOBS_URL, JOB_ID, 'tasks')


def requests_get_mock(*args, **kwargs):

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == YARN_APPS_URL:
        with open(Fixtures.file('apps_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == MR_JOBS_URL:
        with open(Fixtures.file('job_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == MR_JOB_COUNTERS_URL:
        with open(Fixtures.file('job_counter_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == MR_TASKS_URL:
        with open(Fixtures.file('task_metrics'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)


class MapReduceCheck(AgentCheckTest):
    CHECK_NAME = 'mapreduce'

    MR_CONFIG = {
        'resourcemanager_uri': 'http://localhost:8088',
        'cluster_name': CLUSTER_NAME,
        'collect_task_metrics': 'true'
    }

    INIT_CONFIG = {
        'general_counters': [
            {
                'counter_group_name': 'org.apache.hadoop.mapreduce.FileSystemCounter',
                'counters': [
                    {'counter_name': 'FILE_BYTES_READ'},
                    {'counter_name': 'FILE_BYTES_WRITTEN'}
                ]
            }
        ],
        'job_specific_counters': [
            {
                'job_name': 'WordCount',
                'metrics': [
                    {
                        'counter_group_name': 'org.apache.hadoop.mapreduce.FileSystemCounter',
                        'counters': [
                            {'counter_name': 'FILE_BYTES_WRITTEN'}
                        ]
                    }, {
                        'counter_group_name': 'org.apache.hadoop.mapreduce.TaskCounter',
                        'counters': [
                            {'counter_name': 'MAP_OUTPUT_RECORDS'}
                        ]
                    }
                ]
            }
        ]
    }

    MAPREDUCE_JOB_METRIC_VALUES = {
        'mapreduce.job.elapsed_time.max': 99221829,
        'mapreduce.job.maps_total': 1,
        'mapreduce.job.maps_completed': 0,
        'mapreduce.job.reduces_total': 1,
        'mapreduce.job.reduces_completed': 0,
        'mapreduce.job.maps_pending': 0,
        'mapreduce.job.maps_running': 1,
        'mapreduce.job.reduces_pending': 1,
        'mapreduce.job.reduces_running': 0,
        'mapreduce.job.new_reduce_attempts': 1,
        'mapreduce.job.running_reduce_attempts': 0,
        'mapreduce.job.failed_reduce_attempts': 0,
        'mapreduce.job.killed_reduce_attempts': 0,
        'mapreduce.job.successful_reduce_attempts': 0,
        'mapreduce.job.new_map_attempts': 0,
        'mapreduce.job.running_map_attempts': 1,
        'mapreduce.job.failed_map_attempts': 1,
        'mapreduce.job.killed_map_attempts': 0,
        'mapreduce.job.successful_map_attempts': 0,
    }

    MAPREDUCE_JOB_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'job_name:' + JOB_NAME,
        'user_name:' + USER_NAME
    ]

    MAPREDUCE_MAP_TASK_METRIC_VALUES = {
        'mapreduce.job.map.task.elapsed_time.max': 99869037
    }

    MAPREDUCE_MAP_TASK_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'job_name:' + JOB_NAME,
        'user_name:' + USER_NAME,
        'task_type:map'
    ]

    MAPREDUCE_REDUCE_TASK_METRIC_VALUES = {
        'mapreduce.job.reduce.task.elapsed_time.max': 123456
    }

    MAPREDUCE_REDUCE_TASK_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'job_name:' + JOB_NAME,
        'user_name:' + USER_NAME,
        'task_type:reduce'
    ]

    MAPREDUCE_JOB_COUNTER_METRIC_VALUES = {
        'mapreduce.job.counter.total_counter_value': {'value': 0, 'tags': ['counter_name:file_bytes_read']},
        'mapreduce.job.counter.map_counter_value': {'value': 1, 'tags': ['counter_name:file_bytes_read']},
        'mapreduce.job.counter.reduce_counter_value': {'value': 2, 'tags': ['counter_name:file_bytes_read']},
        'mapreduce.job.counter.total_counter_value': {'value': 3, 'tags': ['counter_name:file_bytes_written']},
        'mapreduce.job.counter.map_counter_value': {'value': 4, 'tags': ['counter_name:file_bytes_written']},
        'mapreduce.job.counter.reduce_counter_value': {'value': 5, 'tags': ['counter_name:file_bytes_written']},
        'mapreduce.job.counter.total_counter_value': {'value': 9, 'tags': ['counter_name:map_output_records']},
        'mapreduce.job.counter.map_counter_value': {'value': 10, 'tags': ['counter_name:map_output_records']},
        'mapreduce.job.counter.reduce_counter_value': {'value': 11, 'tags': ['counter_name:map_output_records']},
    }

    MAPREDUCE_JOB_COUNTER_METRIC_TAGS = [
        'cluster_name:' + CLUSTER_NAME,
        'app_name:' + APP_NAME,
        'job_name:' + JOB_NAME,
        'user_name:' + USER_NAME
    ]

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_check(self, mock_requests):
        config = {
            'instances': [self.MR_CONFIG],
            'init_config': self.INIT_CONFIG
        }

        self.run_check(config)

        # Check the MapReduce job metrics
        for metric, value in self.MAPREDUCE_JOB_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.MAPREDUCE_JOB_METRIC_TAGS)

        # Check the map task metrics
        for metric, value in self.MAPREDUCE_MAP_TASK_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.MAPREDUCE_MAP_TASK_METRIC_TAGS)

        # Check the reduce task metrics
        for metric, value in self.MAPREDUCE_REDUCE_TASK_METRIC_VALUES.iteritems():
            self.assertMetric(metric,
                value=value,
                tags=self.MAPREDUCE_REDUCE_TASK_METRIC_TAGS)

        # Check the MapReduce job counter metrics
        for metric, attributes in self.MAPREDUCE_JOB_COUNTER_METRIC_VALUES.iteritems():
            tags = attributes['tags']
            tags.extend(self.MAPREDUCE_JOB_COUNTER_METRIC_TAGS)
            self.assertMetric(metric,
                value=attributes['value'],
                tags=tags)

        # Check the service tests
        self.assertServiceCheckOK(YARN_SERVICE_CHECK,
            tags=['url:http://localhost:8088'])
        self.assertServiceCheckOK(MAPREDUCE_SERVICE_CHECK,
            tags=['url:http://localhost:8088'])

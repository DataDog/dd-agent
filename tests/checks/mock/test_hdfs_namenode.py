# Project
from tests.checks.common import AgentCheckTest, Fixtures

# 3rd Party
import mock
import json

# Namenode URI
NAMENODE_JMX_URI = 'http://localhost:50070/jmx'

# Namesystem state URL
NAME_SYSTEM_STATE_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=FSNamesystemState'

# Namesystem url
NAME_SYSTEM_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=FSNamesystem'

def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            print self.json_data
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    print 'DEBUG: {0}'.format(args[0])
    print NAME_SYSTEM_STATE_URL

    if args[0] == NAME_SYSTEM_STATE_URL:
        print 'here'
        with open(Fixtures.file('hdfs_namesystem_state'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == NAME_SYSTEM_URL:
        print 'here'
        with open(Fixtures.file('hdfs_namesystem'), 'r') as f:
            body = f.read()
            return MockResponse(body, 200)

class HDFSNameNode(AgentCheckTest):
    CHECK_NAME = 'hdfs_namenode'

    HDFS_NAMENODE_CONFIG = {
        'hdfs_namenode_jmx_uri': 'http://localhost:50070'
    }

    HDFS_NAMESYSTEM_STATE_METRICS_VALUES = {
        'hdfs_namenode.capacity_total': 41167421440,
        'hdfs_namenode.capacity_used': 501932032,
        'hdfs_namenode.capacity_remaining': 27878948864,
        'hdfs_namenode.capacity_in_use': None,  # Don't test the value as it's a float
        'hdfs_namenode.total_load': 2,
        'hdfs_namenode.fs_lock_queue_length': 0,
        'hdfs_namenode.blocks_total': 27661,
        'hdfs_namenode.max_objects': 0,
        'hdfs_namenode.files_total': 82950,
        'hdfs_namenode.pending_replication_blocks': 0,
        'hdfs_namenode.under_replicated_blocks': 27661,
        'hdfs_namenode.scheduled_replication_blocks': 0,
        'hdfs_namenode.pending_deletion_blocks': 0,
        'hdfs_namenode.num_live_data_nodes': 1,
        'hdfs_namenode.num_dead_data_nodes': 0,
        'hdfs_namenode.num_decom_live_data_nodes': 0,
        'hdfs_namenode.num_decom_dead_data_nodes': 0,
        'hdfs_namenode.volume_failures_total': 0,
        'hdfs_namenode.estimated_capacity_lost_total': 0,
        'hdfs_namenode.num_decommissioning_data_nodes': 0,
        'hdfs_namenode.num_stale_data_nodes': 0,
        'hdfs_namenode.num_stale_storages': 0,
    }

    HDFS_NAMESYSTEM_METRICS_VALUES = {
        'hdfs_namenode.missing_blocks': 0,
        'hdfs_namenode.corrupt_blocks': 1,
    }

    HDFS_NAMESYSTEM_METRIC_TAGS = [
        'namenode_url:' + HDFS_NAMENODE_CONFIG['hdfs_namenode_jmx_uri']
    ]

    @mock.patch('requests.get', side_effect=requests_get_mock)
    def test_check(self, mock_requests):
        config = {
            'instances': [self.HDFS_NAMENODE_CONFIG]
        }

        self.run_check(config)

        for metric, value in self.HDFS_NAMESYSTEM_STATE_METRICS_VALUES.iteritems():
            self.assertMetric(metric, value=value, tags=self.HDFS_NAMESYSTEM_METRIC_TAGS)

        for metric, value in self.HDFS_NAMESYSTEM_METRICS_VALUES.iteritems():
            self.assertMetric(metric, value=value, tags=self.HDFS_NAMESYSTEM_METRIC_TAGS)

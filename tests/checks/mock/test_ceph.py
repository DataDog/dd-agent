# 3p
import simplejson as json

# project
from tests.checks.common import AgentCheckTest, Fixtures
from checks import AgentCheck

class TestCeph(AgentCheckTest):
    CHECK_NAME = 'ceph'

    def test_simple_metrics(self):
        mocks = {
            '_collect_raw': lambda x,y: json.loads(Fixtures.read_file('raw.json')),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)
        expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                         'ceph_mon_state:peon']
        expected_metrics = ['ceph.num_mons', 'ceph.total_objects', 'ceph.pgstate.active_clean']

        for metric in expected_metrics:
            self.assertMetric(metric, count=1, tags=expected_tags)

        self.assertServiceCheck('ceph.overall_status', status=AgentCheck.OK)

    def test_tagged_metrics(self):
        mocks = {
            '_collect_raw': lambda x,y: json.loads(Fixtures.read_file('raw.json')),
        }
        config = {
            'instances': [{'host': 'foo'}]
        }

        self.run_check_twice(config, mocks=mocks, force_reload=True)
        for osd in ['osd0', 'osd1', 'osd2']:
            expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                             'ceph_mon_state:peon',
                             'ceph_osd:%s' % osd]

            for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
                self.assertMetric(metric, count=1, tags=expected_tags)

        for pool in ['pool0', 'rbd']:
            expected_tags = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
                             'ceph_mon_state:peon',
                             'ceph_pool_name:%s' % pool]
            for metric in ['ceph.read_bytes', 'ceph.write_bytes', 'ceph.pct_used', 'ceph.num_objects']:
                self.assertMetric(metric, count=1, tags=expected_tags)

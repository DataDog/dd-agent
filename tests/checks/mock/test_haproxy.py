from collections import defaultdict
import copy

# 3p
import mock

# project
from tests.checks.common import AgentCheckTest


MOCK_DATA = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-4,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-5,0,0,0,1,,1,1,0,,0,,0,0,0,0,MAINT,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
c,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
c,i-2,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN (agent),1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
c,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,NO CHECK,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
c,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
"""

AGG_STATUSES_BY_SERVICE = (
    (['status:available', 'service:a'], 1),
    (['status:available', 'service:b'], 4),
    (['status:unavailable', 'service:b'], 2),
    (['status:available', 'service:c'], 1),
    (['status:unavailable', 'service:c'], 2)
)

AGG_STATUSES = (
    (['status:available'], 6),
    (['status:unavailable'], 4)
)


class TestCheckHAProxy(AgentCheckTest):
    CHECK_NAME = 'haproxy'

    BASE_CONFIG = {
        'init_config': None,
        'instances': [
            {
                'url': 'http://localhost/admin?stats',
                'collect_status_metrics': True,
            }
        ]
    }

    def _assert_agg_statuses(self, count_status_by_service=True, collate_status_tags_per_host=False):
        expected_statuses = AGG_STATUSES_BY_SERVICE if count_status_by_service else AGG_STATUSES
        for tags, value in expected_statuses:
            if collate_status_tags_per_host:
                # Assert that no aggregate statuses are sent
                self.assertMetric('haproxy.count_per_status', tags=tags, count=0)
            else:
                self.assertMetric('haproxy.count_per_status', value=value, tags=tags)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_agg_only(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        # with count_status_by_service set to False
        config['instances'][0]['count_status_by_service'] = False
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=2, tags=['status:open'])
        self.assertMetric('haproxy.count_per_status', value=4, tags=['status:up'])
        self.assertMetric('haproxy.count_per_status', value=2, tags=['status:down'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:maint'])
        self.assertMetric('haproxy.count_per_status', value=0, tags=['status:nolb'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:no_check'])

        self._assert_agg_statuses(count_status_by_service=False)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_by_service(self, mock_requests):
        self.run_check(self.BASE_CONFIG)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:open', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=3, tags=['status:up', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:open', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:down', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:maint', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:up', 'service:c'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:down', 'service:c'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['status:no_check', 'service:c'])

        self._assert_agg_statuses()

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_by_service_and_host(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:open', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:open', 'service:b'])
        for backend in ['i-1', 'i-2', 'i-3']:
            self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:up', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:down', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:maint', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:up', 'service:c'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:down', 'service:c'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:no_check', 'service:c'])

        self._assert_agg_statuses()

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_by_service_and_collate_per_host(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        config['instances'][0]['collate_status_tags_per_host'] = True
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:a'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:FRONTEND', 'status:available', 'service:b'])
        for backend in ['i-1', 'i-2', 'i-3']:
            self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:%s' % backend, 'status:available', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable', 'service:b'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-1', 'status:available', 'service:c'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable', 'service:c'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable', 'service:c'])

        self._assert_agg_statuses(collate_status_tags_per_host=True)

    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_per_status_collate_per_host(self, mock_requests):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['collect_status_metrics_by_host'] = True
        config['instances'][0]['collate_status_tags_per_host'] = True
        config['instances'][0]['count_status_by_service'] = False
        self.run_check(config)

        self.assertMetric('haproxy.count_per_status', value=2, tags=['backend:FRONTEND', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=2, tags=['backend:i-1', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-2', 'status:unavailable'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:available'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-3', 'status:unavailable'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-4', 'status:unavailable'])
        self.assertMetric('haproxy.count_per_status', value=1, tags=['backend:i-5', 'status:unavailable'])

        self._assert_agg_statuses(count_status_by_service=False, collate_status_tags_per_host=True)

    # This mock is only useful to make the first `run_check` run w/o errors (which in turn is useful only to initialize the check)
    @mock.patch('requests.get', return_value=mock.Mock(content=MOCK_DATA))
    def test_count_hosts_statuses(self, mock_requests):
        self.run_check(self.BASE_CONFIG)

        data = """# pxname,svname,qcur,qmax,scur,smax,slim,stot,bin,bout,dreq,dresp,ereq,econ,eresp,wretr,wredis,status,weight,act,bck,chkfail,chkdown,lastchg,downtime,qlimit,pid,iid,sid,throttle,lbtot,tracked,type,rate,rate_lim,rate_max,check_status,check_code,check_duration,hrsp_1xx,hrsp_2xx,hrsp_3xx,hrsp_4xx,hrsp_5xx,hrsp_other,hanafail,req_rate,req_rate_max,req_tot,cli_abrt,srv_abrt,
a,FRONTEND,,,1,2,12,1,11,11,0,0,0,,,,,OPEN,,,,,,,,,1,1,0,,,,0,1,0,2,,,,0,1,0,0,0,0,,1,1,1,,,
a,BACKEND,0,0,0,0,12,0,11,11,0,0,,0,0,0,0,UP,0,0,0,,0,1221810,0,,1,1,0,,0,,1,0,,0,,,,0,0,0,0,0,0,,,,,0,0,
b,FRONTEND,,,1,2,12,11,11,0,0,0,0,,,,,OPEN,,,,,,,,,1,2,0,,,,0,0,0,1,,,,,,,,,,,0,0,0,,,
b,i-1,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,1,1,30,,1,3,1,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-2,0,0,1,1,,1,1,0,,0,,0,0,0,0,UP 1/2,1,1,0,0,0,1,0,,1,3,2,,71,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-3,0,0,0,1,,1,1,0,,0,,0,0,0,0,UP,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-4,0,0,0,1,,1,1,0,,0,,0,0,0,0,DOWN,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,i-5,0,0,0,1,,1,1,0,,0,,0,0,0,0,MAINT,1,1,0,0,0,1,0,,1,3,3,,70,,2,0,,1,1,,0,,,,,,,0,,,,0,0,
b,BACKEND,0,0,1,2,0,421,1,0,0,0,,0,0,0,0,UP,6,6,0,,0,1,0,,1,3,0,,421,,1,0,,1,,,,,,,,,,,,,,0,0,
""".split('\n')

        # per service
        self.check._process_data(data, True, False, collect_status_metrics=True,
                                 collect_status_metrics_by_host=False)

        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'open')] = 1
        expected_hosts_statuses[('b', 'up')] = 3
        expected_hosts_statuses[('b', 'down')] = 1
        expected_hosts_statuses[('b', 'maint')] = 1
        expected_hosts_statuses[('a', 'open')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # backend hosts
        agg_statuses = self.check._process_backend_hosts_metric(expected_hosts_statuses)
        expected_agg_statuses = {
            'a': {'available': 0, 'unavailable': 0},
            'b': {'available': 3, 'unavailable': 2},
        }
        self.assertEquals(expected_agg_statuses, dict(agg_statuses))

        # with process_events set to True
        self.check._process_data(data, True, True, collect_status_metrics=True,
                                 collect_status_metrics_by_host=False)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        # per host
        self.check._process_data(data, True, False, collect_status_metrics=True,
                                 collect_status_metrics_by_host=True)
        expected_hosts_statuses = defaultdict(int)
        expected_hosts_statuses[('b', 'FRONTEND', 'open')] = 1
        expected_hosts_statuses[('a', 'FRONTEND', 'open')] = 1
        expected_hosts_statuses[('b', 'i-1', 'up')] = 1
        expected_hosts_statuses[('b', 'i-2', 'up')] = 1
        expected_hosts_statuses[('b', 'i-3', 'up')] = 1
        expected_hosts_statuses[('b', 'i-4', 'down')] = 1
        expected_hosts_statuses[('b', 'i-5', 'maint')] = 1
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

        self.check._process_data(data, True, True, collect_status_metrics=True,
                                 collect_status_metrics_by_host=True)
        self.assertEquals(self.check.hosts_statuses, expected_hosts_statuses)

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='etcd')
class CheckEtcdTest(AgentCheckTest):
    CHECK_NAME = "etcd"

    STORE_METRICS = [
        'compareanddelete.fail',
        'compareanddelete.success',
        'compareandswap.fail',
        'compareandswap.success',
        'create.fail',
        'create.success',
        'delete.fail',
        'delete.success',
        'expire.count',
        'gets.fail',
        'gets.success',
        'sets.fail',
        'sets.success',
        'update.fail',
        'update.success',
        'watchers',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {"instances": [{"url": "http://localhost:4001"}]}

    def test_metrics(self):
        self.run_check_twice(self.config)

        tags = ['url:http://localhost:4001', 'etcd_state:leader']

        for mname in self.STORE_METRICS:
            self.assertMetric('etcd.store.%s' % mname, tags=tags, count=1)

        self.assertMetric('etcd.self.send.appendrequest.count', tags=tags, count=1)
        self.assertMetric('etcd.self.recv.appendrequest.count', tags=tags, count=1)

        self.assertServiceCheckOK(self.check.SERVICE_CHECK_NAME,
                                  count=1,
                                  tags=['url:http://localhost:4001'])
        self.coverage_report()


    # FIXME: not really an integration test, should be pretty easy
    # to spin up a cluster to test that.
    def test_followers(self):
        mock = {
            "followers": {
                "etcd-node1": {
                    "counts": {
                        "fail": 1212,
                        "success": 4163176
                    },
                    "latency": {
                        "average": 2.7206299430775007,
                        "current": 1.486487,
                        "maximum": 2018.410279,
                        "minimum": 1.011763,
                        "standardDeviation": 6.246990702203536
                    }
                },
                "etcd-node3": {
                    "counts": {
                        "fail": 1378,
                        "success": 4164598
                    },
                    "latency": {
                        "average": 2.707100125761001,
                        "current": 1.666258,
                        "maximum": 1409.054765,
                        "minimum": 0.998415,
                        "standardDeviation": 5.910089773061448
                    }
                }
            },
            "leader": "etcd-node2"
        }

        mocks = {
            '_get_leader_metrics': lambda url, ssl, timeout: mock
        }

        self.run_check_twice(self.config, mocks=mocks)

        common_leader_tags = ['url:http://localhost:4001', 'etcd_state:leader']
        follower_tags = [
            common_leader_tags[:] + ['follower:etcd-node1'],
            common_leader_tags[:] + ['follower:etcd-node3'],
        ]

        for fol_tags in follower_tags:
            self.assertMetric('etcd.leader.counts.fail', count=1, tags=fol_tags)
            self.assertMetric('etcd.leader.counts.success', count=1, tags=fol_tags)
            self.assertMetric('etcd.leader.latency.avg', count=1, tags=fol_tags)
            self.assertMetric('etcd.leader.latency.min', count=1, tags=fol_tags)
            self.assertMetric('etcd.leader.latency.max', count=1, tags=fol_tags)
            self.assertMetric('etcd.leader.latency.stddev', count=1, tags=fol_tags)
            self.assertMetric('etcd.leader.latency.current', count=1, tags=fol_tags)

    def test_bad_config(self):
        self.assertRaises(Exception,
                          lambda: self.run_check({"instances": [{"url": "http://localhost:4001/test"}]}))

        self.assertServiceCheckCritical(self.check.SERVICE_CHECK_NAME,
                                        count=1,
                                        tags=['url:http://localhost:4001/test/v2/stats/self'])

        self.coverage_report()

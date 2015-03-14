import unittest
from tests.common import AgentCheckTest
from nose.plugins.attrib import attr
from time import sleep
from checks import AgentCheck
from requests.exceptions import Timeout

@attr(requires='etcd')
class EtcdTest(AgentCheckTest):

    CHECK_NAME = "etcd"
    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {"instances": [{"url": "http://localhost:4001"}]}

    def test_metrics(self):
        self.run_check(self.config)
        sleep(1)
        self.run_check(self.config)
        tags = ['url:http://localhost:4001', 'etcd_state:leader']
        self.assertMetric('etcd.store.gets.success', metric_value=0.0, tags=tags)
        self.assertMetric('etcd.store.gets.fail', metric_value=0.0, tags=tags)
        self.assertMetric('etcd.self.send.appendrequest.count', metric_value=0.0, tags=tags)


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
        self.run_check(self.config)
        sleep(1)
        # Monkey-patch json to avoid having to stand up a full cluster
        self.check._get_leader_metrics = lambda u, t: mock
        self.run_check(self.config)
        sleep(1)
        self.run_check(self.config)
        
        self.assertMetric('etcd.leader.counts.fail')
        self.assertMetric('etcd.leader.counts.success')
        self.assertMetric('etcd.leader.latency.avg')
        self.assertMetric('etcd.leader.latency.min')
        self.assertMetric('etcd.leader.latency.max')
        self.assertMetric('etcd.leader.latency.stddev')
        self.assertMetric('etcd.leader.latency.current')

    def test_service_checks(self):
        self.run_check(self.config)

        self.assertEqual(len(self.service_checks), 1, self.service_checks)
        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=['url:http://localhost:4001', 'etcd_state:leader'])

    def test_bad_config(self):
        self.assertRaises(Exception,
                          lambda: self.run_check({"instances": [{"url": "http://localhost:4001/test"}]}))

        self.assertEqual(len(self.service_checks), 1, self.service_checks)
        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.CRITICAL,
                                tags=['url:http://localhost:4001/test/v2/stats/self'])

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

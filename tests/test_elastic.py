# stdlib
import socket
import unittest

# 3p
import requests
from nose.plugins.attrib import attr

# project
from tests.common import load_check
from checks import AgentCheck
PORT = 9200
MAX_WAIT = 150


@attr(requires='elasticsearch')
class TestElastic(unittest.TestCase):
    def test_bad_config(self):
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        conf = {
            'instances': [{'url': 'http://losdfsdsdcalhost:%s' % PORT}]
        }
        # Initialize the check from checks.d
        self.check = load_check('elastic', conf, agentConfig)

        self.assertRaises(requests.exceptions.ConnectionError, self.check.check, conf['instances'][0])
        service_checks = self.check.get_service_checks()
        # 2 service checks b/c a connection failed trying to get the version nb first
        self.assertEquals(len(service_checks), 2, service_checks)
        self.assertEquals(service_checks[0]['status'], AgentCheck.CRITICAL, service_checks)
        self.assertEquals(service_checks[1]['status'], AgentCheck.CRITICAL, service_checks)

    def test_check(self):
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto',
            'hostname': 'agent-es-test'
        }

        conf = {
            'instances': [
                {'url': 'http://localhost:%s' % PORT},
                {'url': 'http://localhost:%s' % PORT, 'is_external': True}
            ]
        }

        # Initialize the check from checks.d
        self.check = load_check('elastic', conf, agentConfig)

        self.check.check(conf['instances'][0])
        r = self.check.get_metrics()
        self.check.get_events()

        self.assertTrue(type(r) == type([]))
        self.assertTrue(len(r) > 0)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.get.total"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.search.fetch.total"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "jvm.mem.heap_committed"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "jvm.mem.heap_used"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "jvm.threads.count"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "jvm.threads.peak_count"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.transport.rx_count"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.transport.tx_size"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.transport.server_open"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.thread_pool.snapshot.queue"]), 1, r)
        self.assertEquals(len([t for t in r if t[0] == "elasticsearch.active_shards"]), 1, r)

        # Checks enabled for specific ES versions
        version = self.check._get_es_version()
        if version >= [0,90,10]:
            # ES versions 0.90.10 and above
            pass
        else:
            # ES version 0.90.9 and below
            self.assertEquals(len([t for t in r if t[0] == "jvm.gc.collection_time"]), 1, r)

        # Service checks
        service_checks = self.check.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == self.check.SERVICE_CHECK_CLUSTER_STATUS]), 1, service_checks)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == self.check.SERVICE_CHECK_CONNECT_NAME]), 1, service_checks)
        # Assert that all service checks have the proper tags: host and port
        self.assertEquals(len([sc for sc in service_checks if "host:localhost" in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "port:%s" % PORT in sc['tags']]), service_checks_count, service_checks)

        self.check.cluster_status[conf['instances'][0].get('url')] = "red"
        self.check.check(conf['instances'][0])
        events = self.check.get_events()
        self.check.get_metrics()
        self.assertEquals(len(events),1,events)

        # Check an "external" cluster
        self.check.check(conf['instances'][1])
        r = self.check.get_metrics()
        expected_hostname = socket.gethostname()
        for m in r:
            if m[0] not in self.check.CLUSTER_HEALTH_METRICS:
                self.assertEquals(m[3]['hostname'], expected_hostname)

        # Service metadata
        service_metadata = self.check.get_service_metadata()
        service_metadata_count = len(service_metadata)
        self.assertTrue(service_metadata_count > 0)
        for meta_dict in service_metadata:
            assert meta_dict

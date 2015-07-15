# stdlib
from Queue import Empty
import time

# 3p
from nose.plugins.attrib import attr

# project
from config import AGENT_VERSION
from tests.checks.common import AgentCheckTest
from util import headers as agent_headers


@attr(requires='core_integration')
class ServiceCheckTestCase(AgentCheckTest):

    CHECK_NAME = "http_check"

    def testHTTPHeaders(self):
        agentConfig = {
            'version': AGENT_VERSION,
            'api_key': 'toto'
        }

        config = {
            'init_config': {},
            'instances': [{
                'url': 'https://google.com',
                'name': 'UpService',
                'timeout': 1,
                'headers': {"X-Auth-Token": "SOME-AUTH-TOKEN"}
            }]
        }

        self.load_check(config, agentConfig)
        url, username, password, http_response_status_code, timeout,\
            include_content, headers, response_time, content_match,\
            tags, ssl, ssl_expiration,\
            instance_ca_certs = self.check._load_conf(config['instances'][0])

        self.assertEqual(headers["X-Auth-Token"], "SOME-AUTH-TOKEN", headers)
        expected_headers = agent_headers(agentConfig).get('User-Agent')
        self.assertEqual(expected_headers, headers.get('User-Agent'), headers)


    def testHTTPWarning(self):
        self.CHECK_NAME = "http_check"

        config = {
            'init_config': {},
            'instances': [{
                'url': 'http://127.0.0.1:55555',
                'name': 'DownService',
                'timeout': 1
            },{
                'url': 'https://google.com',
                'name': 'UpService',
                'timeout': 1
            }]
        }


        self.run_check(config, force_reload=True)
        time.sleep(2)
        # This would normally be called during the next run(), it is what
        # flushes the results of the check

        self.check._process_results()
        self.warnings = self.check.get_warnings()

        self.assertEqual(len(self.warnings), 4, self.warnings)
        self.assertWarning("Skipping SSL certificate validation for "
            "https://google.com based on configuration", count=1)
        self.assertWarning("Using events for service checks is deprecated in "
            "favor of monitors and will be removed in future versions of the "
            "Datadog Agent.", count=3)

        self.check.stop()

    def testHTTP(self):
        self.CHECK_NAME = "http_check"

        # No passwords this time
        config = {
            'init_config': {},
            'instances': [{
                'url': 'http://127.0.0.1:55555',
                'name': 'DownService',
                'timeout': 1
            },{
                'url': 'http://google.com',
                'name': 'UpService',
                'timeout': 1
            }]
        }

        self.run_check(config, force_reload=True)
        time.sleep(2)
        self.assertEqual(self.check.pool.get_nworkers(), 2)

        self.check._process_results()

        self.events = self.check.get_events()
        self.service_checks = self.check.get_service_checks()

        self.assertEqual(type(self.events), type([]))
        self.assertEqual(len(self.events), 1, self.events)
        self.assertEqual(self.events[0]['event_object'], 'DownService')

        self.assertEqual(type(self.service_checks), type([]))
        self.assertEqual(len(self.service_checks), 2, self.service_checks) # 1 per instance

        expected_tags = ["instance:DownService", "url:http://127.0.0.1:55555"]
        self.assertServiceCheck("http.can_connect", status=2, tags=expected_tags)

        expected_tags = ["instance:UpService", "url:http://google.com"]
        self.assertServiceCheck("http.can_connect", status=0, tags=expected_tags)

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()
        self.assertEqual(type(events), type([]))
        self.assertEqual(len(events), 0)
        self.assertEqual(type(service_checks), type([]))
        self.assertEqual(len(service_checks), 0)
        # result Q should be empty here
        self.assertRaises(Empty, self.check.resultsq.get_nowait)

        # Cleanup the threads
        self.check.stop()

    def testTCP(self):
        # No passwords this time
        config = {
            'init_config': {
            },
            'instances': [{
                'host': '127.0.0.1',
                'port': 65530,
                'timeout': 1,
                'name': 'DownService'
            },{
                'host': '126.0.0.1',
                'port': 65530,
                'timeout': 1,
                'name': 'DownService2'
            },{
                'host': 'datadoghq.com',
                'port': 80,
                'timeout': 1,
                'name': 'UpService'

            }]
        }


        self.CHECK_NAME = "tcp_check"
        self.run_check(config, force_reload=True)
        time.sleep(2)
        self.assertEqual(self.check.pool.get_nworkers(), 3)
        # This would normally be called during the next run(), it is what
        # flushes the results of the check
        self.check._process_results()

        self.events = self.check.get_events()
        self.service_checks = self.check.get_service_checks()


        self.assertEqual(type(self.events), type([]))
        self.assertEqual(len(self.events), 2, self.events)
        for event in self.events:
            self.assertTrue(event['event_object'][:11] == 'DownService')

        self.assertEqual(type(self.service_checks), type([]))
        self.assertEqual(len(self.service_checks), 3, self.service_checks) # 1 per instance

        expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530"]
        self.assertServiceCheck("tcp.can_connect", status=2, tags=expected_tags)

        expected_tags = ["instance:DownService2", "target_host:126.0.0.1", "port:65530"]
        self.assertServiceCheck("tcp.can_connect", status=2, tags=expected_tags)

        expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80"]
        self.assertServiceCheck("tcp.can_connect", status=0, tags=expected_tags)

        self.check.stop()

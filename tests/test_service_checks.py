from Queue import Empty
import unittest
import time
from tests.common import load_check
import logging
import nose.tools as nt
from config import AGENT_VERSION
from util import headers as agent_headers

class ServiceCheckTestCase(unittest.TestCase):

    def setUp(self):
        self.checks = []

    def init_check(self, config, check_name):
        self.agentConfig = {
            'version': AGENT_VERSION,
            'api_key': 'toto'
        }

        self.check = load_check(check_name, config, self.agentConfig)
        self.checks.append(self.check)

    def testHTTPHeaders(self):
        config = {
            'init_config': {},
            'instances': [{
                'url': 'https://google.com',
                'name': 'UpService',
                'timeout': 1,
                'headers': { "X-Auth-Token": "SOME-AUTH-TOKEN"}
            }]
        }

        self.init_check(config, 'http_check')
        url, username, password, timeout, include_content, headers, response_time, tags, ssl = self.check._load_conf(config['instances'][0])

        self.assertTrue(headers["X-Auth-Token"] == "SOME-AUTH-TOKEN", headers)
        self.assertTrue(headers.get('User-Agent') == agent_headers(self.agentConfig).get('User-Agent'), headers)



    def testHTTPWarning(self):
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
        self.init_check(config, 'http_check')

        self.check.run()
        time.sleep(1)
        # This would normally be called during the next run(), it is what
        # flushes the results of the check
        self.check._process_results()
        warnings = self.check.get_warnings()

        self.assertTrue(len(warnings) == 3, warnings)
        self.assertTrue(len([k for k in warnings if "Skipping SSL certificate validation" in k])==1, warnings)

    def testHTTP(self):
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

        self.init_check(config, 'http_check')

        def verify_service_checks(service_checks):
            for service_check in service_checks:
                if service_check['check'] == 'http_check.DownService':
                    self.assertTrue(service_check['status']==2, service_check)
                elif service_check['check'] == 'http_check.UpService':
                    self.assertTrue(service_check['status']==0, service_check)
                else:
                    raise Exception('Bad check name')


        self.check.run()
        time.sleep(1)
        nt.assert_equals(self.check.pool.get_nworkers(), 2)
        # This would normally be called during the next run(), it is what
        # flushes the results of the check
        self.check._process_results()

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1, events)
        self.assertTrue(events[0]['event_object'] == 'DownService')
        assert service_checks
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) == 2, service_checks) # 1 per instance
        verify_service_checks(service_checks)

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 0)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) == 0)
        # result Q should be empty here
        self.assertRaises(Empty, self.check.resultsq.get_nowait)

        # We change the stored status, so next check should trigger an event
        self.check.notified['UpService'] = "DOWN"


        time.sleep(1)
        self.check.run()
        time.sleep(1)
        self.check.run()

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()

        self.assertTrue(type(events) == type([]), events)
        self.assertTrue(len(events) == 1, events)
        self.assertTrue(events[0]['event_object'] == 'UpService', events)
        self.assertTrue(type(service_checks) == type([]))
        # FIXME: sometimes it's 3 instead of 2
        self.assertTrue(len(service_checks) >= 2, service_checks) # Only 2 because the second run wasn't flushed
        verify_service_checks(service_checks)

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

        self.init_check(config, 'tcp_check')

        def verify_service_checks(service_checks):
            for service_check in service_checks:
                if service_check['check'].startswith('tcp_check.DownService'):
                    self.assertTrue(service_check['status']==2, service_check)
                elif service_check['check'] == 'tcp_check.UpService':
                    self.assertTrue(service_check['status']==0, service_check)
                else:
                    raise Exception('Bad check name %s' % service_check['check'])


        self.check.run()
        time.sleep(2)
        nt.assert_equals(self.check.pool.get_nworkers(), 3)
        # This would normally be called during the next run(), it is what
        # flushes the results of the check
        self.check._process_results()

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 2, events)
        for event in events:
            self.assertTrue(event['event_object'][:11] == 'DownService')
        assert service_checks
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) == 3, service_checks) # 1 per instance
        verify_service_checks(service_checks)

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 0)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(len(service_checks) == 0)
        # result Q should be empty here
        self.assertRaises(Empty, self.check.resultsq.get_nowait)

        # We change the stored status, so next check should trigger an event
        self.check.notified['UpService'] = "DOWN"

        time.sleep(1)
        self.check.run()
        time.sleep(2)
        self.check.run()

        events = self.check.get_events()
        service_checks = self.check.get_service_checks()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1)
        self.assertTrue(events[0]['event_object'] == 'UpService')
        assert service_checks
        self.assertTrue(type(service_checks) == type([]))
        # FIXME: sometimes it's 4 instead of 3
        self.assertTrue(len(service_checks) >= 3, service_checks) # Only 3 because the second run wasn't flushed
        verify_service_checks(service_checks)

    def tearDown(self):
        for check in self.checks:
            check.stop()

if __name__ == "__main__":
    unittest.main()

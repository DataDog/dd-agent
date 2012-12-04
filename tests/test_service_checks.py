import unittest
import time
from tests.common import load_check
import logging
import nose.tools as nt

class ServiceCheckTestCase(unittest.TestCase):

    def setUp(self):
        self.checks = []

    def init_check(self, config, check_name):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check(check_name, config, self.agentConfig)
        self.checks.append(self.check)

    def testHTTP(self):
        # No passwords this time
        config = {
            'init_config': {},
            'instances': [{
                'url': 'http://127.0.0.1:55555',
                'name': 'DownService'
            },{
                'url': 'http://google.com',
                'name': 'UpService',
                'timeout': 1

            }]
        }

        self.init_check(config, 'http_check')

        nt.assert_equals(self.check.pool.get_nworkers(), 2)

        # We launch each instance twice to be sure to get the results
        self.check.run()
        time.sleep(1)
        self.check.run()
        time.sleep(1)

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1, events)
        self.assertTrue(events[0]['event_object'] == 'DownService')

        events = self.check.get_events()
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 0)

        # We change the stored status, so next check should trigger an event
        self.check.statuses['UpService'] = "DOWN"

        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])
        time.sleep(2)
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1)
        self.assertTrue(events[0]['event_object'] == 'UpService')

        self.check.stop_pool()

        time.sleep(2)


    def testTCP(self):
        # No passwords this time
        config = {
            'init_config': {
            },
            'instances': [{
                'host': '127.0.0.1',
                'port': 65530,
                'name': 'DownService'
            },{
                'host': '126.0.0.1',
                'port': 65530,
                'timeout': 1,
                'name': 'DownService2'
            },{
                'host': 'datadoghq.com',
                'port': 80,
                'name': 'UpService'

            }]
        }

        self.init_check(config, 'tcp_check')

        nt.assert_equals(self.check.pool.get_nworkers(), 3)

        # We launch each instance twice to be sure to get the results
        self.check.run()
        time.sleep(2)
        self.check.run()

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 2, events)
        for event in events:
            self.assertTrue(event['event_object'][:11] == 'DownService')

        events = self.check.get_events()
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 0)

        # We change the stored status, so next check should trigger an event
        self.check.statuses['UpService'] = "DOWN"

        self.check.run()
        time.sleep(5)
        self.check.run()

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1)
        self.assertTrue(events[0]['event_object'] == 'UpService')

        self.check.stop_pool()

        time.sleep(2)
    
    def tearDown(self):
        for check in self.checks:
            check.stop_pool()

if __name__ == "__main__":
    unittest.main()

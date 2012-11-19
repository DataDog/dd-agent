import unittest
import time
from tests.common import load_check
import logging
from nose.tools import set_trace

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
            'init_config': {
                'instances_number': 2
            },
            'instances': [{
                'url': 'http://fsdfdsfsdfsdfsdfsdfsdfsdfsdfsd.com/fake',
                'name': 'DownService'
            },{
                'url': 'http://google.com',
                'name': 'UpService',
                'timeout': 1

            }]
        }

        self.init_check(config, 'http_check')

        self.assertTrue(self.check.pool.get_nworkers() == 2, self.check.pool.get_nworkers())

        # We launch each instance twice to be sure to get the results
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])
        time.sleep(2)
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])

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

        self.assertTrue(self.check.pool.get_nworkers() == 6, self.check.pool.get_nworkers())

        # We launch each instance twice to be sure to get the results
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])
        self.check.check(config['instances'][2])
        time.sleep(2)
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])
        self.check.check(config['instances'][2])

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

        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])
        time.sleep(5)
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])

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

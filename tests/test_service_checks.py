import unittest
import time
from tests.common import load_check
import logging
from nose.tools import set_trace

class ServiceCheckTestCase(unittest.TestCase):

    def init_check(self, config):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('services_checks', config, self.agentConfig)
        logging.getLogger().info(self.check.statuses)

    def testHighNumber(self):
        config = {
            'init_config': {
                'nb_threads': 12,
                'notify': 'handle1, handle2'
            }}

        config['instances'] = []


        def add_http_service(name, url):
            config['instances'].append({
                'name': name,
                'type': 'http',
                'url': url,
                'timeout': 1
                })

        def add_tcp_service(name, url, port):
            config['instances'].append({
                'name': name,
                'type': 'tcp',
                'url': url,
                'port': port,
                'timeout': 1,
                'notify': 'handle3'
        })

        work_http_url = "http://datadoghq.com"
        fail_http_url = "http://google.com/sdfsdfsdfsdfsdfsdfsdffsd.html"
        work_tcp_url = "datadoghq.com"
        work_tcp_port = 80
        fail_tcp_url = "127.0.0.2"
        fail_tcp_port = 65530

        for i in range(25):
            add_tcp_service("fail_tcp_{0}".format(i), fail_tcp_url, fail_tcp_port)

        for i in range(25):
            add_http_service("fail_http_{0}".format(i), fail_http_url)

        for i in range(25):
            add_http_service("work_http_{0}".format(i), work_http_url)

        for i in range(25):
            add_tcp_service("work_tcp_{0}".format(i), work_tcp_url, work_tcp_port)


        self.init_check(config)

        for instance in config['instances']:
            self.check.check(instance)

        time.sleep(10)
        self.check.check(config['instances'][0])

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 50, len(events))

        handles={
            '@handle1': 0,
            '@handle2': 0,
            '@handle3': 0,
            }
        for event in events:
            for handle in handles:
                if handle in event['msg_text']:
                    handles[handle] += 1

        for handle in handles:
            self.assertTrue(handles[handle] == 25)

    def testHTTP(self):
        # No passwords this time
        config = {
            'init_config': {
                'nb_workers': 4
            },
            'instances': [{
                'url': 'http://fsdfdsfsdfsdfsdfsdfsdfsdfsdfsd.com/fake',
                'type': 'http',
                'name': 'DownService'
            },{
                'url': 'http://google.com',
                'type': 'http',
                'name': 'UpService',
                'timeout': 1

            }]
        }

        self.init_check(config)

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
        time.sleep(1)
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1)
        self.assertTrue(events[0]['event_object'] == 'UpService')

        # We restart the pool of worker to not get conflicts with the other test
        self.check.restart_pool()


    def testTCP(self):
        # No passwords this time
        config = {
            'init_config': {
                'parallelize': True,
                'nb_workers': 4
            },
            'instances': [{
                'url': '127.0.0.1',
                'port': 65530,
                'type': 'tcp',
                'name': 'DownService'
            },{
                'url': '126.0.0.1',
                'port': 65530,
                'timeout': 1,
                'type': 'tcp',
                'name': 'DownService2'
            },{
                'url': 'datadoghq.com',
                'port': 80,
                'type': 'tcp',
                'name': 'UpService'

            }]
        }

        self.init_check(config)

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
        time.sleep(1)
        self.check.check(config['instances'][0])
        self.check.check(config['instances'][1])

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 1)
        self.assertTrue(events[0]['event_object'] == 'UpService')

        # We restart the pool of worker to not get conflicts with the other test
        self.check.restart_pool()

    def tearDown(self):
        self.check.stop_pool()

if __name__ == "__main__":
    unittest.main()
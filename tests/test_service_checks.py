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

    def testTcpHighNumber(self):
        config = {
            'init_config': {
                'threads_count': 120,
                'notify': ['handle1', 'handle2']
            }}

        config['instances'] = []


        def add_tcp_service(name, url, port):
            config['instances'].append({
                'name': name,
                'host': url,
                'port': port,
                'timeout': 4,
                'notify': ['handle3']
        })

        work_tcp_url = "google.com"
        work_tcp_port = 80
        fail_tcp_url = "127.0.0.2"
        fail_tcp_port = 65530

        for i in range(250):
            add_tcp_service("fail_tcp_{0}".format(i), fail_tcp_url, fail_tcp_port)

        for i in range(250):
            add_tcp_service("work_tcp_{0}".format(i), work_tcp_url, work_tcp_port)


        self.init_check(config, 'tcp_check')

        self.assertTrue(self.check.pool.get_nworkers() == 120)

        for instance in config['instances']:
            self.check.check(instance)

        time.sleep(20)
        self.check.check(config['instances'][0])

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 250, len(events))

        handles={
            '@handle1': 0,
            '@handle2': 0,
            '@handle3': 0,
            }
        for event in events:
            for handle in handles:
                if handle in event['msg_text']:
                    handles[handle] += 1

        self.assertTrue(handles['@handle1'] == 0)
        self.assertTrue(handles['@handle2'] == 0)
        self.assertTrue(handles['@handle3'] == 250)

        self.check.stop_pool()
        
        time.sleep(2)

    def testHttpHighNumber(self):
        config = {
            'init_config': {
                'threads_count': 120,
                'notify': ['handle1', 'handle2']
            }}

        config['instances'] = []


        def add_http_service(name, url):
            config['instances'].append({
                'name': name,
                'type': 'http',
                'url': url,
                'timeout': 10
                })


        work_http_url = "http://google.com"
        fail_http_url = "http://google.com/sdfsdfsdfsdfsdfsdfsdffsd.html"

        for i in range(250):
            add_http_service("fail_http_{0}".format(i), fail_http_url)

        for i in range(250):
            add_http_service("work_http_{0}".format(i), work_http_url)


        self.init_check(config,'http_check')

        self.assertTrue(self.check.pool.get_nworkers() == 120)

        for instance in config['instances']:
            self.check.check(instance)

        time.sleep(20)
        self.check.check(config['instances'][0])

        events = self.check.get_events()

        assert events
        self.assertTrue(type(events) == type([]))
        self.assertTrue(len(events) == 250, len(events))

        handles={
            '@handle1': 0,
            '@handle2': 0,
            }
        for event in events:
            for handle in handles:
                if handle in event['msg_text']:
                    handles[handle] += 1

        self.assertTrue(handles['@handle1'] == 250, handles)
        self.assertTrue(handles['@handle2'] == 250, handles)

        self.check.stop_pool()

        time.sleep(2)

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
import unittest
from checks.jmx_connector import JmxCheck
import logging
import subprocess
import time
import urllib2
from nose.plugins.skip import SkipTest

from tests.common import kill_subprocess, load_check




class JMXTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass
    

    def testTomcatMetrics(self):
        agentConfig = {
            'tomcat_jmx_instance_1': 'localhost:8090:first_instance',
            'tomcat_jmx_instance_2': 'dummyurl:4444:fake_url',
            'version': '0.1',
            'api_key': 'toto'
        }

        config = JmxCheck.parse_agent_config(agentConfig, 'tomcat')
        config['init_config'] = TOMCAT_CONFIG
        metrics_check = load_check('tomcat', config, agentConfig)
        

        timers_first_check = []

        for instance in config['instances']:
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_first_check.append(time.time() - start)
            except Exception,e:
                #print e
                continue

        metrics = metrics_check.get_metrics()
        
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "tomcat.threads.busy"]), 2, metrics)
        self.assertEquals(len([t for t in metrics if t[0] == "tomcat.bytes_sent"]), 0, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t[0]]) > 4, [t for t in metrics if "jvm." in t[0]])

        timers_second_check = []
        for instance in config['instances']:
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_second_check.append(time.time() - start)
            except Exception,e:
                print e
                continue

        metrics = metrics_check.get_metrics()
        self.assertEquals(len([t for t in metrics if t[0] == "tomcat.bytes_sent"]), 2, metrics)
        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)


        metrics_check.kill_jmx_connectors()


TOMCAT_CONFIG = {'conf': [{'include': {'attribute': {'currentThreadCount': {'alias': 'tomcat.threads.count',
        'metric_type': 'gauge'},
        'currentThreadsBusy': {'alias': 'tomcat.threads.busy',
        'metric_type': 'gauge'},
        'maxThreads': {'alias': 'tomcat.threads.max',
        'metric_type': 'gauge'}},
        'type': 'ThreadPool'}},
        {'include': {'attribute': {'bytesReceived': {'alias': 'tomcat.bytes_rcvd',
        'metric_type': 'counter'},
        'bytesSent': {'alias': 'tomcat.bytes_sent',
        'metric_type': 'counter'},
        'errorCount': {'alias': 'tomcat.error_count',
        'metric_type': 'counter'},
        'maxTime': {'alias': 'tomcat.max_time',
        'metric_type': 'gauge'},
        'processingTime': {'alias': 'tomcat.processing_time',
        'metric_type': 'counter'},
        'requestCount': {'alias': 'tomcat.request_count',
        'metric_type': 'counter'}},
        'type': 'GlobalRequestProcessor'}},
        {'include': {'attribute': {'errorCount': {'alias': 'tomcat.servlet.error_count',
        'metric_type': 'counter'},
        'processingTime': {'alias': 'tomcat.servlet.processing_time',
        'metric_type': 'counter'},
        'requestCount': {'alias': 'tomcat.servlet.request_count',
        'metric_type': 'counter'}},
        'j2eeType': 'Servlet'}},
        {'include': {'accessCount': {'alias': 'tomcat.cache.access_count',
        'metric_type': 'counter'},
        'hitsCounts': {'alias': 'tomcat.cache.hits_count',
        'metric_type': 'counter'},
        'type': 'Cache'}},
        {'include': {'jspCount': {'alias': 'tomcat.jsp.count',
        'metric_type': 'counter'},
        'jspReloadCount': {'alias': 'tomcat.jsp.reload_count',
        'metric_type': 'counter'},
        'type': 'JspMonitor'}}]}

if __name__ == "__main__":
    unittest.main()

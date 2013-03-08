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


    def testCustomJMXMetric(self):
        #raise SkipTest()
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }
        config = {}
        
        config['instances'] = [
    {
        "host": "localhost",
        "port": 8090,
        "conf": 
        [
            {"include":{
                "domain" : "Catalina",
                "type": "Connector",
                "port": "8009",
                "attribute": 
                    {"bufferSize": 
                        {"alias": "my.metric.buf",
                         "metric_type": "gauge"}
                    }
                }
            },
            {"include":{
                "domain": "Catalina",
                "type": "ThreadPool",
                "name": "http-8080"
                }
            },
            {"include":{
                "domain": "java.lang"
                }
            }
        ]
    }
]


            


        metrics_check = load_check('jmx', config, agentConfig)

        timers_first_check = []

        for instance in config['instances']:
            start = time.time()
            metrics_check.check(instance)
            timers_first_check.append(time.time() - start)

        metrics = metrics_check.get_metrics()
        


        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "my.metric.buf"]), 1, metrics)
        self.assertTrue(len([t for t in metrics if t[3]['tags'][1] == 'type:ThreadPool' and "jmx.catalina" in t[0]]) > 8, metrics)
        self.assertTrue(len([t for t in metrics if "jmx.java.lang" in t[0]]) > 50, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t[0]]) > 4, metrics)


        timers_second_check = []
        for instance in config['instances']:
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_second_check.append(time.time() - start)
            except Exception,e:
                print e
                continue

        metrics_check.kill_jmx_connectors()


        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)

        
        time.sleep(2)

        


    def testJavaMetric(self):
        agentConfig = {
            'java_jmx_instance_1': 'localhost:8090',
            'java_jmx_instance_2': 'dummyhost:9999:dummy',
            'version': '0.1',
            'api_key': 'toto'
        }

        config = JmxCheck.parse_agent_config(agentConfig, 'java')

        metrics_check = load_check('jmx', config, agentConfig)


        timers_first_check = []

        for instance in config['instances']:
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_first_check.append(time.time() - start)
            except Exception,e:
                print e
                continue

        metrics = metrics_check.get_metrics()
        
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "jvm.thread_count"]), 1, metrics)
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
        metrics_check.kill_jmx_connectors()

        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)

        

if __name__ == "__main__":
    unittest.main()

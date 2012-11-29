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

    def start_solr(self, params, port):
        try:
            params = ["java", "-jar", "-Dcom.sun.management.jmxremote", "-Dcom.sun.management.jmxremote.ssl=false"] + params.split(' ') + ["/tmp/apache-solr-3/example/start.jar"]
            logging.getLogger('dd.testjmx').info("executing %s" % " ".join(params))
            process = subprocess.Popen(params, executable="java", cwd="/tmp/apache-solr-3/example/", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            return process
        except Exception:
            logging.getLogger().exception("Cannot instantiate Solr")
            return None

    def start_tomcat(self, path, port):
        path = "%s/startup.sh" % path
        self.manage_tomcat(path, port)
        time.sleep(3)

    def stop_tomcat(self, path):
        path = "%s/shutdown.sh" % path
        self.manage_tomcat(path)


    def manage_tomcat(self, path, port = None):
        try:
            self.process = None
            self.process = subprocess.Popen(["sh", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print "TOMCAT STARTED"
        except Exception:
            logging.getLogger().exception("Cannot instantiate Tomcat")

    def testCustomJMXMetric(self):
        raise SkipTest()
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


            

        tomcat6 = '/tmp/apache-tomcat-6/bin'
        self.start_tomcat(tomcat6, 8080)

        metrics_check = load_check('jmx', config, agentConfig)

        timers_first_check = []

        for instance in config['instances']:
            #print "processing instance %s" % instance
            start = time.time()
            metrics_check.check(instance)
            timers_first_check.append(time.time() - start)

        metrics = metrics_check.get_metrics()
        


        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "my.metric.buf"]), 1, metrics)
        self.assertEquals(len([t for t in metrics if t[3]['tags'][1] == 'type:ThreadPool']), 10, metrics)
        self.assertTrue(len([t for t in metrics if "jmx.java.lang" in t[0]]) > 50, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t[0]]) > 4, metrics)


        timers_second_check = []
        for instance in config['instances']:
            #print "processing instance %s" % instance
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_second_check.append(time.time() - start)
            except Exception,e:
                print e
                continue

        self.stop_tomcat(tomcat6)

        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)

        metrics_check.kill_jmx_connectors()

        


    def testJavaMetric(self):
        raise SkipTest()
        agentConfig = {
            'java_jmx_instance_1': 'localhost:8090',
            'java_jmx_instance_2': 'dummyhost:9999:dummy',
            'java_jmx_instance_3': 'localhost:2222:second_instance',
            'version': '0.1',
            'api_key': 'toto'
        }

        config = JmxCheck.parse_agent_config(agentConfig, 'java')

        metrics_check = load_check('jmx', config, agentConfig)

        # Starting tomcat
        tomcat6 = '/tmp/apache-tomcat-6/bin'
        self.start_tomcat(tomcat6, 8080)

        # Starting solr
        jmx_prefix = "-Dcom.sun.management.jmxremote"
        first_instance = "%s.port=2222 %s.authenticate=false -Djetty.port=8380" % (jmx_prefix, jmx_prefix)
        first_instance = self.start_solr(first_instance, 8983)

        timers_first_check = []

        for instance in config['instances']:
            #print "processing instance %s" % instance
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
        self.assertEquals(len([t for t in metrics if t[0] == "jvm.thread_count"]), 2, metrics)
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

        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)

        self.stop_tomcat(tomcat6)
        metrics_check.kill_jmx_connectors()
        if first_instance:
            kill_subprocess(first_instance)

    def testTomcatMetrics(self):
        raise SkipTest()
        agentConfig = {
            'tomcat_jmx_instance_1': 'localhost:8090:first_instance',
            'tomcat_jmx_instance_2': 'dummyurl:4444:fake_url',
            'tomcat_jmx_instance_3': 'monitorRole:tomcat@localhost:8091:second_instance_with_auth',
            'version': '0.1',
            'api_key': 'toto'
        }

        config = JmxCheck.parse_agent_config(agentConfig, 'tomcat')
        config['init_config'] = TOMCAT_CONFIG
        metrics_check = load_check('tomcat', config, agentConfig)
        

        tomcat6 = '/tmp/apache-tomcat-6/bin'
        tomcat7 = '/tmp/apache-tomcat-7/bin'
        self.start_tomcat(tomcat6, 8080)
        self.start_tomcat(tomcat7, 7070)

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
        self.assertEquals(len([t for t in metrics if t[0] == "tomcat.threads.busy"]), 4, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t[0]]) > 4, [t for t in metrics if "jvm." in t[0]])

        timers_second_check = []
        for instance in config['instances']:
            #print "processing instance %s" % instance
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_second_check.append(time.time() - start)
            except Exception,e:
                print e
                continue

        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)


        metrics_check.kill_jmx_connectors()

        self.stop_tomcat(tomcat6)
        self.stop_tomcat(tomcat7)

    
    def testSolrMetrics(self):
        raise SkipTest()
        agentConfig = {
            'solr_jmx_instance_1': 'localhost:3000:first_instance',
            'solr_jmx_instance_2': 'dummyurl:4444:fake_url',
            'solr_jmx_instance_3': 'monitorRole:solr@localhost:3001:second_instance_with_auth',
            'version': '0.1',
            'api_key': 'toto'
        }

        jmx_prefix = "-Dcom.sun.management.jmxremote"

        
        first_instance = None
        second_instance = None
       
        first_instance = "%s.port=3000 %s.authenticate=false -Djetty.port=8980" % (jmx_prefix, jmx_prefix)
        second_instance = "%s.port=3001 %s.authenticate=true -Djetty.port=8984 %s.password.file=/tmp/apache-solr-3/example/jmxremote.password %s.access.file=/tmp/apache-solr-3/example/jmxremote.access" % (jmx_prefix, jmx_prefix, jmx_prefix, jmx_prefix)
        
        first_instance = self.start_solr(first_instance, 8983)
        second_instance = self.start_solr(second_instance, 8984)

        config = JmxCheck.parse_agent_config(agentConfig, 'solr')
        config['init_config'] = SOLR_CONFIG

        metrics_check = load_check('solr', config, agentConfig)

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
        self.assertEquals(len([t for t in metrics if t[3].get('device_name') == "solr" and t[0] == "jvm.thread_count"]), 2, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t[0]]) > 4, [t for t in metrics if "jvm." in t[0]])

        timers_second_check = []
        for instance in config['instances']:
            #print "processing instance %s" % instance
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_second_check.append(time.time() - start)
            except Exception,e:
                continue

        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)

        metrics_check.kill_jmx_connectors()
        if first_instance:
            kill_subprocess(first_instance)
        if second_instance:
            kill_subprocess(second_instance)




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

SOLR_CONFIG = {
'conf': 
[{'include': 
{'attribute': 
{'maxDoc': 
{'alias': 'solr.searcher.maxdoc',
'metric_type': 'gauge'},
'numDocs': 
{'alias': 'solr.searcher.numdocs',
'metric_type': 'gauge'},
'warmupTime': 
{'alias': 'solr.searcher.warmup',
'metric_type': 'gauge'}},
'type': 'searcher'}},
{'include': 
{'attribute': 
{'cumulative_evictions': 
{'alias': 'solr.cache.evictions',
'metric_type': 'counter'},
'cumulative_hits': {'alias': 'solr.cache.hits',
'metric_type': 'counter'},
'cumulative_inserts': {'alias': 'solr.cache.inserts',
'metric_type': 'counter'},
'cumulative_lookups': {'alias': 'solr.cache.lookups',
'metric_type': 'counter'}},
'id': 'org.apache.solr.search.FastLRUCache'}},
{'include': {'attribute': {'cumulative_evictions': {'alias': 'solr.cache.evictions',
'metric_type': 'counter'},
'cumulative_hits': {'alias': 'solr.cache.hits',
'metric_type': 'counter'},
'cumulative_inserts': {'alias': 'solr.cache.inserts',
'metric_type': 'counter'},
'cumulative_lookups': {'alias': 'solr.cache.lookups',
'metric_type': 'counter'}},
'id': 'org.apache.solr.search.LRUCache'}},
{'include': {'attribute': {'avgRequestsPerSecond': {'alias': 'solr.search_handler.avg_requests_per_sec',
'metric_type': 'gauge'},
'avgTimePerRequest': {'alias': 'solr.search_handler.avg_time_per_req',
'metric_type': 'gauge'},
'errors': {'alias': 'solr.search_handler.errors',
'metric_type': 'counter'},
'requests': {'alias': 'solr.search_handler.requests',
'metric_type': 'counter'},
'timeouts': {'alias': 'solr.search_handler.timeouts',
'metric_type': 'counter'},
'totalTime': {'alias': 'solr.search_handler.time',
'metric_type': 'counter'}},
'id': 'org.apache.solr.handler.component.SearchHandler'}}]}
if __name__ == "__main__":
    unittest.main()

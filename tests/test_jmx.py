import unittest
from checks.jmx import Tomcat, Solr
import logging
import subprocess
import time
import urllib2

class JMXTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def start_solr(self, params, port):
        try:
            params = ["java", "-jar", "-Dcom.sun.management.jmxremote", "-Dcom.sun.management.jmxremote.ssl=false"] + params.split(' ') + ["/tmp/apache-solr-3.6.1/example/start.jar"]
            logging.getLogger('dd.testjmx').info("executing %s" % " ".join(params))
            process = subprocess.Popen(params, executable="java", cwd="/tmp/apache-solr-3.6.1/example/", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            raise Exception("started")

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

        except Exception:
            logging.getLogger().exception("Cannot instantiate Tomcat")

    
    def testTomcatMetrics(self):
        self.metrics_check = Tomcat(logging.getLogger())
        agentConfig = {
            'tomcat_jmx_instance_1': 'localhost:8090:first_instance',
            'tomcat_jmx_instance_2': 'dummyurl:4444:fake_url',
            'tomcat_jmx_instance_3': 'monitorRole:tomcat@localhost:8091:second_instance_with_auth',
            'version': '0.1',
            'api_key': 'toto'
        }

        tomcat6 = '/tmp/apache-tomcat-6.0.35/bin'
        tomcat7 = '/tmp/apache-tomcat-7.0.29/bin'
        self.start_tomcat(tomcat6, 8080)
        self.start_tomcat(tomcat7, 7070)

        r = self.metrics_check.check(agentConfig)

        self.stop_tomcat(tomcat6)
        self.stop_tomcat(tomcat7)
        self.assertTrue(type(r) == type([]))
        self.assertTrue(len(r) > 0)
        self.assertEquals(len([t for t in r if t[0] == "tomcat.threads.busy"]), 2, r)

    
    def testSolrMetrics(self):
        self.metrics_check = Solr(logging.getLogger())
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
        second_instance = "%s.port=3001 %s.authenticate=true -Djetty.port=8984 %s.password.file=/tmp/apache-solr-3.6.1/example/jmxremote.password %s.access.file=/tmp/apache-solr-3.6.1/example/jmxremote.access" % (jmx_prefix, jmx_prefix, jmx_prefix, jmx_prefix)
        
        first_instance = self.start_solr(first_instance, 8983)
        second_instance = self.start_solr(second_instance, 8984)
        
        
        r = self.metrics_check.check(agentConfig)
        
        if first_instance:
            first_instance.terminate()
        if second_instance:
            second_instance.terminate()
        self.assertTrue(type(r) == type([]))
        self.assertTrue(len(r) > 0)
        self.assertEquals(len([t for t in r if t[3].get('device_name') == "solr" and t[0] == "jvm.thread_count"]), 2, r)

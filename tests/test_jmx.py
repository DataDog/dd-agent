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
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }
        config = {}
        config['instances'] = [
            {
            'host': 'localhost',
            'port': 8090,
            'domains': [
                {
                'name': 'Catalina',
                'beans': [
                    {
                    'name': 'Catalina:type=Connector,port=8009',
                    'attributes': [{
                        'name': 'bufferSize',
                        'type': 'gauge',
                        'alias': 'my.metric.buf'
                        }]
                    },{
                    'name': 'Catalina:type=ThreadPool,name=http-8080',
                    'attributes': 'all'}
                    ]
                },{
                'name': 'java.lang',
                'beans': 'all'}]
            }]

        tomcat6 = '/tmp/apache-tomcat-6/bin'
        self.start_tomcat(tomcat6, 8080)

        metrics_check = load_check('jmx', config, agentConfig)

        for instance in config['instances']:
            print "processing instance %s" % instance
            try:
                metrics_check.check(instance)
            except Exception,e:
                print "Check failed for instance %s" % instance
                continue

        metrics = metrics_check.get_metrics()
        metrics_check.kill_jmx_connectors()

        self.stop_tomcat(tomcat6)
        time.sleep(2)


        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "my.metric.buf"]), 1, metrics)
        self.assertEquals(len([t for t in metrics if t[3]['tags'][1] == 'type:ThreadPool']), 10, metrics)
        self.assertTrue(len([t for t in metrics if "jmx.java.lang" in t[0]]) > 50)






    def testJavaMetric(self):
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

        for instance in config['instances']:
            print "processing instance %s" % instance
            try:
                metrics_check.check(instance)
            except Exception,e:
                print "Check failed for instance %s" % instance
                continue

        metrics = metrics_check.get_metrics()
        metrics_check.kill_jmx_connectors()

        if first_instance:
            kill_subprocess(first_instance)

        self.stop_tomcat(tomcat6)

        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "jvm.thread_count"]), 2, metrics)

    def testTomcatMetrics(self):
        agentConfig = {
            'tomcat_jmx_instance_1': 'localhost:8090:first_instance',
            'tomcat_jmx_instance_2': 'dummyurl:4444:fake_url',
            'tomcat_jmx_instance_3': 'monitorRole:tomcat@localhost:8091:second_instance_with_auth',
            'version': '0.1',
            'api_key': 'toto'
        }

        config = JmxCheck.parse_agent_config(agentConfig, 'tomcat')

        metrics_check = load_check('tomcat', config, agentConfig)
        

        tomcat6 = '/tmp/apache-tomcat-6/bin'
        tomcat7 = '/tmp/apache-tomcat-7/bin'
        self.start_tomcat(tomcat6, 8080)
        self.start_tomcat(tomcat7, 7070)

        for instance in config['instances']:
            print "processing instance %s" % instance
            try:
                metrics_check.check(instance)
            except Exception,e:
                print "Check failed for instance %s" % instance
                continue

        metrics = metrics_check.get_metrics()
        metrics_check.kill_jmx_connectors()

        self.stop_tomcat(tomcat6)
        self.stop_tomcat(tomcat7)
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[0] == "tomcat.threads.busy"]), 4, metrics)

    
    def testSolrMetrics(self):
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

        metrics_check = load_check('solr', config, agentConfig)

        for instance in config['instances']:
            print "processing instance %s" % instance
            try:
                metrics_check.check(instance)
            except Exception,e:
                print "Check failed for instance %s" % instance
                continue
        
        
        metrics = metrics_check.get_metrics()
        metrics_check.kill_jmx_connectors()

        if first_instance:
            kill_subprocess(first_instance)
        if second_instance:
            kill_subprocess(second_instance)

        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 0)
        self.assertEquals(len([t for t in metrics if t[3].get('device_name') == "solr" and t[0] == "jvm.thread_count"]), 2, metrics)

if __name__ == "__main__":
    unittest.main()

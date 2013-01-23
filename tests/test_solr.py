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

    
    def testSolrMetrics(self):
        agentConfig = {
            'solr_jmx_instance_1': 'localhost:8090',
            'solr_jmx_instance_2': 'dummyurl:4444:fake_url',
            'version': '0.1',
            'api_key': 'toto'
        }

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
        self.assertTrue(len(metrics) > 8, metrics)
        self.assertEquals(len([t for t in metrics if t[3].get('device_name') == "solr" and t[0] == "jvm.thread_count"]), 1, metrics)
        self.assertTrue(len([t for t in metrics if "jvm." in t[0]]) > 4, [t for t in metrics if "jvm." in t[0]])
        self.assertTrue(len([t for t in metrics if "solr." in t[0]]) > 4, [t for t in metrics if "solr." in t[0]])

        timers_second_check = []
        for instance in config['instances']:
            try:
                start = time.time()
                metrics_check.check(instance)
                timers_second_check.append(time.time() - start)
            except Exception,e:
                continue

        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 2]), 0, timers_second_check)

        metrics_check.kill_jmx_connectors()



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

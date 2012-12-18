from checks.jmx_connector import JmxCheck, JMXMetric, convert

class SolrMetric(JMXMetric):
    
    @property
    def metric_name(self):
        if hasattr(self, '_metric_name'):
            return self._metric_name
        name = ['solr', self.domain, self.attribute_name]
        return convert(".".join(name))

    @property
    def device(self):
        type_tag = self.tags.get('type')
        if type_tag == "searcher":
            return None
            
        return self.tags.get('type')


class Solr(JmxCheck):

    SOLR_DOMAINS = ['solr']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        domains = Solr.SOLR_DOMAINS + self.init_config.get('domains', [])

        self.get_and_send_jvm_metrics(instance, dump, tags)
        self.create_metrics(instance, self.get_beans(dump, domains, approx=True), SolrMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()

    @staticmethod
    def parse_agent_config(agentConfig):

        return JmxCheck.parse_agent_config(agentConfig, 'solr', INIT_CONFIG)





INIT_CONFIG = {
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
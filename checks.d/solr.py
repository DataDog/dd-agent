from checks.jmx_connector import JmxConnector, JmxCheck, JMXMetric

import logging

lg = logging.getLogger('solr')

class SolrMetric(JMXMetric):

    WHITELIST = {
    'maxDoc' : [{
        'type' : 'searcher',
        'params' : ("solr.searcher.maxdoc", "gauge")}],
    'numDocs' : [{
        'type' : 'searcher',
        'params' : ("solr.searcher.numdocs", "gauge")}],
    'warmupTime' : [{
        'type' : 'searcher',
        'params' : ("solr.searcher.warmup", "gauge")}],

    'cumulative_lookups' : [{
        'id' : 'org.apache.solr.search.FastLRUCache',
        'params' : ("solr.cache.lookups", "counter")},{
        
        'id' : 'org.apache.solr.search.LRUCache',
        'params' : ("solr.cache.lookups", "counter")}],
    
    'cumulative_hits' : [{
        'id' : 'org.apache.solr.search.FastLRUCache',
        'params' : ("solr.cache.hits", "counter")},{
        
        'id' : 'org.apache.solr.search.LRUCache',
        'params' : ("solr.cache.hits", "counter")}],
    
    'cumulative_inserts' : [{
        'id' : 'org.apache.solr.search.FastLRUCache',
        'params' : ("solr.cache.inserts", "counter")},{
        
        'id' : 'org.apache.solr.search.LRUCache',
        'params' : ("solr.cache.inserts", "counter")}],
    
    'cumulative_evictions' : [{
        'id' : 'org.apache.solr.search.FastLRUCache',
        'params' : ("solr.cache.evictions", "counter")},{
        
        'id' : 'org.apache.solr.search.LRUCache',
        'params' : ("solr.cache.evictions", "counter")}],

    'errors' : [{
        'id' : 'org.apache.solr.handler.component.SearchHandler',
        'params' : ("solr.search_handler.errors", "counter")}],
    'requests' : [{
        'id' : 'org.apache.solr.handler.component.SearchHandler',
        'params' : ("solr.search_handler.requests", "counter")}],
    'timeouts' : [{
        'id' : 'org.apache.solr.handler.component.SearchHandler',
        'params' : ("solr.search_handler.timeouts", "counter")}],
    'totalTime' : [{
        'id' : 'org.apache.solr.handler.component.SearchHandler',
        'params' : ("solr.search_handler.time", "counter")}],
    'avgTimePerRequest' : [{
        'id' : 'org.apache.solr.handler.component.SearchHandler',
        'params' : ("solr.search_handler.avg_time_per_req", "gauge")}],
    'avgRequestsPerSecond' : [{
        'id' : 'org.apache.solr.handler.component.SearchHandler',
        'params' : ("solr.search_handler.avg_requests_per_sec", "gauge")}],

    }
 

    def get_params(self):
        if SolrMetric.WHITELIST.has_key(self.attribute_name):
            for dic in SolrMetric.WHITELIST[self.attribute_name]:
                invalid = False
                for key in dic.keys():
                    if key=='params':
                        continue
                    if self.tags.get(key) != dic[key]:
                        invalid = True
                        break
                if not invalid:
                    return dic['params']

        return None


    @property
    def send_metric(self):
        return self.get_params() is not None

    @property
    def metric_name(self):
        return self.get_params()[0]

    @property
    def type(self):
        return self.get_params()[1]


class Solr(JmxCheck):

    SOLR_DOMAINS = ['solr']

    def check(self, instance):
        (host, port, user, password, jmx, instance_name) = self._load_config(instance)
        tags = {}
        if instance_name is not None:
            tags['instance'] = instance_name
        dump = jmx.dump()

        self.get_jvm_metrics(dump, tags)
        self.create_metrics(self.get_beans(dump, Solr.SOLR_DOMAINS, approx=True), SolrMetric, tags=tags)
        self.send_jmx_metrics()
        self.clear_jmx_metrics()




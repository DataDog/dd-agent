#! /usr/bin/python

import urlparse
import urllib2

from checks import Check
from util import json, headers

class ElasticSearch(Check):

    STATS_URL = "/_nodes/stats?all=true&pretty=true"

    METRICS = { 
        "docs.count": "gauge",
        "docs.deleted": "gauge",
        "store.size": ("gauge", "store.size_in_bytes"),
        "indexing.index.total": ("gauge","indexing.index_total"),
        "indexing.index.time": ("gauge","indexing.index_time_in_millis"),
        "indexing.index.current": ("gauge","indexing.index_current"),
        "indexing.delete.total": ("gauge", "indexing.delete_total"),
        "indexing.delete.time": ("gauge", "indexing.delete_time_in_millis"),
        "indexing.delete.current": ("gauge","indexing.delete_current"),
        "get.total": ("gauge","get.total"),
        "get.time": ("gauge","get.time_in_millis"),
        "get.current": ("gauge","get.current"),
        "get.exists.total": ("gauge","get.exists_total"),
        "get.exists.time": ("gauge","get.exists_time_in_millis"),
        "get.missing.total": ("gauge","get.missing_total"),
        "get.missing.time": ("gauge","get.missing_time_in_millis"),
    }


    @classmethod
    def _map_metric(cls,func):
        
        for metric in cls.METRICS:
            desc = cls.METRICS[metric]
            if type(desc) == tuple:
                func(metric,*desc)
            else:
                func(metric,desc,metric)

    def __init__(self, logger):
        Check.__init__(self, logger)

        def generate_metric(name, type, path):
            if type == "counter":
                self.counter(name)
            else:
                self.gauge(name)

        self._map_metric(generate_metric)

    def _get_data(self, agentConfig, url):
        "Hit a given URL and return the parsed json"
        
        req = urllib2.Request(url, None, headers(agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()
        return json.loads(response)

    def _process_metric(self, data, metric, path):

        value = data.get("indices",None)
        for key in path.split('.'):
            if value is not None:
                value = value.get(key,None)

        if value is not None:
            self.save_sample(metric,long(value))

    def _process_data(self, agentConfig, data):

        for node in data['nodes']:
            node_data = data['nodes'][node]

            def process_metric(metric, type, path):
                self._process_metric(node_data, metric, path)

            self._map_metric(process_metric)

    def check(self, config):
        """Extract data from stats URL
http://www.elasticsearch.org/guide/reference/api/admin-cluster-nodes-stats.html
        """

        host = config.get("elasticsearch", None)

        # Check if we are configured properly
        if host is None:
            return False

        # Try to fetch data from the stats URL
        url = urlparse.urljoin(host,self.STATS_URL)

        data = None
        try:
            data = self._get_data(agentConfig, url)
        except:
            self.logger.exception('Unable to get ElasticSearch statistics')
            return False

        self._process_data(agentConfig, data)
        return self.get_metrics()

if __name__ == "__main__":
    import logging
    agentConfig = { 'elasticsearch': 'http://localhost:9200', 
                    'version': '0.1',
                    'apiKey': 'toto' }
    es = ElasticSearch(logging)
    print es.check(agentConfig)
    print es.check(agentConfig)


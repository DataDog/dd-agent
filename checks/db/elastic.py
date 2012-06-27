#! /usr/bin/python

import urlparse
import urllib2
import socket

from checks import Check, gethostname
from util import json, headers

class ElasticSearch(Check):

    STATS_URL = "/_nodes/stats?all=true"

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
        "search.query.total": ("gauge","search.query_total"),
        "search.query.time": ("gauge","search.query_time_in_millis"),
        "search.query.current": ("gauge","search.query_current"),
        "search.fetch.total": ("gauge","search.fetch_total"),
        "search.fetch.time": ("gauge","search.fetch_time_in_millis"),
        "search.fetch.current": ("gauge","search.fetch_current"),
        "cache.field.evictions": ("gauge","cache.field_evictions"),
        "cache.field.size": ("gauge","cache.field_size_in_bytes"),
        "cache.filter.count": ("gauge","cache.filter_count"),
        "cache.filter.evictions": ("gauge","cache.filter_evictions"),
        "cache.filter.size": ("gauge","cache.filter_size_in_bytes"),
        "merges.current": ("gauge","merges.current"),
        "merges.current.docs": ("gauge","merges.current_docs"),
        "merges.current.size": ("gauge","merges.current_size_in_bytes"),
        "merges.total": ("gauge","merges.total"),
        "merges.total.time": ("gauge","merges.total_time_in_millis"),
        "merges.total.docs": ("gauge","merges.total_docs"),
        "merges.total.size": ("gauge","merges.total_size_in_bytes"),
        "refresh.total": ("gauge","refresh.total"),
        "refresh.total.time": ("gauge","refresh.total_time_in_millis"),
        "flush.total": ("gauge","flush.total"),
        "flush.total.time": ("gauge","flush.total_time_in_millis"),
    }

    @classmethod
    def _map_metric(cls,func):
        for metric in cls.METRICS:
            desc = cls.METRICS[metric]
            if type(desc) == tuple:
                func("es." + metric,*desc)
            else:
                func("es." + metric,desc,metric)

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

    def _metric_not_found(self, metric, path):
        self.logger.warning("Metric not found: %s -> %s", path, metric)

    def _process_metric(self, data, metric, path):

        value = data.get("indices",None)
        
        for key in path.split('.'):
            if value is not None:
                value = value.get(key,None)
            else:
                value = None
                break

        if value is not None:
            self.save_sample(metric,long(value))
        else:
            self._metric_not_found(metric, path)

    def _process_data(self, agentConfig, data):

        for node in data['nodes']:
            node_data = data['nodes'][node]

            # ES nodes will use `hostname` regardless of how the agent is configured
            hostnames = (
                gethostname(agentConfig),
                socket.gethostname(),
                socket.getfqdn()
            )
            if node_data['hostname'] in hostnames:
                def process_metric(metric, xtype, path):
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

        self.logger.info("Fetching elastic search data from: %s" % url)

        data = None
        try:
            data = self._get_data(config, url)
        except:
            self.logger.exception('Unable to get ElasticSearch statistics')
            return False

        self._process_data(config, data)

        return self.get_metrics()

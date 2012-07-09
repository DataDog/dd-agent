#! /usr/bin/python

import urlparse
import urllib2
import socket
import subprocess
import sys

from checks import Check, gethostname
from util import json, headers

class NodeNotFound(Exception): pass

class ElasticSearch(Check):

    STATS_URL = "/_cluster/nodes/stats?all=true"
    NODES_URL = "/_cluster/nodes?network=true"

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
                func("elasticsearch." + metric,*desc)
            else:
                func("elasticsearch." + metric,desc,metric)

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

            def process_metric(metric, xtype, path):
                self._process_metric(node_data, metric, path)

            if 'hostname' in node_data:
                # For ES >= 0.19
                hostnames = (
                    gethostname(agentConfig).decode('utf-8'),
                    socket.gethostname().decode('utf-8'),
                    socket.getfqdn().decode('utf-8')
                )
                if node_data['hostname'].decode('utf-8') in hostnames:
                    self._map_metric(process_metric)
            else:
                # ES < 0.19
                # Fetch interface address from ifconfig or ip addr and check
                # against the primary IP from ES
                try:
                    base_url = self._base_es_url(agentConfig['elasticsearch'])
                    url = "%s%s" % (base_url, self.NODES_URL)
                    primary_addr = self._get_primary_addr(agentConfig, url, node)
                except NodeNotFound:
                    # Skip any nodes that aren't found
                    continue
                if self._host_matches_node(primary_addr):
                    self._map_metric(process_metric)

    def _get_primary_addr(self, agentConfig, url, node_name):
        ''' Returns a list of primary interface addresses as seen by ES.
        Used in ES < 0.19
        '''
        req = urllib2.Request(url, None, headers(agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()
        data = json.loads(response)

        if node_name in data['nodes']:
            node = data['nodes'][node_name]
            if 'network' in node:
                return node['network']['primary_interface']['address']

        raise NodeNotFound()

    def _host_matches_node(self, primary_addrs):
        ''' For < 0.19, check if the current host matches the IP given
        in the cluster nodes check `/_cluster/nodes`. Uses `ip addr` on Linux
        and `ifconfig` on Mac
        '''
        if sys.platform == 'darwin':
            ifaces = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE)
        else:
            ifaces = subprocess.Popen(['ip', 'addr'], stdout=subprocess.PIPE)
        grepper = subprocess.Popen(['grep', 'inet'], stdin=ifaces.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        ifaces.stdout.close()
        out, err = grepper.communicate()

        # Capture the list of interface IPs
        ips = []
        for iface in out.split("\n"):
            iface = iface.strip()
            if iface:
                ips.append( iface.split(' ')[1].split('/')[0] )

        # Check the interface addresses against the primary address
        return primary_addrs in ips

    def _base_es_url(self, config_url):
        parsed = urlparse.urlparse(config_url)
        if parsed.path == "":
            return config_url
        return "%s://%s" % (parsed.scheme, parsed.netloc)

    def check(self, config):
        """Extract data from stats URL
http://www.elasticsearch.org/guide/reference/api/admin-cluster-nodes-stats.html
        """

        config_url = config.get("elasticsearch", None)

        # Check if we are configured properly
        if config_url is None:
            return False

        # Try to fetch data from the stats URL
        # If only the hostname was passed, accept that and add our stats_url
        # Else use the full URL as provided
        if urlparse.urlparse(config_url).path == "":
            url = urlparse.urljoin(config_url, self.STATS_URL)
        else:
            url = config_url

        self.logger.info("Fetching elasticsearch data from: %s" % url)

        data = None
        try:
            data = self._get_data(config, url)
        except:
            self.logger.exception('Unable to get elasticsearch statistics')
            return False

        self._process_data(config, data)

        return self.get_metrics()

import urlparse
import urllib2
import socket
import subprocess
import sys
from datetime import datetime
import time

from checks import AgentCheck
from util import json, headers

HEALTH_URL = "/_cluster/health?pretty=true"
STATS_URL = "/_cluster/nodes/stats?all=true"
NODES_URL = "/_cluster/nodes?network=true"


def _get_data(agentConfig, url):
    "Hit a given URL and return the parsed json"
    req = urllib2.Request(url, None, headers(agentConfig))
    request = urllib2.urlopen(req)
    response = request.read()
    return json.loads(response)

class NodeNotFound(Exception): pass



class ElasticSearch(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # Host status needs to persist across all checks
        self.cluster_status = {}


    METRICS = {
        "elasticsearch.docs.count": ("gauge", "indices.docs.count"),
        "elasticsearch.docs.deleted": ("gauge", "indices.docs.deleted"),
        "elasticsearch.store.size": ("gauge", "indices.store.size_in_bytes"),
        "elasticsearch.indexing.index.total": ("gauge", "indices.indexing.index_total"),
        "elasticsearch.indexing.index.time": ("gauge", "indices.indexing.index_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.indexing.index.current": ("gauge", "indices.indexing.index_current"),
        "elasticsearch.indexing.delete.total": ("gauge", "indices.indexing.delete_total"),
        "elasticsearch.indexing.delete.time": ("gauge", "indices.indexing.delete_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.indexing.delete.current": ("gauge", "indices.indexing.delete_current"),
        "elasticsearch.get.total": ("gauge", "indices.get.total"),
        "elasticsearch.get.time": ("gauge", "indices.get.time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.get.current": ("gauge", "indices.get.current"),
        "elasticsearch.get.exists.total": ("gauge", "indices.get.exists_total"),
        "elasticsearch.get.exists.time": ("gauge", "indices.get.exists_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.get.missing.total": ("gauge", "indices.get.missing_total"),
        "elasticsearch.get.missing.time": ("gauge", "indices.get.missing_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.search.query.total": ("gauge", "indices.search.query_total"),
        "elasticsearch.search.query.time": ("gauge", "indices.search.query_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.search.query.current": ("gauge", "indices.search.query_current"),
        "elasticsearch.search.fetch.total": ("gauge", "indices.search.fetch_total"),
        "elasticsearch.search.fetch.time": ("gauge", "indices.search.fetch_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.search.fetch.current": ("gauge", "indices.search.fetch_current"),
        "elasticsearch.cache.field.evictions": ("gauge", "indices.cache.field_evictions"),
        "elasticsearch.cache.field.size": ("gauge", "indices.cache.field_size_in_bytes"),
        "elasticsearch.cache.filter.count": ("gauge", "indices.cache.filter_count"),
        "elasticsearch.cache.filter.evictions": ("gauge", "indices.cache.filter_evictions"),
        "elasticsearch.cache.filter.size": ("gauge", "indices.cache.filter_size_in_bytes"),
        "elasticsearch.merges.current": ("gauge", "indices.merges.current"),
        "elasticsearch.merges.current.docs": ("gauge", "indices.merges.current_docs"),
        "elasticsearch.merges.current.size": ("gauge", "indices.merges.current_size_in_bytes"),
        "elasticsearch.merges.total": ("gauge", "indices.merges.total"),
        "elasticsearch.merges.total.time": ("gauge", "indices.merges.total_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.merges.total.docs": ("gauge", "indices.merges.total_docs"),
        "elasticsearch.merges.total.size": ("gauge", "indices.merges.total_size_in_bytes"),
        "elasticsearch.refresh.total": ("gauge", "indices.refresh.total"),
        "elasticsearch.refresh.total.time": ("gauge", "indices.refresh.total_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.flush.total": ("gauge", "indices.flush.total"),
        "elasticsearch.flush.total.time": ("gauge", "indices.flush.total_time_in_millis", lambda v: float(v)/1000),
        "elasticsearch.process.open_fd": ("gauge", "process.open_file_descriptors"),
        "elasticsearch.transport.rx_count": ("gauge", "transport.rx_count"),
        "elasticsearch.transport.tx_count": ("gauge", "transport.tx_count"),
        "elasticsearch.transport.rx_size": ("gauge", "transport.rx_size_in_bytes"),
        "elasticsearch.transport.tx_size": ("gauge", "transport.tx_size_in_bytes"),
        "elasticsearch.transport.server_open": ("gauge", "transport.server_open"),
        "elasticsearch.thread_pool.bulk.active": ("gauge", "thread_pool.bulk.active"),
        "elasticsearch.thread_pool.bulk.threads": ("gauge", "thread_pool.bulk.threads"),
        "elasticsearch.thread_pool.bulk.queue": ("gauge", "thread_pool.bulk.queue"),
        "elasticsearch.thread_pool.cache.active": ("gauge", "thread_pool.cache.active"),
        "elasticsearch.thread_pool.cache.threads": ("gauge", "thread_pool.cache.threads"),
        "elasticsearch.thread_pool.cache.queue": ("gauge", "thread_pool.cache.queue"),
        "elasticsearch.thread_pool.flush.active": ("gauge", "thread_pool.flush.active"),
        "elasticsearch.thread_pool.flush.threads": ("gauge", "thread_pool.flush.threads"),
        "elasticsearch.thread_pool.flush.queue": ("gauge", "thread_pool.flush.queue"),
        "elasticsearch.thread_pool.generic.active": ("gauge", "thread_pool.generic.active"),
        "elasticsearch.thread_pool.generic.threads": ("gauge", "thread_pool.generic.threads"),
        "elasticsearch.thread_pool.generic.queue": ("gauge", "thread_pool.generic.queue"),
        "elasticsearch.thread_pool.get.active": ("gauge", "thread_pool.get.active"),
        "elasticsearch.thread_pool.get.threads": ("gauge", "thread_pool.get.threads"),
        "elasticsearch.thread_pool.get.queue": ("gauge", "thread_pool.get.queue"),
        "elasticsearch.thread_pool.index.active": ("gauge", "thread_pool.index.active"),
        "elasticsearch.thread_pool.index.threads": ("gauge", "thread_pool.index.threads"),
        "elasticsearch.thread_pool.index.queue": ("gauge", "thread_pool.index.queue"),
        "elasticsearch.thread_pool.management.active": ("gauge", "thread_pool.management.active"),
        "elasticsearch.thread_pool.management.threads": ("gauge", "thread_pool.management.threads"),
        "elasticsearch.thread_pool.management.queue": ("gauge", "thread_pool.management.queue"),
        "elasticsearch.thread_pool.merge.active": ("gauge", "thread_pool.merge.active"),
        "elasticsearch.thread_pool.merge.threads": ("gauge", "thread_pool.merge.threads"),
        "elasticsearch.thread_pool.merge.queue": ("gauge", "thread_pool.merge.queue"),
        "elasticsearch.thread_pool.percolate.active": ("gauge", "thread_pool.percolate.active"),
        "elasticsearch.thread_pool.percolate.threads": ("gauge", "thread_pool.percolate.threads"),
        "elasticsearch.thread_pool.percolate.queue": ("gauge", "thread_pool.percolate.queue"),
        "elasticsearch.thread_pool.refresh.active": ("gauge", "thread_pool.refresh.active"),
        "elasticsearch.thread_pool.refresh.threads": ("gauge", "thread_pool.refresh.threads"),
        "elasticsearch.thread_pool.refresh.queue": ("gauge", "thread_pool.refresh.queue"),
        "elasticsearch.thread_pool.search.active": ("gauge", "thread_pool.search.active"),
        "elasticsearch.thread_pool.search.threads": ("gauge", "thread_pool.search.threads"),
        "elasticsearch.thread_pool.search.queue": ("gauge", "thread_pool.search.queue"),
        "elasticsearch.thread_pool.snapshot.active": ("gauge", "thread_pool.snapshot.active"),
        "elasticsearch.thread_pool.snapshot.threads": ("gauge", "thread_pool.snapshot.threads"),
        "elasticsearch.thread_pool.snapshot.queue": ("gauge", "thread_pool.snapshot.queue"),
        "elasticsearch.http.current_open": ("gauge", "http.current_open"),
        "elasticsearch.http.total_opened": ("gauge", "http.total_opened"),
        "jvm.gc.collection_count": ("gauge", "jvm.gc.collection_count"),
        "jvm.gc.collection_time": ("gauge", "jvm.gc.collection_time_in_millis", lambda v: float(v)/1000),
        "jvm.gc.concurrent_mark_sweep.count": ("gauge", "jvm.gc.collectors.ConcurrentMarkSweep.collection_count"),
        "jvm.gc.concurrent_mark_sweep.collection_time": ("gauge", "jvm.gc.collectors.ConcurrentMarkSweep.collection_time_in_millis", lambda v: float(v)/1000),
        "jvm.gc.par_new.count": ("gauge", "jvm.gc.collectors.ParNew.collection_count"),
        "jvm.gc.par_new.collection_time": ("gauge", "jvm.gc.collectors.ParNew.collection_time_in_millis", lambda v: float(v)/1000),
        "jvm.gc.copy.count": ("gauge", "jvm.gc.collectors.Copy.collection_count"),
        "jvm.gc.copy.collection_time": ("gauge", "jvm.gc.collectors.Copy.collection_time_in_millis", lambda v: float(v)/1000),
        "jvm.mem.heap_committed": ("gauge", "jvm.mem.heap_committed_in_bytes"),
        "jvm.mem.heap_used": ("gauge", "jvm.mem.heap_used_in_bytes"),
        "jvm.mem.non_heap_committed": ("gauge", "jvm.mem.non_heap_committed_in_bytes"),
        "jvm.mem.non_heap_used": ("gauge", "jvm.mem.non_heap_used_in_bytes"),
        "jvm.threads.count": ("gauge", "jvm.threads.count"),
        "jvm.threads.peak_count": ("gauge", "jvm.threads.peak_count"),
        "elasticsearch.number_of_nodes": ("gauge", "number_of_nodes"),
        "elasticsearch.number_of_data_nodes": ("gauge", "number_of_data_nodes"),
        "elasticsearch.active_primary_shards": ("gauge", "active_primary_shards"),
        "elasticsearch.active_shards": ("gauge", "active_shards"),
        "elasticsearch.relocating_shards": ("gauge", "relocating_shards"),
        "elasticsearch.initializing_shards": ("gauge", "initializing_shards"),
        "elasticsearch.unassigned_shards": ("gauge", "unassigned_shards"),
    }


    def check(self, instance):
        config_url = instance.get('url')
        if config_url is None:
            raise Exception("An url must be specified")

        tags = ['url:%s' % config_url]
        self.load_url(config_url, instance, tags=tags, url_suffix=STATS_URL)

    def check_status(self, data, url):
        if self.cluster_status.get(url, None) is None:
            self.cluster_status[url] = data['status']
            if data['status'] in ["yellow", "red"]:
                event = self._create_event(data['status'])
                self.event(event)
        if data['status'] != self.cluster_status.get(url):
            self.cluster_status[url] = data['status']
            event = self._create_event(data['status'])
            self.event(event)


    def load_url(self, config_url, instance, tags=None, url_suffix=STATS_URL):

        # Try to fetch data from the stats URL
        # If only the hostname was passed, accept that and add our stats_url
        # Else use the full URL as provided
        if urlparse.urlparse(config_url).path == "":
            url = urlparse.urljoin(config_url, url_suffix)
        else:
            url = config_url

        self.log.debug("Fetching elasticsearch data from: %s" % url)

        try:
            data = _get_data(self.agentConfig, url)

            if url_suffix==STATS_URL:
                self._process_data(data, tags=tags, instance=instance)
                self.load_url(config_url, instance, tags=tags, url_suffix=HEALTH_URL)

            else:
                self.check_status(data, config_url)
                self._process_health_data(data, tags=tags)

        except Exception, e:
            self.log.exception('Unable to get elasticsearch statistics %s' % str(e))
            raise

    def _base_es_url(self, config_url):
        parsed = urlparse.urlparse(config_url)
        if parsed.path == "":
            return config_url
        return "%s://%s" % (parsed.scheme, parsed.netloc)

    def _process_data(self, data, tags=None, instance=None):
        for node in data['nodes']:
            node_data = data['nodes'][node]

            def process_metric(metric, xtype, path, xform=None):
                # closure over node_data
                self._process_metric(node_data, metric, path, xform, tags=tags)

            if 'hostname' in node_data:
                # For ES >= 0.19
                hostnames = (
                    self.hostname.decode('utf-8'),
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
                    base_url = self._base_es_url(instance['url'])
                    url = "%s%s" % (base_url, NODES_URL)
                    primary_addr = self._get_primary_addr(self.agentConfig, url, node)
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
            if 'network' in node\
            and 'primary_interface' in node['network']\
            and 'address' in node['network']['primary_interface']:
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

    def _process_metric(self, data, metric, path, xform=None, tags=None):
        """data: dictionary containing all the stats
        metric: datadog metric
        path: corresponding path in data, flattened, e.g. thread_pool.bulk.queue
        xfom: a lambda to apply to the numerical value
        """
        value = data
        # Traverse the nested dictionaries
        for key in path.split('.'):
            if value is not None:
                value = value.get(key, None)
            else:
                break

        if value is not None:
            if xform: value = xform(value)
            if self.METRICS[metric][0] == "gauge":

                self.gauge(metric, value, tags=tags)
            else:
                self.rate(metric, value, tags=tags)
        else:
            self._metric_not_found(metric, path)

    def _process_health_data(self, data, tags=None):
            def process_metric(metric, xtype, path, xform=None):
                # closure over node_data
                self._process_metric(data, metric, path, xform, tags=tags)
            self._map_metric(process_metric)

    @classmethod
    def _map_metric(cls, func):
        """Apply a function to all known metrics.
        Used to create and sample metrics.
        """
        for metric in cls.METRICS:
            # metric description
            desc = cls.METRICS[metric]
            func(metric, *desc)

    def _metric_not_found(self, metric, path):
        self.log.debug("Metric not found: %s -> %s", path, metric)

    def _create_event(self, status):
        hostname = self.hostname.decode('utf-8')
        if status == "red":
            alert_type = "error"
            msg_title = "%s is %s" % (hostname, status)

        elif status == "yellow":
            alert_type = "warning"
            msg_title = "%s is %s" % (hostname, status)

        else:
            # then it should be green
            alert_type = "success"
            msg_title = "%s recovered as %s" % (hostname, status)

        msg = "ElasticSearch: %s just reported as %s" % (hostname, status)

        return { 'timestamp': int(time.mktime(datetime.utcnow().timetuple())),
                 'event_type': 'elasticsearch',
                 'host': hostname,
                 'msg_text':msg,
                 'msg_title': msg_title,
                 "alert_type": alert_type,
                 "source_type_name": "elasticsearch",
                 "event_object": hostname
            }

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('elasticsearch'):
            return False

        return {
            'instances': [{
                'url': agentConfig.get('elasticsearch'),
            }]
        }


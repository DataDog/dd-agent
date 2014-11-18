# stdlib
import socket
import subprocess
import sys
import time
import urlparse
import urllib2
import time

# project
from checks import AgentCheck
from checks.utils import add_basic_auth
from util import headers

# 3rd party
import simplejson as json

class NodeNotFound(Exception): pass

class ElasticSearch(AgentCheck):
    SERVICE_CHECK_CONNECT_NAME = 'elasticsearch.can_connect'
    SERVICE_CHECK_CLUSTER_STATUS = 'elasticsearch.cluster_health'
    
    METRICS = { # Metrics that are common to all Elasticsearch versions
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
        "elasticsearch.cluster_status": ("gauge", "status", lambda v: {"red":0,"yellow":1,"green":2}.get(v, -1)),
    }

    SOURCE_TYPE_NAME = 'elasticsearch'

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

        # Host status needs to persist across all checks
        self.cluster_status = {}

    def check(self, instance):
        config_url = instance.get('url')
        added_tags = instance.get('tags')
        is_external = instance.get('is_external', False)
        if config_url is None:
            raise Exception("An url must be specified")

        # Load basic authentication configuration, if available.
        username, password = instance.get('username'), instance.get('password')
        if username and password:
            auth = (username, password)
        else:
            auth = None

        # Support URLs that have a path in them from the config, for
        # backwards-compatibility.
        parsed = urlparse.urlparse(config_url)
        if parsed[2] != "":
            config_url = "%s://%s" % (parsed[0], parsed[1])
        port = parsed.port
        host = parsed.hostname
        service_check_tags = [
            'host:%s' % host,
            'port:%s' % port
        ]

        # Tag by URL so we can differentiate the metrics from multiple instances
        tags = ['url:%s' % config_url]
        if added_tags is not None:
            for tag in added_tags:
                tags.append(tag)

        # Check ES version for this instance and define parameters (URLs and metrics) accordingly
        version = self._get_es_version(config_url, auth)
        self._define_params(version)

        # Load stats data.
        url = urlparse.urljoin(config_url, self.STATS_URL)
        stats_data = self._get_data(url, auth, send_service_check=True, service_check_tags=service_check_tags)
        self._process_stats_data(config_url, stats_data, auth, tags=tags,
                                 is_external=is_external)

        # Load the health data.
        url = urlparse.urljoin(config_url, self.HEALTH_URL)
        health_data = self._get_data(url, auth, send_service_check=True, service_check_tags=service_check_tags)
        self._process_health_data(config_url, health_data, tags=tags, service_check_tags=service_check_tags)
        self.service_check(self.SERVICE_CHECK_CONNECT_NAME, AgentCheck.OK, tags=service_check_tags)

    def _get_es_version(self, config_url, auth=None):
        """ Get the running version of Elastic Search.
        """
        try:
            data = self._get_data(config_url, auth)
            version = map(int, data['version']['number'].split('.')[0:3])
        except Exception, e:
            self.warning("Error while trying to get Elasticsearch version from %s %s" % (config_url, str(e)))
            version = [0, 0, 0]

        self.log.debug("Elasticsearch version is %s" % version)
        return version

    def _define_params(self, version):
        """ Define the set of URLs and METRICS to use depending on the
            running ES version.
        """
        if version >= [0,90,10]:
            # ES versions 0.90.10 and above
            self.HEALTH_URL = "/_cluster/health?pretty=true"
            self.STATS_URL = "/_nodes/stats?all=true"
            self.NODES_URL = "/_nodes?network=true"

            additional_metrics = {
                "jvm.gc.collectors.young.count": ("gauge", "jvm.gc.collectors.young.collection_count"),
                "jvm.gc.collectors.young.collection_time": ("gauge", "jvm.gc.collectors.young.collection_time_in_millis", lambda v: float(v)/1000),
                "jvm.gc.collectors.old.count": ("gauge", "jvm.gc.collectors.old.collection_count"),
                "jvm.gc.collectors.old.collection_time": ("gauge", "jvm.gc.collectors.old.collection_time_in_millis", lambda v: float(v)/1000)
            }
        else:
            self.HEALTH_URL = "/_cluster/health?pretty=true"
            self.STATS_URL = "/_cluster/nodes/stats?all=true"
            self.NODES_URL = "/_cluster/nodes?network=true"

            additional_metrics = {
                "jvm.gc.concurrent_mark_sweep.count": ("gauge", "jvm.gc.collectors.ConcurrentMarkSweep.collection_count"),
                "jvm.gc.concurrent_mark_sweep.collection_time": ("gauge", "jvm.gc.collectors.ConcurrentMarkSweep.collection_time_in_millis", lambda v: float(v)/1000),
                "jvm.gc.par_new.count": ("gauge", "jvm.gc.collectors.ParNew.collection_count"),
                "jvm.gc.par_new.collection_time": ("gauge", "jvm.gc.collectors.ParNew.collection_time_in_millis", lambda v: float(v)/1000),
                "jvm.gc.collection_count": ("gauge", "jvm.gc.collection_count"),
                "jvm.gc.collection_time": ("gauge", "jvm.gc.collection_time_in_millis", lambda v: float(v)/1000),
            }

        self.METRICS.update(additional_metrics)

        if version >= [0,90,5]:
            # ES versions 0.90.5 and above
            additional_metrics = {
                "elasticsearch.search.fetch.open_contexts": ("gauge", "indices.search.open_contexts"),
                "elasticsearch.cache.filter.evictions": ("gauge", "indices.filter_cache.evictions"),
                "elasticsearch.cache.filter.size": ("gauge", "indices.filter_cache.memory_size_in_bytes"),
                "elasticsearch.id_cache.size": ("gauge","indices.id_cache.memory_size_in_bytes"),
                "elasticsearch.fielddata.size": ("gauge","indices.fielddata.memory_size_in_bytes"),
                "elasticsearch.fielddata.evictions": ("gauge","indices.fielddata.evictions"),
            }
        else:
            # ES version 0.90.4 and below
            additional_metrics = {
                "elasticsearch.cache.field.evictions": ("gauge", "indices.cache.field_evictions"),
                "elasticsearch.cache.field.size": ("gauge", "indices.cache.field_size_in_bytes"),
                "elasticsearch.cache.filter.count": ("gauge", "indices.cache.filter_count"),
                "elasticsearch.cache.filter.evictions": ("gauge", "indices.cache.filter_evictions"),
                "elasticsearch.cache.filter.size": ("gauge", "indices.cache.filter_size_in_bytes"),
            }

        self.METRICS.update(additional_metrics)

    def _get_data(self, url, auth=None, send_service_check=False, service_check_tags=None):
        """ Hit a given URL and return the parsed json
            `auth` is a tuple of (username, password) or None
        """
        req = urllib2.Request(url, None, headers(self.agentConfig))
        if auth:
            add_basic_auth(req, *auth)
        try:
            request = urllib2.urlopen(req)
        except urllib2.URLError as e:
            if send_service_check:
                self.service_check(self.SERVICE_CHECK_CONNECT_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=e.reason)
            raise
        except Exception as e:
            if send_service_check:
                self.service_check(self.SERVICE_CHECK_CONNECT_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=str(e))
            raise

        response = request.read()
        return json.loads(response)

    def _process_stats_data(self, config_url, data, auth, tags=None, is_external=False):
        for node_name in data['nodes']:
            node_data = data['nodes'][node_name]
            # On newer version of ES it's "host" not "hostname"
            node_hostname = node_data.get('hostname', node_data.get('host', None))
            should_process = is_external or self.should_process_node(config_url,
                                                node_name, node_hostname, auth)
            if should_process:
                for metric in self.METRICS:
                    desc = self.METRICS[metric]
                    self._process_metric(node_data, metric, *desc, tags=tags)

    def should_process_node(self, config_url, node_name, node_hostname, auth):
        """ The node stats API will return stats for every node so we
            want to filter out nodes that we don't care about.
        """
        if node_hostname is not None:
            # For ES >= 0.19
            hostnames = (
                self.hostname.decode('utf-8'),
                socket.gethostname().decode('utf-8'),
                socket.getfqdn().decode('utf-8')
            )
            if node_hostname.decode('utf-8') in hostnames:
                return True
        else:
            # ES < 0.19
            # Fetch interface address from ifconfig or ip addr and check
            # against the primary IP from ES
            try:
                nodes_url = urlparse.urljoin(config_url, self.NODES_URL)
                primary_addr = self._get_primary_addr(nodes_url, node_name, auth)
            except NodeNotFound:
                # Skip any nodes that aren't found
                return False
            if self._host_matches_node(primary_addr):
                return True

    def _get_primary_addr(self, url, node_name, auth):
        """ Returns a list of primary interface addresses as seen by ES.
            Used in ES < 0.19
        """
        req = urllib2.Request(url, None, headers(self.agentConfig))
        # Load basic authentication configuration, if available.
        if auth:
            add_basic_auth(req, *auth)
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
        """ For < 0.19, check if the current host matches the IP given in the
            cluster nodes check `/_cluster/nodes`. Uses `ip addr` on Linux and
            `ifconfig` on Mac
        """
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

    def _process_metric(self, data, metric, xtype, path, xform=None, tags=None):
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
            if xtype == "gauge":
                self.gauge(metric, value, tags=tags)
            else:
                self.rate(metric, value, tags=tags)
        else:
            self._metric_not_found(metric, path)

    def _process_health_data(self, config_url, data, tags=None, service_check_tags=None):
        if self.cluster_status.get(config_url, None) is None:
            self.cluster_status[config_url] = data['status']
            if data['status'] in ["yellow", "red"]:
                event = self._create_event(data['status'])
                self.event(event)

        if data['status'] != self.cluster_status.get(config_url):
            self.cluster_status[config_url] = data['status']
            event = self._create_event(data['status'])
            self.event(event)

        for metric in self.METRICS:
            # metric description
            desc = self.METRICS[metric]
            self._process_metric(data, metric, *desc, tags=tags)

        # Process the service check
        cluster_status = data['status']
        if cluster_status == 'green':
            status = AgentCheck.OK
            tag = "OK"
        elif cluster_status == 'yellow':
            status = AgentCheck.WARNING
            tag = "WARN"
        else:
            status = AgentCheck.CRITICAL
            tag = "ALERT"
        
        msg = "{0} on cluster \"{1}\" | active_shards={2} | initializing_shards={3} | relocating_shards={4} | unassigned_shards={5} | timed_out={6}" \
                    .format(tag, data["cluster_name"],
                                 data["active_shards"],
                                 data["initializing_shards"],
                                 data["relocating_shards"],
                                 data["unassigned_shards"],
                                 data["timed_out"])

        self.service_check(self.SERVICE_CHECK_CLUSTER_STATUS, status, message=msg, tags=service_check_tags)


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

        return { 'timestamp': int(time.time()),
                 'event_type': 'elasticsearch',
                 'host': hostname,
                 'msg_text':msg,
                 'msg_title': msg_title,
                 "alert_type": alert_type,
                 "source_type_name": "elasticsearch",
                 "event_object": hostname
            }



# stdlib
import re
import time
import json
# 3p
from subprocess import check_output, call

# project
from checks import AgentCheck
from urlparse import urlsplit

DEFAULT_TIMEOUT = 30
GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate


class Aerospike(AgentCheck):
    """
    Aerospike agent check.
    """
    # Source
    SOURCE_TYPE_NAME = 'aerospike'

    # Service check
    SERVICE_CHECK_NAME = 'aerospike.can_connect'

    # Metrics
    """
    Core metrics collected by default.
    """
    SERVICE_METRICS = {
        "cluster_size": GAUGE,
        "client_connections": GAUGE,
        "heartbeat_received_foreign": GAUGE,
        "index-used-bytes-memory": GAUGE,
        "objects": GAUGE,
        "stat_write_reqs": RATE,
        "stat_write_success": RATE,
        "total-bytes-disk": RATE,
        "total-bytes-memory": RATE,
        "used-bytes-disk": GAUGE,
        "used-bytes-memory": GAUGE,
        "partition_object_count": GAUGE,
        "query_fail": GAUGE,
        "stat_delete_success": RATE,
        "stat_read_reqs": RATE,
        "stat_write_reqs": RATE,
        "stat_read_success": RATE,
        "stat_write_success": RATE,
        "transactions": GAUGE,
        "uptime": GAUGE,
        "write_master": RATE,
        "write_prole": RATE,
        "available-bin-names": GAUGE,
        "record_refs": GAUGE,
        "memory-size": GAUGE
    }

    FREQUENCYCAP_METRICS = {
        "n_objects": GAUGE,
        "available-bin-names" : RATE,
        "memory-size": GAUGE,
        "filesize": GAUGE,
        "max-ttl": GAUGE,
        "total-bytes-disk": RATE,
        "total-bytes-memory": RATE,
        "objects": GAUGE,
        "used-bytes-disk": RATE,
        "used-bytes-memory": RATE,
        "writecache": GAUGE,
    }

    HOLDOFF_METRICS = {
        "n_objects": GAUGE,
        "available-bin-names" : RATE,
        "memory-size": GAUGE,
        "default-ttl": GAUGE,
        "filesize": GAUGE,
        "max-ttl": GAUGE,
        "total-bytes-disk": RATE,
        "total-bytes-memory": RATE,
        "objects": GAUGE,
        "used-bytes-disk": RATE,
        "used-bytes-memory": RATE,
        "writecache": GAUGE,
    }

    SEGMENT_METRICS = {
        "n_objects": GAUGE,
        "available-bin-names" : RATE,
        "memory-size": GAUGE,
        "default-ttl": GAUGE,
        "filesize": GAUGE,
        "max-ttl": GAUGE,
        "total-bytes-disk": RATE,
        "total-bytes-memory": RATE,
        "objects": GAUGE,
        "expired-objects": GAUGE,
        "used-bytes-disk": RATE,
        "used-bytes-memory": RATE,
        "migrate-record-receives": RATE,
        "migrate-records-transmitted": RATE,
        "writecache": GAUGE,
    }

    SESSION_METRICS = {
        "n_objects": GAUGE,
        "available-bin-names" : RATE,
        "memory-size": GAUGE,
        "default-ttl": GAUGE,
        "filesize": GAUGE,
        "max-ttl": GAUGE,
        "total-bytes-disk": RATE,
        "total-bytes-memory": RATE,
        "objects": GAUGE,
        "expired-objects": GAUGE,
        "used-bytes-disk": RATE,
        "used-bytes-memory": RATE,
        "migrate-record-receives": RATE,
        "migrate-records-transmitted": RATE,
        "writecache": GAUGE,
    }

    """
    Metrics collected by default.
    """
    DEFAULT_METRICS = {
        'service': SERVICE_METRICS,
        'session': SESSION_METRICS,
        'frequencycap': FREQUENCYCAP_METRICS

    }
    ADDITIONAL_METRICS = {
        'holdoff': HOLDOFF_METRICS,
        'segment': SEGMENT_METRICS,
    }
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Members' last replica set states
        self._last_state_by_server = {}

        # List of metrics to collect per instance
        self.metrics_to_collect_by_instance = {}

    def _build_metric_list_to_collect(self, additional_metrics):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Create Metrics Listx
        for default_metric_key in self.DEFAULT_METRICS.iterkeys():
            default_metrics = self.DEFAULT_METRICS[default_metric_key]
            for metric in default_metrics.iterkeys():
                metrics_to_collect["%s.%s" % (default_metric_key, metric)] = default_metrics[metric]

        for option in additional_metrics:
            additional_metrics = self.ADDITIONAL_METRICS.get(option)
            if not additional_metrics:
                if option in self.DEFAULT_METRICS:
                    self.log.warning(
                        u"`%s` option is deprecated."
                        u" The corresponding metrics are collected by default.", option
                    )
                else:
                    self.log.warning(
                        u"Failed to extend the list of metrics to collect:"
                        u" unrecognized `%s` option", option
                    )
                continue

            self.log.debug(
                u"Adding `%s` corresponding metrics to the list"
                u" of metrics to collect.", option
            )
            for metric in additional_metrics.iterkeys():
                metrics_to_collect["%s.%s" % (option, metric)] = additional_metrics[metric]

        return metrics_to_collect

    def _get_metrics_to_collect(self, instance_key, additional_metrics):
        """
        Return and cache the list of metrics to collect.
        """
        if instance_key not in self.metrics_to_collect_by_instance:
            self.metrics_to_collect_by_instance[instance_key] = \
                self._build_metric_list_to_collect(additional_metrics)
        return self.metrics_to_collect_by_instance[instance_key]

    def _resolve_metric(self, original_metric_name, metrics_to_collect, prefix=""):
        """
        Return the submit method and the metric name to use.
        The metric name is defined as follow:
        * If available, the normalized metric name alias
        * (Or) the normalized original metric name
        """

        submit_method = metrics_to_collect[original_metric_name][0] \
            if isinstance(metrics_to_collect[original_metric_name], tuple) \
            else metrics_to_collect[original_metric_name]

        metric_name = metrics_to_collect[original_metric_name][1] \
            if isinstance(metrics_to_collect[original_metric_name], tuple) \
            else original_metric_name

        return submit_method, self._normalize(metric_name, submit_method, prefix)

    def _normalize(self, metric_name, submit_method, prefix):
        """
        Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "aerospike." if not prefix else "aerospike.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == RATE else ""

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.normalize(metric_name.lower()),
            metric_prefix=metric_prefix, metric_suffix=metric_suffix
        )

    def parse_ouput(self, output, hostname):
        """
        Added Parse output to parse metrics And create dictionary
        {
            'hostname':
            {
                'component.metric_name' : 'metric_value'
            }
        }
        :param output:
        :param hostname:
        :return:
        """
        node_info = {}
        node_names = {}
        output_lines = output.splitlines()
        metric_type = ''
        for line in output_lines:
            if "~~~" in line:
                metric_type = line.strip('~').split(' ')[0].lower()
                continue
            line_info = line.split(" : ")
            if line_info and len(line_info) > 1:
                if line_info[0].strip() == 'NODE':
                    # add node info dict
                    host_list = line_info[1].split()
                    for i in range(0, len(host_list)):
                        node_name = host_list[i].strip()
                        node_name = node_name.split(":")[0]
                        # set host name as key in node name to send only this metrics for the server
                        if hostname in node_name and hostname != node_name:
                            node_name = hostname
                        if node_name not in node_info:
                            node_names[i] = node_name
                            node_info[node_name] = {}
                elif node_info:
                    metric_name = line_info[0].strip()
                    metric_list = line_info[1].split()
                    for i in range(0, len(metric_list)):
                        metric_key = '%s.%s' % (metric_type, metric_name)
                        if len(metric_list) > i and len(node_names) > i:
                            node_info[node_names[i]][metric_key] = metric_list[i].strip()
        return node_info


    def check(self, instance):
        """
        Check and Send Metrics
        """

        if 'host' not in instance:
            raise Exception("Missing 'host' in aerospike config")

        host = str(instance['host']).strip()
        # Added this to deal with localhost configuration.
        if host == 'localhost' or host == '127.0.0.1':
            # get actual host name if its localhost.
            host = check_output('sudo hostname', shell=True)
            host = host.strip()

        additional_metrics = instance.get('additional_metrics', [])

        tags = instance.get('tags', [])
        tags.append('host:%s' % host)

        metrics_to_collect = self._get_metrics_to_collect(
            host,
            additional_metrics
        )

        # de-dupe tags to avoid a memory leak
        tags = list(set(tags))

        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT)) * 1000
        metrics_stats = {}
        try:
            output = check_output("sudo /opt/aerospike/bin/asadm -h localhost -e 'show statistics'", shell=True)
            metrics_stats = self.parse_ouput(output, host)
        except Exception:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=tags)
            raise

        for metric_name in metrics_to_collect:
            if metrics_stats:
                if metric_name in metrics_stats[host]:
                    try:
                        if value.is_digit():
                            value = int(metrics_stats[host][metric_name])
                        else:
                            value = metrics_stats[host][metric_name]
                    except:
                        value = metrics_stats[host][metric_name]

                    # Submit the metric
                    submit_method, metric_name_alias = self._resolve_metric(metric_name, metrics_to_collect, "")
                    submit_method(self, metric_name_alias, value, tags=tags)

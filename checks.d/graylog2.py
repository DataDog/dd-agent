"""
Datadog agent check for graylog server 2.0:
  https://www.graylog.org/
  https://github.com/Graylog2/graylog2-server

  This agent check will use graylog's REST API to fetch metrics about the server and
  report them to Datadog.

  For a list of available metrics you can use the following API endpoint:
    http://127.0.0.1:12900/cluster/<node-id>/metrics/names
  Or use the `Cluster/Metrics` endpoints from the REST API Browser at:
    http://127.0.0.1:12900/api-browser

Note:
  This agent check will modify the original graylog2 metric names to be more human friendly,
  all metrics will be prefixed with "graylog2", it will also replace some of the existing metric
  name prefixes (e.g. org.graylog2. -> graylog2., org.apache. -> graylog2.apache.)
  as well as making them Datadog friendly (IndexerSetupService -> indexer_setup_service)

Recommended:
  Graylog2 has ALOT of available metrics once resolved (thousands of them)
  You can use the `prefix_whitelist` and `prefix_blacklist` options below to limit which
  metrics are included or excluded. For each original metric name, this agent will check
  if any of the defined prefixes matches for that metric, which will then include or
  exclude that metric depending on which list the prefix is defined in
"""
# standard library
import urlparse

# third party
import requests

# project
from checks import AgentCheck
from util import headers

CLUSTER_URI = '/cluster'
METRIC_NAMESPACE_URI_TEMPLATE = '/cluster/%s/metrics/namespace/%s'

class Graylog2(AgentCheck):
    # Metric namespaces to fetch metrics for
    # DEV: We do this instead of fetching full list of metric names,
    #   then fetching each metric individually (or then determining namespaces from that)
    METRIC_NAMESPACES = [
        'cluster-eventbus.',
        'jvm.',
        'org.apache.',
        'org.graylog2.',
    ]

    # Mapping of namespace prefixes to their appropriate metric prefix
    # e.g 'org.graylog2.throughput.input' -> 'throughput.input'
    # DEV: A global `graylog2` prefix is added to all metrics
    METRIC_PREFIXES = {
        'cluster-eventbus.': 'cluster-eventbus.',
        'jvm.': 'jvm.',
        'org.apache.': 'apache.',
        'org.graylog2.': '',
    }

    # Prefix to add to every metric
    METRIC_PREFIX = 'graylog2'

    # Mapping of node data to a tag name
    # DEV: This is a whitelist of which data we want to become tags
    # DEV: Basically just ensuring we start with `node` to make it easier
    NODE_TAGS = {
        'cluster_id': 'node_cluster_id',
        'codename': 'node_codename',
        'facility': 'node_facility',
        'hostname': 'node_hostname',
        'node_id': 'node_id',
        'version': 'graylog_version',
    }

    def check(self, instance):
        # Fetch config data
        transport_uri = instance.get('transport_uri', 'http://127.0.0.1:12900')
        username = instance.get('username')
        password = instance.get('password')
        auth = (username, password)
        prefix_whitelist = instance.get('prefix_whitelist', [])
        prefix_blacklist = instance.get('prefix_blacklist', [])

        # Fetch the list of nodes in this cluster
        # `nodes = {<node_id>: dict(<node_data>)}
        nodes = self._get_nodes(transport_uri, auth=auth)

        # For each node in the cluster, fetch and emit metrics
        for node_id, node_data in nodes.iteritems():
            self.log.debug('Fetching metrics for node_id: %s' % (node_id, ))
            metrics = self._get_node_metrics(node_id, transport_uri, auth, prefix_whitelist, prefix_blacklist)
            self._emit_metrics(node_data, metrics)

    def _get_nodes(self, transport_uri, auth):
        """Helper to fetch the list of nodes in this cluster"""
        req_uri = urlparse.urljoin(transport_uri, CLUSTER_URI)
        req = requests.get(req_uri, auth=auth, headers=headers(self.agentConfig))
        req.raise_for_status()

        # {
        #   "<node_id>": {
        #     "facility": "graylog-server",
        #     "node_id": "<node_id>",
        #     ...
        #   }
        # }
        return req.json()

    def _get_node_metrics(self, node_id, transport_uri, auth, prefix_whitelist, prefix_blacklist):
        """Helper to fetch all metrics for a given node in the cluster"""
        all_metrics = []
        for metric_namespace in self.METRIC_NAMESPACES:
            self.log.debug('Fetching node %s metrics for namespace %s' % (node_id, metric_namespace))
            metrics_uri = METRIC_NAMESPACE_URI_TEMPLATE % (node_id, metric_namespace)
            req_uri = urlparse.urljoin(transport_uri, metrics_uri)
            req = requests.get(req_uri, auth=auth, headers=headers(self.agentConfig))
            req.raise_for_status()

            # {
            #   "total": <count>,
            #   "metrics": [
            #     {
            #       "full_name": "<metric_name>",
            #       "metric": {
            #         "<metric_key>": <value>
            #       },
            #       "name": "<short_name>",
            #       "type": "<metric_type>"
            #     }
            #   ]
            # }
            data = req.json()
            namespace_metrics = []
            for metric_data in data.get('metrics', []):
                # Check against our whitelist
                if prefix_whitelist:
                    # Skip any metrics that are not in our whitelist
                    match = False
                    for prefix in prefix_whitelist:
                        if metric_data['full_name'].startswith(prefix):
                            match = True
                            break
                    if not match:
                        self.log.debug('Metric %s not found in prefix whitelist, skipping' % (metric_data['full_name'], ))
                        continue

                # Check against our blacklist
                if prefix_blacklist:
                    # Skip any metrics that are in our blacklist
                    match = False
                    for prefix in prefix_blacklist:
                        if metric_data['full_name'].startswith(prefix):
                            self.log.debug('Metric %s matches blacklist prefix %s, skipping' % (metric_data['full_name'], prefix))
                            match = True
                            break
                    if match:
                        continue

                # Adjust the prefix of the metrics
                # e.g. 'org.graylog2.throughput.input' -> 'throughput.input'
                full_name = metric_data['full_name']
                if full_name.startswith(metric_namespace):
                    new_prefix = self.METRIC_PREFIXES[metric_namespace]
                    full_name = new_prefix + full_name[len(metric_namespace):]
                    self.log.debug('Changed metric name from %s to %s' % (metric_data['full_name'], full_name))
                metric_data['full_name'] = full_name

                namespace_metrics.append(metric_data)

            # Save our metrics for the results
            all_metrics += namespace_metrics

        return all_metrics

    def _emit_metrics(self, node_data, metrics):
        """Helper to emit the fetched metrics for for a given node in the cluster"""
        # Generate list of tags to use for the metrics
        node_tags = []
        for key, tag_name in self.NODE_TAGS.iteritems():
            if key in node_data:
                node_tags.append('%s:%s' % (tag_name, node_data[key]))
        self.log.debug('Using node tags of %s' % (node_tags, ))

        # Process and emit the metrics
        for metric_data in metrics:
            # Resolve/collect all metrics before emitting
            resolved_metrics = {}
            for metric_name, metric_value in metric_data['metric'].iteritems():
                # Metric values could be a single value or a dict of values
                # If we have a dict, then we have two levels of values (see "rate" and "time" examples above)
                #
                # metric_data = {
                #   "full_name": "full.metric.name",
                #   "metric_name": {
                #     "count": 5,
                #     "time": {
                #       "min": 0.
                #       "max": 5,
                #       "99th_percentile": 4,
                #       ...
                #     },
                #     "rate": {
                #       "total": 0,
                #       "mean": 3,
                #       "one_minute": 2,
                #       ...
                #     }
                #   }
                # }
                metric_name = '%s.%s' % (metric_data['full_name'], metric_name)
                if isinstance(metric_value, dict):
                    for sub_name, sub_value in metric_value.iteritems():
                        # Skip any `duration_unit`, `rate_unit`, etc values
                        if sub_name.endswith('_unit'):
                            continue
                        # e.g. `graylog2.rest.system.inputs.create.time.min`
                        sub_metric_name = '%s.%s' % (metric_name, sub_name)
                        resolved_metrics[sub_metric_name] = sub_value
                else:
                    resolved_metrics[metric_name] = metric_value

            # Emit the collected metrics
            # DEV: We are always going to use a `gauge` since these metrics are snapshots
            for metric_name, value in resolved_metrics.iteritems():
                normalized_metric_name = self.normalize(metric_name, prefix=self.METRIC_PREFIX, fix_case=True)
                self.log.debug('Emitting metric %s: %s' % (normalized_metric_name, value))
                self.gauge(normalized_metric_name, value, tags=node_tags)

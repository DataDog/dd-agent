import urllib2
from util import json, headers

from checks import AgentCheck

class Couchbase(AgentCheck):
    """Extracts stats from Couchbase via its REST API
    http://docs.couchbase.com/couchbase-manual-2.0/#using-the-rest-api
    """
    def _create_metric(self, data, tags=None):
        storage_totals = data.get('stats', {})['storageTotals']
        for key, storage_type in storage_totals.items():
            for metric, val in storage_type.items():
                if val is not None:
                    metric_name = '.'.join(['couchbase', key, metric])
                    self.gauge(metric_name, val, tags=tags)
#                    self.log.debug('found metric %s with value %s' % (metric_name, val))

        for bucket_name, bucket_stats in data.get('buckets', {}).items():
            for name, val in bucket_stats.items():
                if val is not None:
                    metric_name = '.'.join(['couchbase', 'by_bucket', name])
                    metric_tags = list(tags)
                    metric_tags.append('bucket:%s' % bucket_name)
                    self.gauge(metric_name, val[0], tags=metric_tags, device_name=bucket_name)
#                    self.log.debug('found metric %s with value %s' % (metric_name, val[0]))

        for node_name, node_stats in data.get('nodes', {}).items():
            for name, val in node_stats['interestingStats'].items():
                if val is not None:
                    metric_name = '.'.join(['couchbase', 'by_node', name])
                    metric_tags = list(tags)
                    metric_tags.append('node:%s' % node_name)
                    self.gauge(metric_name, val, tags=metric_tags, device_name=node_name)
#                    self.log.debug('found metric %s with value %s' % (metric_name, val))


    def _get_stats(self, url):
        "Hit a given URL and return the parsed json"
        self.log.debug('Fetching Couchbase stats at url: %s' % url)
        req = urllib2.Request(url, None, headers(self.agentConfig))

        # Do the request, log any errors
        request = urllib2.urlopen(req)
        response = request.read()
        return json.loads(response)

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            return False
        data = self.get_data(server)
        self._create_metric(data, tags=['instance:%s' % server])

    def get_data(self, server):
        # The dictionary to be returned.
        couchbase = {'stats': None,
                'buckets': {},
                'nodes': {}
                }

        # First, get overall stats and a list of nodes.
        endpoint = '/pools/nodes'

        url = '%s%s' % (server, endpoint)
        overall_stats = self._get_stats(url)

        # No overall stats? bail out now
        if overall_stats is None:
            return False
        else:
            couchbase['stats'] = overall_stats

        nodes = overall_stats['nodes']

        # Next, get all the nodes
        if nodes is not None:
            for node in nodes:
                couchbase['nodes'][node['hostname']] = node

        # Next, get all buckets .
        endpoint = overall_stats['buckets']['uri']

        url = '%s%s' % (server, endpoint)
        buckets = self._get_stats(url)

        if buckets is not None:
            for bucket in buckets:
                bucket_name = bucket['name']

                # We have to manually build the URI for the stats bucket, as this is not auto discoverable
                url = '%s/pools/nodes/buckets/%s/stats' % (server, bucket_name)
                bucket_stats = self._get_stats(url)
                bucket_samples = bucket_stats['op']['samples']
                if bucket_samples is not None:
                    couchbase['buckets'][bucket['name']] = bucket_samples

        return couchbase

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('couchbase_server'):
            return False


        return {
            'instances': [{
                'server': agentConfig.get('couchbase_server'),
                'user': agentConfig.get('couchbase_user'),
                'pass': agentConfig.get('couchbase_pass'),
            }]
        }

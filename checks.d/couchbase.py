# stdlib
import re
import sys

# project
from util import headers
from checks import AgentCheck

# 3rd party
import simplejson as json
import requests

#Constants
COUCHBASE_STATS_PATH = '/pools/default'
DEFAULT_TIMEOUT = 10
class Couchbase(AgentCheck):
    """Extracts stats from Couchbase via its REST API
    http://docs.couchbase.com/couchbase-manual-2.0/#using-the-rest-api
    """
    SERVICE_CHECK_NAME = 'couchbase.can_connect'

    def _create_metrics(self, data, tags=None):
        storage_totals = data['stats']['storageTotals']
        for key, storage_type in storage_totals.items():
            for metric_name, val in storage_type.items():
                if val is not None:
                    metric_name = '.'.join(['couchbase', key, self.camel_case_to_joined_lower(metric_name)])
                    self.gauge(metric_name, val, tags=tags)

        for bucket_name, bucket_stats in data['buckets'].items():
            for metric_name, val in bucket_stats.items():
                if val is not None:
                    metric_name = '.'.join(['couchbase', 'by_bucket', self.camel_case_to_joined_lower(metric_name)])
                    metric_tags = list(tags)
                    metric_tags.append('bucket:%s' % bucket_name)
                    self.gauge(metric_name, val[0], tags=metric_tags, device_name=bucket_name)

        for node_name, node_stats in data['nodes'].items():
            for metric_name, val in node_stats['interestingStats'].items():
                if val is not None:
                    metric_name = '.'.join(['couchbase', 'by_node', self.camel_case_to_joined_lower(metric_name)])
                    metric_tags = list(tags)
                    metric_tags.append('node:%s' % node_name)
                    self.gauge(metric_name, val, tags=metric_tags, device_name=node_name)


    def _get_stats(self, url, instance):
        """ Hit a given URL and return the parsed json. """
        self.log.debug('Fetching Couchbase stats at url: %s' % url)

        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT))

        auth = None
        if 'user' in instance and 'password' in instance:
            auth = (instance['user'], instance['password'])

        r = requests.get(url, auth=auth, headers=headers(self.agentConfig),
            timeout=timeout)
        r.raise_for_status()
        return r.json()

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("The server must be specified")
        tags = instance.get('tags', [])
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))
        tags.append('instance:%s' % server)
        data = self.get_data(server, instance)
        self._create_metrics(data, tags=list(set(tags)))

    def get_data(self, server, instance):
        # The dictionary to be returned.
        couchbase = {'stats': None,
                'buckets': {},
                'nodes': {}
                }

        # build couchbase stats entry point
        url = '%s%s' % (server, COUCHBASE_STATS_PATH)

        # Fetch initial stats and capture a service check based on response.
        service_check_tags = ['instance:%s' % server]
        try:
            overall_stats = self._get_stats(url, instance)
            # No overall stats? bail out now
            if overall_stats is None:
                raise Exception("No data returned from couchbase endpoint: %s" % url)
        except requests.exceptions.HTTPError as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=str(e.message))
            raise
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=str(e))
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

        couchbase['stats'] = overall_stats

        nodes = overall_stats['nodes']

        # Next, get all the nodes
        if nodes is not None:
            for node in nodes:
                couchbase['nodes'][node['hostname']] = node

        # Next, get all buckets .
        endpoint = overall_stats['buckets']['uri']

        url = '%s%s' % (server, endpoint)
        buckets = self._get_stats(url, instance)

        if buckets is not None:
            for bucket in buckets:
                bucket_name = bucket['name']

                # Fetch URI for the stats bucket
                endpoint = bucket['stats']['uri']
                url = '%s%s' % (server, endpoint)

                try:
                    bucket_stats = self._get_stats(url, instance)
                except requests.exceptions.HTTPError:
                    url_backup = '%s/pools/nodes/buckets/%s/stats' % (server, bucket_name)
                    bucket_stats = self._get_stats(url_backup, instance)

                bucket_samples = bucket_stats['op']['samples']
                if bucket_samples is not None:
                    couchbase['buckets'][bucket['name']] = bucket_samples

        return couchbase

    # Takes a camelCased variable and returns a joined_lower equivalent.
    # Returns input if non-camelCase variable is detected.
    def camel_case_to_joined_lower(self, variable):
        # replace non-word with _
        converted_variable = re.sub('\W+', '_', variable)

        # insert _ in front of capital letters and lowercase the string
        converted_variable = re.sub('([A-Z])', '_\g<1>', converted_variable).lower()

        # remove duplicate _
        converted_variable = re.sub('_+', '_', converted_variable)

        # handle special case of starting/ending underscores
        converted_variable = re.sub('^_|_$', '', converted_variable)

        return converted_variable


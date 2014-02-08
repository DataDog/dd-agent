import urllib2
from util import json, headers

from checks import AgentCheck

class CouchDb(AgentCheck):
    """Extracts stats from CouchDB via its REST API
    http://wiki.apache.org/couchdb/Runtime_Statistics
    """
    def _create_metric(self, data, tags=None):
        overall_stats = data.get('stats', {})
        for key, stats in overall_stats.items():
            for metric, val in stats.items():
                if val['current'] is not None:
                    metric_name = '.'.join(['couchdb', key, metric])
                    self.gauge(metric_name, val['current'], tags=tags)
        
        for db_name, db_stats in data.get('databases', {}).items():
            for name, val in db_stats.items():
                if name in ['doc_count', 'disk_size'] and val is not None:
                    metric_name = '.'.join(['couchdb', 'by_db', name])
                    metric_tags = list(tags)
                    metric_tags.append('db:%s' % db_name)
                    self.gauge(metric_name, val, tags=metric_tags, device_name=db_name)

        
    def _get_stats(self, url):
        "Hit a given URL and return the parsed json"
        self.log.debug('Fetching Couchdb stats at url: %s' % url)
        req = urllib2.Request(url, None, headers(self.agentConfig))

        # Do the request, log any errors
        request = urllib2.urlopen(req)
        response = request.read()
        return json.loads(response)

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("A server must be specified")
        data = self.get_data(server)
        self._create_metric(data, tags=['instance:%s' % server])

    def get_data(self, server):
        # The dictionary to be returned.
        couchdb = {'stats': None, 'databases': {}}

        # First, get overall statistics.
        endpoint = '/_stats/'

        url = '%s%s' % (server, endpoint)
        overall_stats = self._get_stats(url)

        # No overall stats? bail out now
        if overall_stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        couchdb['stats'] = overall_stats

        # Next, get all database names.
        endpoint = '/_all_dbs/'

        url = '%s%s' % (server, endpoint)
        databases = self._get_stats(url)

        if databases is not None:
            for dbName in databases:
                endpoint = '/%s/' % dbName

                url = '%s%s' % (server, endpoint)
                db_stats = self._get_stats(url)
                if db_stats is not None:
                    couchdb['databases'][dbName] = db_stats

        return couchdb

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('couchdb_server'):
            return False

        
        return {
            'instances': [{
                'server': agentConfig.get('couchdb_server'),
            }]
        }
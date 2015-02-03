# stdlib
import urllib2

# project
from util import headers
from checks.utils import add_basic_auth
from checks import AgentCheck

# 3rd party
import simplejson as json

class CouchDb(AgentCheck):
    """Extracts stats from CouchDB via its REST API
    http://wiki.apache.org/couchdb/Runtime_Statistics
    """

    SOURCE_TYPE_NAME = 'couchdb'
    SERVICE_CHECK_NAME = 'couchdb.can_connect'

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


    def _get_stats(self, url, instance):
        "Hit a given URL and return the parsed json"
        self.log.debug('Fetching Couchdb stats at url: %s' % url)
        req = urllib2.Request(url, None, headers(self.agentConfig))

        if 'user' in instance and 'password' in instance:
            add_basic_auth(req, instance['user'], instance['password'])

        # Do the request, log any errors
        request = urllib2.urlopen(req)
        response = request.read()
        return json.loads(response)

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("A server must be specified")
        data = self.get_data(server, instance)
        self._create_metric(data, tags=['instance:%s' % server])

    def get_data(self, server, instance):
        # The dictionary to be returned.
        couchdb = {'stats': None, 'databases': {}}

        # First, get overall statistics.
        endpoint = '/_stats/'

        url = '%s%s' % (server, endpoint)

        # Fetch initial stats and capture a service check based on response.
        service_check_tags = ['instance:%s' % server]
        try:
            overall_stats = self._get_stats(url, instance)
        except urllib2.URLError as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=str(e.reason))
            raise
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                tags=service_check_tags, message=str(e))
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                tags=service_check_tags,
                message='Connection to %s was successful' % url)

        # No overall stats? bail out now
        if overall_stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        couchdb['stats'] = overall_stats

        # Next, get all database names.
        endpoint = '/_all_dbs/'

        url = '%s%s' % (server, endpoint)
        databases = self._get_stats(url, instance)

        if databases is not None:
            for dbName in databases:
                endpoint = '/%s/' % dbName

                url = '%s%s' % (server, endpoint)

                db_stats = self._get_stats(url, instance)
                if db_stats is not None:
                    couchdb['databases'][dbName] = db_stats

        return couchdb

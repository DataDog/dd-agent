import httplib
import re
import traceback
import urllib2
from util import json, headers

class CouchDb(Check):
    """Extracts stats from CouchDB via its REST API"""
    def _get_stats(self, logger, agentConfig, url):
        "Hit a given URL and return the parsed json"
        try:
            req = urllib2.Request(url, None, headers(agentConfig))

            # Do the request, log any errors
            request = urllib2.urlopen(req)
            response = request.read()

            return json.loads(response)

        except:
            logger.exception('Unable to get CouchDB statistics')
            return None

    def check(self, logger, agentConfig):
        if ('CouchDBServer' not in agentConfig or agentConfig['CouchDBServer'] == ''):
            return False

        logger.debug('getCouchDBStatus: config set to %s' % agentConfig['CouchDBServer'])

        # The dictionary to be returned.
        couchdb = {'stats': None, 'databases': {}}

        # First, get overall statistics.
        endpoint = '/_stats/'

        url = '%s%s' % (agentConfig['CouchDBServer'], endpoint)
        overall_stats = self._get_stats(logger, agentConfig, url)

        # No overall stats? bail out now
        if overall_stats is None:
            return False
        else:
            couchdb['stats'] = overall_stats

        # Next, get all database names.
        endpoint = '/_all_dbs/'

        url = '%s%s' % (agentConfig['CouchDBServer'], endpoint)
        databases = self._get_stats(logger, agentConfig, url)

        if databases is not None:
            for dbName in databases:
                endpoint = '/%s/' % dbName

                url = '%s%s' % (agentConfig['CouchDBServer'], endpoint)
                db_stats = self._get_stats(logger, agentConfig, url)
                if db_stats is not None:
                    couchdb['databases'][dbName] = db_stats

        return couchdb

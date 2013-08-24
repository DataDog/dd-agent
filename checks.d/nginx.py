import re
import time
import urllib2
import base64

from util import headers
from checks import AgentCheck

class Nginx(AgentCheck):
    """Tracks basic nginx metrics via the status module
    * number of connections
    * number of requets per second

    Requires nginx to have the status option compiled.
    See http://wiki.nginx.org/HttpStubStatusModule for more details

    $ curl http://localhost:81/nginx_status/
    Active connections: 8
    server accepts handled requests
     1156958 1156958 4491319
    Reading: 0 Writing: 2 Waiting: 6

    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.assumed_url = {}

    def check(self, instance):
        if 'nginx_status_url' not in instance:
            raise Exception('nginx instance missing "nginx_status_url" value.')

        url = self.assumed_url.get(instance['nginx_status_url'], instance['nginx_status_url'])

        tags = instance.get('tags', [])

        req = urllib2.Request(url, None,
            headers(self.agentConfig))
        if 'nginx_status_user' in instance and 'nginx_status_password' in instance:
            auth_str = '%s:%s' % (instance['nginx_status_user'], instance['nginx_status_password'])
            encoded_auth_str = base64.encodestring(auth_str)
            req.add_header("Authorization", "Basic %s" % encoded_auth_str)
        request = urllib2.urlopen(req)
        response = request.read()

        metric_count = 0

        # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
        # Connections
        parsed = re.search(r'Active connections:\s+(\d+)', response)
        if parsed:
            metric_count += 1
            connections = int(parsed.group(1))
            self.gauge("nginx.net.connections", connections, tags=tags)
        
        # Requests per second
        parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
        if parsed:
            metric_count += 1
            requests = int(parsed.group(3))
            self.rate("nginx.net.request_per_s", requests, tags=tags)
        
        # Connection states, reading, writing or waiting for clients
        parsed = re.search(r'Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)', response)
        if parsed:
            metric_count += 1
            reading, writing, waiting = map(int, parsed.groups())
            self.gauge("nginx.net.reading", reading, tags=tags)
            self.gauge("nginx.net.writing", writing, tags=tags)
            self.gauge("nginx.net.waiting", waiting, tags=tags)

        if metric_count == 0:
            if self.assumed_url.get(instance['nginx_status_url'], None) is None and url[-5:] != '?auto':
                self.assumed_url[instance['nginx_status_url']]= '%s?auto' % url
                self.warning("Assuming url was not correct. Trying to add ?auto suffix to the url")
                self.check(instance)
            else:
                raise Exception("No metrics were fetched for this instance. Make sure that %s is the proper url." % instance['nginx_status_url'])

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('nginx_status_url'):
            return False

        return {
            'instances': [{'nginx_status_url': agentConfig.get('nginx_status_url')}]
        }
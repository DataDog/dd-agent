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
    def check(self, instance):
        if 'nginx_status_url' not in instance:
            raise Exception('NginX instance missing "nginx_status_url" value.')
        tags = instance.get('tags', [])

        response = self._get_data(instance)
        self._get_metrics(response, tags)

    def _get_data(self, instance):
        url = instance.get('nginx_status_url')
        req = urllib2.Request(url, None, headers(self.agentConfig))
        if 'user' in instance and 'password' in instance:
            auth_str = '%s:%s' % (instance['user'], instance['password'])
            encoded_auth_str = base64.encodestring(auth_str)
            req.add_header("Authorization", "Basic %s" % encoded_auth_str)

        request = urllib2.urlopen(req)
        return request.read()


    def _get_metrics(self, response, tags):
        # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
        # Connections
        parsed = re.search(r'Active connections:\s+(\d+)', response)
        if parsed:
            connections = int(parsed.group(1))
            self.gauge("nginx.net.connections", connections, tags=tags)

        # Requests per second
        parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', response)
        if parsed:
            conn = int(parsed.group(1))
            requests = int(parsed.group(3))
            self.rate("nginx.net.conn_opened_per_s", conn, tags=tags)
            self.rate("nginx.net.request_per_s", requests, tags=tags)

        # Connection states, reading, writing or waiting for clients
        parsed = re.search(r'Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)', response)
        if parsed:
            reading, writing, waiting = map(int, parsed.groups())
            self.gauge("nginx.net.reading", reading, tags=tags)
            self.gauge("nginx.net.writing", writing, tags=tags)
            self.gauge("nginx.net.waiting", waiting, tags=tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        instances = []

        # Try loading from the very old format
        nginx_url = agentConfig.get("nginx_status_url", None)
        if nginx_url is not None:
            instances.append({
                'nginx_status_url': nginx_url
            })

        # Try the older multi-instance style
        # nginx_status_url_1: http://www.example.com/nginx_status:first_tag
        # nginx_status_url_2: http://www.example2.com/nginx_status:8080:second_tag
        # nginx_status_url_2: http://www.example3.com/nginx_status:third_tag
        def load_conf(index=1):
            instance = agentConfig.get("nginx_status_url_%s" % index, None)
            if instance is not None:
                instance = instance.split(":")
                instances.append({
                    'nginx_status_url': ":".join(instance[:-1]),
                    'tags': ['instance:%s' % instance[-1]]
                })
                load_conf(index+1)

        load_conf()

        if not instances:
            return False

        return {
            'instances': instances
        }

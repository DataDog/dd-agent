import re
import urllib2
import urlparse

from util import headers, json
from checks import AgentCheck
from checks.utils import add_basic_auth

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

        response, content_type = self._get_data(instance)
        if content_type == 'application/json':
            metrics = self.parse_json(response, tags)
        else:
            metrics = self.parse_text(response, tags)

        funcs = {
            'gauge': self.gauge,
            'rate': self.rate
        }
        for row in metrics:
            try:
                name, value, tags, metric_type = row
                func = funcs[metric_type]
                func(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s' % repr(row))

    def _get_data(self, instance):
        url = instance.get('nginx_status_url')
        req = urllib2.Request(url, None, headers(self.agentConfig))
        if 'user' in instance and 'password' in instance:
            add_basic_auth(req, instance['user'], instance['password'])

        # Submit a service check for status page availability.
        parsed_url = urlparse.urlparse(url)
        nginx_host = parsed_url.hostname
        nginx_port = parsed_url.port or 80
        service_check_name = 'nginx.can_connect'
        service_check_tags = ['host:%s' % nginx_host, 'port:%s' % nginx_port]
        try:
            response = urllib2.urlopen(req)
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK,
                               tags=service_check_tags)

        body = response.read()
        resp_headers = response.info()
        return body, resp_headers.get('Content-Type', 'text/plain')

    @classmethod
    def parse_text(cls, raw, tags):
        # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
        # Connections
        output = []
        parsed = re.search(r'Active connections:\s+(\d+)', raw)
        if parsed:
            connections = int(parsed.group(1))
            output.append(('nginx.net.connections', connections, tags, 'gauge'))

        # Requests per second
        parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', raw)
        if parsed:
            conn = int(parsed.group(1))
            requests = int(parsed.group(3))
            output.extend([('nginx.net.conn_opened_per_s', conn, tags, 'rate'),
                           ('nginx.net.request_per_s', requests, tags, 'rate')])

        # Connection states, reading, writing or waiting for clients
        parsed = re.search(r'Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)', raw)
        if parsed:
            reading, writing, waiting = parsed.groups()
            output.extend([
                ("nginx.net.reading", int(reading), tags, 'gauge'),
                ("nginx.net.writing", int(writing), tags, 'gauge'),
                ("nginx.net.waiting", int(waiting), tags, 'gauge'),
            ])
        return output

    @classmethod
    def parse_json(cls, raw, tags=None):
        if tags is None:
            tags = []
        parsed = json.loads(raw)
        metric_base = 'nginx'
        output = []
        all_keys = parsed.keys()

        tagged_keys = [('caches', 'cache'), ('server_zones', 'server_zone'),
                       ('upstreams', 'upstream')]

        # Process the special keys that should turn into tags instead of
        # getting concatenated to the metric name
        for key, tag_name in tagged_keys:
            metric_name = '%s.%s' % (metric_base, tag_name)
            for tag_val, data in parsed.get(key, {}).iteritems():
                tag = '%s:%s' % (tag_name, tag_val)
                output.extend(cls._flatten_json(metric_name, data, tags + [tag]))

        # Process the rest of the keys
        rest = set(all_keys) - set([k for k, _ in tagged_keys])
        for key in rest:
            metric_name = '%s.%s' % (metric_base, key)
            output.extend(cls._flatten_json(metric_name, parsed[key], tags))

        return output

    @classmethod
    def _flatten_json(cls, metric_base, val, tags):
        ''' Recursively flattens the nginx json object. Returns the following:
            [(metric_name, value, tags)]
        '''
        output = []
        if isinstance(val, dict):
            # Pull out the server as a tag instead of trying to read as a metric
            if 'server' in val and val['server']:
                server = 'server:%s' % val.pop('server')
                if tags is None:
                    tags = [server]
                else:
                    tags = tags + [server]
            for key, val2 in val.iteritems():
                metric_name = '%s.%s' % (metric_base, key)
                output.extend(cls._flatten_json(metric_name, val2, tags))

        elif isinstance(val, list):
            for val2 in val:
                output.extend(cls._flatten_json(metric_base, val2, tags))

        elif isinstance(val, bool):
            # Turn bools into 0/1 values
            if val:
                val = 1
            else:
                val = 0
            output.append((metric_base, val, tags, 'gauge'))

        elif isinstance(val, (int, float)):
            output.append((metric_base, val, tags, 'gauge'))

        return output

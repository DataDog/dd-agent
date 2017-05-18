# stdlib
import re
import urllib2
import urlparse

# project
from util import headers
from checks import AgentCheck
from checks.utils import add_basic_auth

class Php(AgentCheck):
    """Tracks basic php-fpm metrics via the status module
    * accepted conn
    * listen queue
    * max listen queue
    * listen queue len
    * idle processes
    * active processes
    * total processes
    * max active processes
    * max children reached
    * slow requests

    Requires php-fpm pools to have the status option.
    See http://www.php.net/manual/de/install.fpm.configuration.php#pm.status-path for more details

    """

    def check(self, instance):
        if 'php_status_url' not in instance:
            raise Exception('php instance missing "php_status_url" value.')
        tags = instance.get('tags', [])
        
        response, content_type = self._get_data(instance)
        metrics = self.parse_text(response, tags)
        
        funcs = {
            'gauge': self.gauge,
            'rate': self.rate,
            'increment': self.increment
        }
        for row in metrics:
            try:
                name, value, tags, metric_type = row
                func = funcs[metric_type]
                func(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s' % repr(row))

    def _get_data(self, instance):
        url = instance.get('php_status_url')
        req = urllib2.Request(url, None, headers(self.agentConfig))
        if 'php_status_user' in instance and 'php_status_password' in instance:
            add_basic_auth(req, instance['php_status_user'], instance['php_status_password'])

        # Submit a service check for status page availability.
        parsed_url = urlparse.urlparse(url)
        php_ping_host = parsed_url.hostname
        php_ping_port = parsed_url.port or 80
        service_check_name = 'php_status.can_connect'
        service_check_tags = ['host:%s' % php_ping_host, 'port:%s' % php_ping_port]
        try:
            response = urllib2.urlopen(req)
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK)

        body = response.read()
        resp_headers = response.info()
        return body, resp_headers.get('Content-Type', 'text/plain')

    @classmethod
    def parse_text(cls, response, tags):

        GAUGES = {
            'listen queue': 'php.listen_queue',
            'max listen queue': 'php.max_listen_queue',
            'listen queue len': 'php.listen_queue_len',
            'idle processes': 'php.idle_processes',
            'active processes': 'php.active_processes',
            'total processes': 'php.total_processes',
            'max active processes': 'php.max_active_processes',
            'max children reached': 'php.max_children_reached'
        }

        RATES = {
        
        }

        INCREMENTS = {
            'accepted conn': 'php.accepted_conn',
            'slow requests': 'php.slow_requests'
        }

        output = []
        # Loop through and extract the numerical values
        for line in response.split('\n'):
            values = line.split(': ')
            if len(values) == 2: # match
                metric, value = values
                try:
                    value = float(value)
                except ValueError:
                    continue

                # Send metric as a gauge, if applicable
                if metric in GAUGES:
                    metric_name = GAUGES[metric]
                    output.append((metric_name, value, tags, 'gauge'))

                # Send metric as a rate, if applicable
                if metric in RATES:
                    metric_name = RATES[metric]
                    output.append((metric_name, value, tags, 'rate'))

                # Send metric as a increment, if applicable
                if metric in INCREMENTS:
                    metric_name = INCREMENTS[metric]
                    output.append((metric_name, value, tags, 'increment'))

        return output
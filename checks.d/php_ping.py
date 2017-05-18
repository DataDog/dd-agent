# stdlib
import re
import urllib2
import urlparse

# project
from util import headers
from checks import AgentCheck
from checks.utils import add_basic_auth

class PhpPing(AgentCheck):
    """Monitors php-fpm status via ping-url

    Requires php-fpm pools to have the status option.
    See http://www.php.net/manual/de/install.fpm.configuration.php#ping.path for more details

    """

    def check(self, instance):
        if 'php_ping_url' not in instance:
            raise Exception('php instance missing "php_ping_url" value.')
        tags = instance.get('tags', [])
        
        response, content_type = self._get_data(instance)
        metrics = self.parse_status(response, tags)
        
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
        url = instance.get('php_ping_url')
        req = urllib2.Request(url, None, headers(self.agentConfig))
        if 'php_ping_user' in instance and 'php_ping_password' in instance:
            add_basic_auth(req, instance['php_ping_user'], instance['php_ping_password'])

        # Submit a service check for status page availability.
        parsed_url = urlparse.urlparse(url)
        php_ping_host = parsed_url.hostname
        php_ping_port = parsed_url.port or 80
        service_check_name = 'php_ping.can_connect'
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
    def parse_status(cls, raw, tags):
        output = []
        parsed = re.search(r'pong', raw)
        if parsed:
            output.append(('php.ping', 1, tags, 'gauge'))

        return output

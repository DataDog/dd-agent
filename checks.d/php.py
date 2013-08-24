import urllib2
import base64

from util import headers
from checks import AgentCheck

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

    COUNTERS = {
        'accepted conn': 'php.accepted_conn',
        'slow requests': 'php.slow_requests'
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.assumed_url = {}

    def check(self, instance):
        if 'php_status_url' not in instance:
            raise Exception('php instance missing "php_status_url" value.')

        url = self.assumed_url.get(instance['php_status_url'], instance['php_status_url'])

        tags = instance.get('tags', [])

        req = urllib2.Request(url, None,
            headers(self.agentConfig))
        if 'php_status_user' in instance and 'php_status_password' in instance:
            auth_str = '%s:%s' % (instance['php_status_user'], instance['php_status_password'])
            encoded_auth_str = base64.encodestring(auth_str)
            req.add_header("Authorization", "Basic %s" % encoded_auth_str)
        request = urllib2.urlopen(req)
        response = request.read()

        metric_count = 0
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
                if metric in self.GAUGES:
                    metric_count += 1
                    metric_name = self.GAUGES[metric]
                    self.gauge(metric_name, value, tags=tags)

                # Send metric as a rate, if applicable
                if metric in self.RATES:
                    metric_count += 1
                    metric_name = self.RATES[metric]
                    self.rate(metric_name, value, tags=tags)

                # Send metric as a increment, if applicable
                if metric in self.COUNTERS:
                    metric_count += 1
                    metric_name = self.COUNTERS[metric]
                    self.increment(metric_name, value, tags=tags)

        if metric_count == 0:
            if self.assumed_url.get(instance['php_status_url'], None) is None and url[-5:] != '?auto':
                self.assumed_url[instance['php_status_url']]= '%s?auto' % url
                self.warning("Assuming url was not correct. Trying to add ?auto suffix to the url")
                self.check(instance)
            else:
                raise Exception("No metrics were fetched for this instance. Make sure that %s is the proper url." % instance['php_status_url'])

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('php_status_url'):
            return False

        return {
            'instances': [{'php_status_url': agentConfig.get('php_status_url')}]
        }
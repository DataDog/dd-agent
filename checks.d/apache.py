import urllib2

from util import headers
from checks import AgentCheck

class Apache(AgentCheck):
    """Tracks basic connection/requests/workers metrics

    See http://httpd.apache.org/docs/2.2/mod/mod_status.html for more details
    """
    GAUGES = {
        'IdleWorkers': 'apache.performance.idle_workers',
        'BusyWorkers': 'apache.performance.busy_workers',
        'CPULoad': 'apache.performance.cpu_load',
        'Uptime': 'apache.performance.uptime',
        'Total kBytes': 'apache.net.bytes',
        'Total Accesses': 'apache.net.hits',
    }

    RATES = {
        'Total kBytes': 'apache.net.request_per_s',
        'Total Accesses': 'apache.net.bytes_per_s',
    }

    def check(self, instance):
        if 'apache_status_url' not in instance:
            self.log.warn("Missing 'apache_status_url' in Apache config")
            return
        tags = instance.get('tags', [])
        req = urllib2.Request(instance['apache_status_url'], None,
            headers(self.agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()

        # Loop through and extract the numerical values
        for line in response.split('\n'):
            values = line.split(': ')
            if len(values) == 2: # match
                metric, value = values
                try:
                    value = float(value)
                except ValueError:
                    continue

                # Special case: kBytes => bytes
                if metric == 'Total kBytes':
                    value = value * 1024

                # Send metric as a gauge, if applicable
                if metric in self.GAUGES:
                    metric_name = self.GAUGES[metric]
                    self.gauge(metric_name, value, tags=tags)

                # Send metric as a rate, if applicable
                if metric in self.RATES:
                    metric_name = self.RATES[metric]
                    self.rate(metric_name, value, tags=tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('apache_status_url'):
            return False

        return {
            'instances': [{'apache_status_url': agentConfig.get('apache_status_url')}]
        }
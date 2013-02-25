import urllib2

from util import headers
from checks import AgentCheck

class Lighttpd(AgentCheck):
    """Tracks basic connection/requests/workers metrics

    See http://redmine.lighttpd.net/projects/1/wiki/Docs_ModStatus for more details
    """
    GAUGES = {
        'IdleServers': 'lighttpd.performance.idle_server',
        'BusyServers': 'lighttpd.performance.busy_servers',
        'Uptime': 'lighttpd.performance.uptime',
        'Total kBytes': 'lighttpd.net.bytes',
        'Total Accesses': 'lighttpd.net.hits',
    }

    RATES = {
        'Total kBytes': 'lighttpd.net.bytes_per_s',
        'Total Accesses': 'lighttpd.net.request_per_s'
    }

    def check(self, instance):
        if 'lighttpd_status_url' not in instance:
            raise Exception("Missing 'lighttpd_status_url' in Lighttpd config")

        tags = instance.get('tags', [])
        req = urllib2.Request(instance['lighttpd_status_url'], None,
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

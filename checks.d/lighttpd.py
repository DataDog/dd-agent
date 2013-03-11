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


    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.assumed_url = {}

    def check(self, instance):
        if 'lighttpd_status_url' not in instance:
            raise Exception("Missing 'lighttpd_status_url' variable in Lighttpd config")

        url = self.assumed_url.get(instance['lighttpd_status_url'], instance['lighttpd_status_url'])

        tags = instance.get('tags', [])
        req = urllib2.Request(url, None,
            headers(self.agentConfig))
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

                # Special case: kBytes => bytes
                if metric == 'Total kBytes':
                    value = value * 1024

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

        if metric_count == 0:
            if self.assumed_url.get('lighttpd_status_url', None) is None and url[-5:] != '?auto':
                self.assumed_url['lighttpd_status_url'] = '%s?auto' % url
                self.log.debug("Assuming url was not correct. Trying to add ?auto suffix to the url")
                self.check(instance)
            else:
                raise Exception("No metrics were fetched for this instance. Make sure that %s is the proper url." % instance['lighttpd_status_url'])


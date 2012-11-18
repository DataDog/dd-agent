import urllib2

from util import headers
from checks import AgentCheck

class Apache(AgentCheck):
    """Tracks basic connection/requests/workers metrics

    See http://httpd.apache.org/docs/2.2/mod/mod_status.html for more details
    """
    METRIC_TRANSLATION = {
        'ReqPerSec': 'apache.net.request_per_s',
        'IdleWorkers': 'apache.performance.idle_workers',
        'BusyWorkers': 'apache.performance.busy_workers',
        'CPULoad': 'apache.performance.cpu_load',
        'Uptime': 'apache.performance.uptime',
        'Total kBytes': 'apache.net.bytes',
        'Total Accesses': 'apache.net.hits',
        'BytesPerSec': 'apache.net.bytes_per_s',
    }

    def check(self, instance):
        if 'apache_status_url' not in instance:
            self.log.warn("Missing 'apache_status_url' in Apache config")
            return
        tags = instance.get('tags', [])

        try:
            req = urllib2.Request(instance['apache_status_url'], None,
                headers(self.agentConfig))
            request = urllib2.urlopen(req)
            response = request.read()

            # Loop through and extract the numerical values
            for line in response.split('\n'):
                values = line.split(': ')
                if len(values) == 2: # match
                    metric, value = values
                    metric_name = self.METRIC_TRANSLATION.get(metric, metric)
                    try:
                        if metric_name == 'apache.net.bytes':
                            self.gauge(metric_name, float(value) * 1024, tags=tags)
                        else:
                            self.gauge(metric_name, float(value), tags=tags)
                    except ValueError:
                        continue
        except:
            self.log.exception('Unable to get Apache status')

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('apache_status_url'):
            return False

        return {
            'instances': [{'apache_status_url': agentConfig.get('apache_status_url')}]
        }
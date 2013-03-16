import urllib2

from util import headers
from checks import AgentCheck


class Lighttpd2(AgentCheck):
    """Tracks Lighttpd connection/requests metrics

    See http://redmine.lighttpd.net/projects/lighttpd2/wiki/Mod_status for more details
    """
    GAUGES = {
        'memory_usage': 'lighttpd2.performance.memory_usage',
        'requests_avg': 'lighttpd2.net.requests_avg',
        'traffic_out_avg': 'lighttpd2.net.bytes_out_avg',
        'traffic_in_avg': 'lighttpd2.net.bytes_in_avg',
        'connections_avg': 'lighttpd2.net.connections_avg',
        'connection_state_start': 'lighttpd2.connections.state_start',
        'connection_state_read_header': 'lighttpd2.connections.state_read_header',
        'connection_state_handle_request': 'lighttpd2.connections.state_handle_request',
        'connection_state_write_response': 'lighttpd2.connections.state_write_response',
        'connection_state_keep_alive': 'lighttpd2.connections.state_keep_alive',
        'requests_avg_5sec': 'lighttpd2.net.requests_avg_5sec',
        'traffic_out_avg_5sec': 'lighttpd2.net.bytes_out_avg_5sec',
        'traffic_in_avg_5sec': 'lighttpd2.net.bytes_in_avg_5sec',
        'connections_avg_5sec': 'lighttpd2.net.connections_avg_5sec',
    }

    COUNTERS = {
        'requests_abs': 'lighttpd2.net.requests_total',
        'traffic_out_abs': 'lighttpd2.net.bytes_out',
        'traffic_in_abs': 'lighttpd2.net.bytes_in',
        'connections_abs': 'lighttpd2.net.connections_total',
        'status_1xx': 'lighttpd2.response.status_1xx',
        'status_2xx': 'lighttpd2.response.status_2xx',
        'status_3xx': 'lighttpd2.response.status_3xx',
        'status_4xx': 'lighttpd2.response.status_4xx',
        'status_5xx': 'lighttpd2.response.status_5xx',
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        if 'lighttpd2_status_url' not in instance:
            raise Exception("Missing 'lighttpd2_status_url' variable in Lighttpd2 config")

        url = instance['lighttpd2_status_url']
        if url.endswith('?auto'):
            raise Exception('Lighttpd2 status url (%s) requests legacy metrics, replace "?auto" with "?format=plain"' % url)

        if not url.endswith('?format=plain'):
            raise Exception('Lighttpd2 status url (%s) must end with ?format=plain' % url)

        tags = instance.get('tags', [])
        req = urllib2.Request(url, None, headers(self.agentConfig))
        request = urllib2.urlopen(req)
        response = request.read()

        metric_count = 0
        # Loop through and extract the numerical values
        for line in response.split('\n'):
            values = line.split(': ')
            if len(values) == 2:  # match
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

                # Send metric as a counter, if applicable
                if metric in self.COUNTERS:
                    metric_count += 1
                    metric_name = self.COUNTERS[metric]
                    self.increment(metric_name, value, tags=tags)

        if metric_count == 0:
            raise Exception("No metrics were fetched for this instance. Make sure that %s is the proper url." % url)

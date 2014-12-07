# stdlib
import urllib2
import urlparse

# project
from util import headers
from checks import AgentCheck

# 3rd party
import simplejson as json

class Fluentd(AgentCheck):
    SERVICE_CHECK_NAME = 'fluentd.is_ok'
    GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']

    """Tracks basic fluentd metrics via the monitor_agent plugin
    * number of retry_count
    * number of buffer_queue_length
    * number of buffer_total_queued_size

    $ curl http://localhost:24220/api/plugins.json
    {"plugins":[{"type": "monitor_agent", ...}, {"type": "forward", ...}]}
    """
    def check(self, instance):
        if 'monitor_agent_url' not in instance:
            raise Exception('Fluentd instance missing "monitor_agent_url" value.')

        try:
            url = instance.get('monitor_agent_url')
            tags = instance.get('tags', [])

            parsed_url = urlparse.urlparse(url)
            monitor_agent_host = parsed_url.hostname
            monitor_agent_port = parsed_url.port or 24220
            service_check_tags = ['fluentd_host:%s' % monitor_agent_host, 'fluentd_port:%s' % monitor_agent_port]

            req = urllib2.Request(url, None, headers(self.agentConfig))
            res = urllib2.urlopen(req).read()
            status = json.loads(res)
            metric = {}
            for p in status['plugins']:
                for n in self.GAUGES:
                    if p.get(n) is None:
                        continue
                    if not p.get('type') in metric:
                        metric[p.get('type')] = {}
                    if not n in metric[p.get('type')] or metric[p.get('type')][n] < p.get(n):
                        metric[p.get('type')][n] = p.get(n)
            for t in metric.keys():
                for m in metric[t].keys():
                    self.gauge('fluentd.%s.%s' % (t, m), metric[t][m], tags)
        except Exception, e:
            msg = "No stats could be retrieved from %s : %s" % (url, str(e))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=msg)
            raise msg
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

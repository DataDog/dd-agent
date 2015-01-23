# stdlib
from collections import defaultdict
import urllib2
import urlparse

# project
from util import headers
from checks import AgentCheck

# 3rd party
import simplejson as json

class Fluentd(AgentCheck):
    SERVICE_CHECK_NAME = 'fluentd.is_ok'
    METRICS = [
        ('retry_count', AgentCheck.gauge),
        ('buffer_queue_length', AgentCheck.gauge),
        ('buffer_total_queued_size', AgentCheck.rate),
    ]

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
            plugin_ids = instance.get('plugin_ids', [])

            parsed_url = urlparse.urlparse(url)
            monitor_agent_host = parsed_url.hostname
            monitor_agent_port = parsed_url.port or 24220
            service_check_tags = ['fluentd_host:%s' % monitor_agent_host, 'fluentd_port:%s' % monitor_agent_port]

            req = urllib2.Request(url, None, headers(self.agentConfig))
            res = urllib2.urlopen(req).read()
            status = json.loads(res)

            for p in status['plugins']:
                for m_name, m_func in self.METRICS:
                    if p.get(m_name) is None or p.get('plugin_id') not in plugin_ids:
                        continue
                    m_func(self, 'fluentd.%s' % m_name, p.get(m_name), ["plugin_id:%s" % p.get('plugin_id')])
        except Exception, e:
            msg = "No stats could be retrieved from %s : %s" % (url, str(e))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=msg)
            raise e
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

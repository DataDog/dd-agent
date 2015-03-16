# stdlib
from collections import defaultdict
import urlparse

# project
from util import headers
from checks import AgentCheck

# 3rd party
import simplejson as json
import requests

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
            plugin_ids = instance.get('plugin_ids', [])

            parsed_url = urlparse.urlparse(url)
            monitor_agent_host = parsed_url.hostname
            monitor_agent_port = parsed_url.port or 24220
            service_check_tags = ['fluentd_host:%s' % monitor_agent_host, 'fluentd_port:%s' % monitor_agent_port]

            r = requests.get(url, headers=headers(self.agentConfig))
            r.raise_for_status()
            status = r.json()

            for p in status['plugins']:
                for m in self.GAUGES:
                    if p.get(m) is None:
                        continue
                    if p.get('plugin_id') in plugin_ids:
                        self.gauge('fluentd.%s' % (m), p.get(m), ["plugin_id:%s" % p.get('plugin_id')])
        except Exception, e:
            msg = "No stats could be retrieved from %s : %s" % (url, str(e))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=msg)
            raise e
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

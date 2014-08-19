# stdlib
import re
import urllib2
import urlparse

# project
from util import headers
from checks import AgentCheck

# 3rd party
import simplejson as json

class Fluentd(AgentCheck):
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
            service_check_name = 'fluentd.is_ok'
            service_check_tags = ['host:%s' % monitor_agent_host, 'port:%s' % monitor_agent_port]

            req = urllib2.Request(url, None, headers(self.agentConfig))
            res = urllib2.urlopen(req).read()
            status = json.loads(res)
            for plg in status['plugins']:
                for metric in ('retry_count', 'buffer_total_queued_size', 'buffer_queue_length'):
                    if plg.get(metric) is not None:
                        self.histogram('fluentd.%s' % (metric), plg[metric], tags)
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK, tags=service_check_tags)

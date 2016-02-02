# stdlib
import urlparse

# 3rd party
import requests

# project
from checks import AgentCheck
from util import headers


class Fluentd(AgentCheck):
    SERVICE_CHECK_NAME = 'fluentd.is_ok'
    GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']
    _AVAILABLE_TAGS = frozenset(['plugin_id', 'type'])

    """Tracks basic fluentd metrics via the monitor_agent plugin
    * number of retry_count
    * number of buffer_queue_length
    * number of buffer_total_queued_size

    $ curl http://localhost:24220/api/plugins.json
    {"plugins":[{"type": "monitor_agent", ...}, {"type": "forward", ...}]}
    """
    def check(self, instance):
        url = instance.get('monitor_agent_url')
        plugin_ids = instance.get('plugin_ids', [])
        custom_tags = instance.get('tags', [])
        tag_by = instance.get('tag_by')

        if not url:
            raise Exception('Fluentd instance missing "monitor_agent_url" value.')

        # Fallback  with `tag_by: plugin_id`
        if tag_by not in self._AVAILABLE_TAGS:
            self.log.warning("Invalid `tag_by` paramenter: '{0}' - defaulting to 'plugin_id'".format(tag_by))
            tag_by = 'plugin_id'

        try:
            parsed_url = urlparse.urlparse(url)
            monitor_agent_host = parsed_url.hostname
            monitor_agent_port = parsed_url.port or 24220
            service_check_tags = custom_tags + ['fluentd_host:%s' % monitor_agent_host, 'fluentd_port:%s'
                                  % monitor_agent_port]

            r = requests.get(url, headers=headers(self.agentConfig))
            r.raise_for_status()
            status = r.json()

            for p in status['plugins']:
                for m in self.GAUGES:
                    value = p.get(m)
                    if value is None:
                        continue
                    # Filter unspecified plugins to keep backward compatibility.
                    if not plugin_ids or p.get('plugin_id') in plugin_ids:
                        self.gauge('fluentd.{0}'.format(m), value,
                                   custom_tags + ["{0}:{1}".format(tag_by, p.get(tag_by))])

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.HTTPError, ValueError) as e:
            msg = "Unable to retrieve stats from {url}".format(url=url)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=msg)
            raise e
        except Exception as e:
            self.log.error("Unhandled exception - unable to perform service check, submit metrics: ", e)
            raise e
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

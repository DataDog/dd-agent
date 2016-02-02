# stdlib
import urlparse

# 3rd party
import requests
import simplejson as json

# project
from checks import AgentCheck
from util import headers


class Kong(AgentCheck):
    """ collects metrics for Kong """
    def check(self, instance):
        metrics = self._fetch_data(instance)
        for row in metrics:
            try:
                name, value, tags = row
                self.gauge(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s' % repr(row))

    def _fetch_data(self, instance):
        if 'kong_status_url' not in instance:
            raise Exception('missing "kong_status_url" value')
        tags = instance.get('tags', [])
        url = instance.get('kong_status_url')

        parsed_url = urlparse.urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or 8001
        service_check_name = 'kong.can_connect'
        service_check_tags = ['host:%s' % host, 'port:%s' % port]

        try:
            self.log.debug(u"Querying URL: {0}".format(url))
            response = requests.get(url, headers=headers(self.agentConfig))
            self.log.debug(u"Kong status `response`: {0}".format(response))
            response.raise_for_status()
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK,
                               tags=service_check_tags)
        if response.status_code != 200:
            self.service_check(service_check_name, AgentCheck.CRITICAL,
                               tags=service_check_tags)

        return self._parse_json(response.content, tags)

    def _parse_json(self, raw, tags=None):
        if tags is None:
            tags = []
        parsed = json.loads(raw)
        metric_base = 'kong'
        output = []
        tagged_keys = ['database', 'server']
        for key in tagged_keys:
            metric_name = '%s.%s' % (metric_base, key)
            metric_list = []
            for tag_val, data in parsed.get(key).items():
                tag = '%s.%s' % (metric_name, tag_val)
                metric_list.append((tag, data, tags + [tag]))

            output.extend(metric_list)

        return output

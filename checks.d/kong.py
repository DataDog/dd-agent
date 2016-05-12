# stdlib
import urlparse

# 3rd party
import requests
import simplejson as json

# project
from checks import AgentCheck
from util import headers


class Kong(AgentCheck):

    METRIC_PREFIX = 'kong.'

    """ collects metrics for Kong """
    def check(self, instance):
        metrics = self._fetch_data(instance)
        for row in metrics:
            try:
                name, value, tags = row
                self.gauge(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s', row)

    def _fetch_data(self, instance):
        if 'kong_status_url' not in instance:
            raise Exception('missing "kong_status_url" value')
        tags = instance.get('tags', [])
        url = instance.get('kong_status_url')

        parsed_url = urlparse.urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or 80
        service_check_name = 'kong.can_connect'
        service_check_tags = ['kong_host:%s' % host, 'kong_port:%s' % port]

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
            if response.status_code == 200:
                self.service_check(service_check_name, AgentCheck.OK,
                                   tags=service_check_tags)
            else:
                self.service_check(service_check_name, AgentCheck.CRITICAL,
                                   tags=service_check_tags)

        return self._parse_json(response.content, tags)

    def _parse_json(self, raw, tags=None):
        if tags is None:
            tags = []
        parsed = json.loads(raw)
        output = []

        # First get the server stats
        for name, value in parsed.get('server').items():
            metric_name = self.METRIC_PREFIX + name
            output.append((metric_name, value, tags))

        # Then the database metrics
        databases_metrics = parsed.get('database').items()
        output.append((self.METRIC_PREFIX + 'table.count', len(databases_metrics), tags))
        for name, items in databases_metrics:
            output.append((self.METRIC_PREFIX + 'table.items', items, tags + ['table:{}'.format(name)]))

        return output

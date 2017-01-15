# stdlib
from collections import namedtuple

# Datadog
from checks import AgentCheck

# 3p
import requests


class PowerDNSRecursorCheck(AgentCheck):
    # See https://doc.powerdns.com/md/recursor/stats/ for metrics explanation
    GAUGE_METRICS = [
        'cache-entries',
        'concurrent-queries',
        'negcache-entries',
    ]
    RATE_METRICS = [
        'all-outqueries',
        'answers-slow',
        'answers0-1',
        'answers1-10',
        'answers10-100',
        'answers100-1000',
        'cache-hits',
        'cache-misses',
        'dont-outqueries',
        'ipv6-outqueries',
        'ipv6-questions',
        'noerror-answers',
        'nxdomain-answers',
        'outgoing-timeouts',
        'over-capacity-drops',
        'packetcache-entries',
        'packetcache-hits',
        'packetcache-misses',
        'questions',
        'servfail-answers',
        'tcp-client-overflow',
        'tcp-clients',
        'tcp-outqueries',
        'tcp-questions',
        'throttle-entries',
        'throttled-out',
        'throttled-outqueries',
        'unauthorized-tcp',
        'unauthorized-udp',
        'unexpected-packets',
    ]

    SERVICE_CHECK_NAME = 'powerdns.recursor.can_connect'

    def check(self, instance):
        config, tags = self._get_config(instance)
        stats = self._get_pdns_stats(config)
        for stat in stats:
            if stat['name'] in PowerDNSRecursorCheck.GAUGE_METRICS:
                self.gauge('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif stat['name'] in PowerDNSRecursorCheck.RATE_METRICS:
                self.rate('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)

    def _get_config(self, instance):
        required = ['host', 'port', 'api_key']
        for param in required:
            if not instance.get(param):
                raise Exception("powerdns_recursor instance missing %s. Skipping." % (param))

        host = instance.get('host')
        port = int(instance.get('port'))
        api_key = instance.get('api_key')
        tags = instance.get('tags', [])

        Config = namedtuple('Config', [
            'host',
            'port',
            'api_key']
        )

        return Config(host, port, api_key), tags

    def _get_pdns_stats(self, config):
        url = "http://{}:{}/servers/localhost/statistics".format(config.host, config.port)
        service_check_tags = ['recursor_host:{}'.format(config.host), 'recursor_port:{}'.format(config.port)]
        headers = {"X-API-Key": config.api_key}
        try:
            request = requests.get(url, headers=headers)
            request.raise_for_status()
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            raise
        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                           tags=service_check_tags)
        return request.json()

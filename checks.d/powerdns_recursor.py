# stdlib
from collections import namedtuple

# Datadog
from checks import AgentCheck

# 3p
import requests


class PowerDNSRecursorCheck(AgentCheck):
    # See https://doc.powerdns.com/md/recursor/stats/ for metrics explanation
    GAUGE_METRICS_V3 = [
        'cache-entries',
        'concurrent-queries',
        'negcache-entries',
        'packetcache-entries',
    ]
    RATE_METRICS_V3 = [
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
    GAUGE_METRICS_V4 = [
        'cache-entries',
        'concurrent-queries',
        'failed-host-entries',
        'negcache-entries',
        'packetcache-entries',
        'throttle-entries',
        'fd-usage',
    ]
    RATE_METRICS_V4 = [
        'all-outqueries',
        'answers-slow',
        'answers0-1',
        'answers1-10',
        'answers10-100',
        'answers100-1000',
        'auth4-answers-slow',
        'auth4-answers0-1',
        'auth4-answers1-10',
        'auth4-answers10-100',
        'auth4-answers100-1000',
        'auth6-answers-slow',
        'auth6-answers0-1',
        'auth6-answers1-10',
        'auth6-answers10-100',
        'auth6-answers100-1000',
        'cache-hits',
        'cache-misses',
        'case-mismatches',
        'chain-resends',
        'client-parse-errors',
        'dlg-only-drops',
        'dnssec-queries',
        'dnssec-result-bogus',
        'dnssec-result-indeterminate',
        'dnssec-result-insecure',
        'dnssec-result-nta',
        'dnssec-result-secure',
        'dnssec-validations',
        'dont-outqueries',
        'edns-ping-matches',
        'edns-ping-mismatches',
        'ignored-packets',
        'ipv6-outqueries',
        'ipv6-questions',
        'malloc-bytes',
        'max-mthread-stack',
        'no-packet-error',
        'noedns-outqueries',
        'noerror-answers',
        'noping-outqueries',
        'nsset-invalidations',
        'nsspeeds-entries',
        'nxdomain-answers',
        'outgoing-timeouts',
        'outgoing4-timeouts',
        'outgoing6-timeouts',
        'over-capacity-drops',
        'packetcache-hits',
        'packetcache-misses',
        'policy-drops',
        'policy-result-custom',
        'policy-result-drop',
        'policy-result-noaction',
        'policy-result-nodata',
        'policy-result-nxdomain',
        'policy-result-truncate',
        'qa-latency',
        'questions',
        'real-memory-usage',
        'resource-limits',
        'security-status',
        'server-parse-errors',
        'servfail-answers',
        'spoof-prevents',
        'sys-msec',
        'tcp-client-overflow',
        'tcp-clients',
        'tcp-outqueries',
        'tcp-questions',
        'throttled-out',
        'throttled-outqueries',
        'too-old-drops',
        'udp-in-errors',
        'udp-noport-errors',
        'udp-recvbuf-errors',
        'udp-sndbuf-errors',
        'unauthorized-tcp',
        'unauthorized-udp',
        'unexpected-packets',
        'unreachables',
        'uptime',
        'user-msec',
    ]

    SERVICE_CHECK_NAME = 'powerdns.recursor.can_connect'

    def check(self, instance):
        config, tags = self._get_config(instance)
        if config.version == 4:
            stats = self._get_pdns_stats_v4(config)
            for stat in stats:
                if stat['name'] in PowerDNSRecursorCheck.GAUGE_METRICS_V4:
                    self.gauge('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)
                elif stat['name'] in PowerDNSRecursorCheck.RATE_METRICS_V4:
                    self.rate('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)
        else:
            stats = self._get_pdns_stats(config)
            for stat in stats:
                if stat['name'] in PowerDNSRecursorCheck.GAUGE_METRICS_V3:
                    self.gauge('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)
                elif stat['name'] in PowerDNSRecursorCheck.RATE_METRICS_V3:
                    self.rate('powerdns.recursor.{}'.format(stat['name']), float(stat['value']), tags=tags)

    def _get_config(self, instance):
        required = ['host', 'port', 'api_key']
        for param in required:
            if not instance.get(param):
                raise Exception("powerdns_recursor instance missing %s. Skipping." % (param))

        host = instance.get('host')
        port = int(instance.get('port'))
        api_key = instance.get('api_key')
        version = instance.get('version')
        tags = instance.get('tags', [])

        Config = namedtuple('Config', [
            'host',
            'port',
            'api_key',
            'version'
        ]
        )

        return Config(host, port, api_key, version), tags

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

    def _get_pdns_stats_v4(self, config):
        url = "http://{}:{}/api/v1/servers/localhost/statistics".format(config.host, config.port)
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

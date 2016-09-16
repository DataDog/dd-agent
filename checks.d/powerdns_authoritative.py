# stdlib
from collections import namedtuple

# Datadog
from checks import AgentCheck

# 3p
import requests


class PowerDNSAuthoritativeCheck(AgentCheck):
    # See https://doc.powerdns.com/md/authoritative/stats/ for metrics explanation
    GAUGE_METRICS = [
        'corrupt-packets',
        'deferred-cache-inserts',
        'deferred-cache-lookup',
        'dnsupdate-answers',
        'dnsupdate-changes',
        'dnsupdate-queries',
        'dnsupdate-refused',
        'incoming-notifications',
        'packetcache-hit',
        'packetcache-miss',
        'packetcache-size',
        'query-cache-hit',
        'query-cache-miss',
        'rd-queries',
        'recursing-answers',
        'recursing-questions',
        'recursion-unanswered',
        'security-status',
        'servfail-packets',
        'signatures',
        'tcp-answers',
        'tcp-answers-bytes',
        'tcp-queries',
        'tcp4-answers',
        'tcp4-answers-bytes',
        'tcp4-queries',
        'tcp6-answers',
        'tcp6-answers-bytes',
        'tcp6-queries',
        'timedout-packets',
        'udp-answers',
        'udp-answers-bytes',
        'udp-do-queries',
        'udp-queries',
        'udp4-answers',
        'udp4-answers-bytes',
        'udp4-queries',
        'udp6-answers',
        'udp6-answers-bytes',
        'udp6-queries',
        'fd-usage',
        'key-cache-size',
        'latency',
        'meta-cache-size',
        'qsize-q',
        'real-memory-usage',
        'signature-cache-size',
        'sys-msec',
        'udp-in-errors',
        'udp-noport-errors',
        'udp-recvbuf-errors',
        'udp-sndbuf-errors',
        'uptime',
        'user-msec'
    ]

    SERVICE_CHECK_NAME = 'powerdns.authoritative.can_connect'

    def check(self, instance):
        config, tags = self._get_config(instance)
        stats = self._get_pdns_stats(config)
        for stat in stats:
            self.log.debug('powerdns.authoritative.{}:{}'.format(stat['name'], stat['value']))

            if stat['name'] in PowerDNSAuthoritativeCheck.GAUGE_METRICS:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif stat['name'] in PowerDNSAuthoritativeCheck.RATE_METRICS:
                self.rate('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)

    def _get_config(self, instance):
        required = ['host', 'port', 'api_key']
        for param in required:
            if not instance.get(param):
                raise Exception("powerdns_authoritative instance missing %s. Skipping." % (param))

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
        url = "http://{}:{}/api/v1/servers/localhost/statistics".format(config.host, config.port)
        service_check_tags = ['authoritative_host:{}'.format(config.host), 'authoritative_port:{}'.format(config.port)]
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
	    self.log.debug(request.json())
        return request.json()

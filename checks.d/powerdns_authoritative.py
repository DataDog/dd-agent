# stdlib
from collections import namedtuple

# Datadog
from checks import AgentCheck

# 3p
import requests

class PowerDNSAuthoritativeCheck(AgentCheck):
    # See https://doc.powerdns.com/md/authoritative/performance/#performance-monitoring for metrics explanation

    SERVICE_CHECK_NAME = 'powerdns.authoritative.can_connect'

    def check(self, instance):
        config, tags = self._get_config(instance)
        stats = self._get_pdns_stats(config)
        for stat in stats:
            self.log.debug('powerdns.authoritative.{}:{}'.format(stat['name'], stat['value']))

            if 'status' in stat['name']:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif 'size' in stat['name']:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif 'usage' in stat['name']:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif 'msec' in stat['name']:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif 'time' in stat['name']:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            elif 'latency' in stat['name']:
                self.gauge('powerdns.authoritative.{}'.format(stat['name']), float(stat['value']), tags=tags)
            else:
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

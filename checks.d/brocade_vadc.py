# stdlib
from collections import namedtuple

# Datadog
from checks import AgentCheck

# 3p
import requests


class BrocadeVadcCheck(AgentCheck):
    # See https://www.brocade.com/content/dam/common/documents/content-types/user-guide/brocade-vtm-11.0-restapi.pdf
    STATS_API = 'api/tm/3.10/status/local_tm/statistics'

    # this is a list of endpoints to recursively query for values
    METRICS_ENDPOINTS = [
        'pools',
        'virtual_servers',
    ]

    # these are the metrics to collect all 64bit integers.
    POOL_RATE = [
        'bytes_in',
        'bytes_out',
        'conns_queued',
        'queue_timeouts',
    ]
    POOL_GAUGE = [
        'max_queue_time',
        'mean_queue_time',
        'min_queue_time',
        'nodes',
        'session_migrated',
        'session_migrated',
        'total_conn',
    ]
    VIRTUAL_SERVER_RATE = [
        'bytes_in',
        'bytes_out',
        'cert_status_requests',
        'cert_status_responses',
        'connect_timed_out',
        'connection_errors',
        'connection_failures',
        'data_timed_out',
        'direct_replies',
        'discard',
        'gzip',
        'gzip_bytes_saved',
        'http_cache_hit_rate',
        'http_cache_hits',
        'http_cache_lookups',
        'http_rewrite_cookie',
        'http_rewrite_location',
        'keepalive_timed_out',
        'max_duration_timed_out',
        'processing_timed_out',
        'sip_rejected_requests',
        'sip_total_calls',
        'total_dgram',
        'total_http1_requests',
        'total_http2_requests',
        'total_http_requests',
        'total_requests',
        'total_tcp_reset',
        'total_udp_unreachables',
        'udp_timed_out',
    ]
    VIRTUAL_SERVER_GAUGE = [
        'current_conn',
        'max_conn',
    ]

    SERVICE_CHECK_NAME = 'brocade_vadc.can_connect'

    def check(self, instance):
        config, tags = self._get_config(instance)
        stats = self._get_vadc_stats(config)

        # iterate over the different metrics endpoints in the stats dict
        # required because the nesting is different depending on the metric
        # type collected.
        for endpoint in BrocadeVadcCheck.METRICS_ENDPOINTS:
            if endpoint == 'pools':
                self._get_pool_stats(stats[endpoint], tags)
            elif endpoint == 'virtual_servers':
                self._get_virtualserver_stats(stats[endpoint], tags)

    def _get_config(self, instance):
        required = ['host', 'port', 'username', 'password']
        for param in required:
            if not instance.get(param):
                raise Exception("brocade_vadc instance missing %s. Skipping." % (param))

        host = instance.get('host')
        port = int(instance.get('port'))
        username = instance.get('username')
        password = instance.get('password')
        verify_ssl = instance.get('verify_ssl')
        tags = instance.get('tags', [])

        Config = namedtuple('Config', [
            'host',
            'port',
            'username',
            'password',
            'verify_ssl',
        ])

        return Config(host, port, username, password, verify_ssl), tags

    def _get_vadc_stats(self, config):
        stats = {}
        service_check_tags = [
            'brocade_vadc_host:{}'.format(config.host),
            'brocade_vadc_port:{}'.format(config.port),
        ]

        try:
            session = requests.Session()
            session.auth = (config.username, config.password)
            url = "https://{}:{}/{}".format(config.host, config.port, self.STATS_API)

            g = session.get(url, verify=config.verify_ssl)
            g.raise_for_status()

        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            raise

        for METRICS in self.METRICS_ENDPOINTS:
            url = "https://{}:{}/{}/{}/".format(config.host, config.port, self.STATS_API, METRICS)
            # create a temp dict that we use to roll-up into the stats dict created above.
            tmp = {}
            try:
                s = session.get(url, verify=config.verify_ssl)
                s.raise_for_status()
            except Exception:
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   tags=service_check_tags)

            for ref in s.json().get("children"):
                if ref is None:
                    continue
                else:
                    # we strip the tailing / out of the url format because the href returned from the API
                    # already includes it.
                    tmp[ref.get("name")] = session.get("https://{}:{}{}".format(config.host,
                                                                                config.port,
                                                                                ref.get("href"))).json()

            # roll-up tmp into stats{}
            stats[METRICS] = tmp

        self.service_check(self.SERVICE_CHECK_NAME,
                           AgentCheck.OK,
                           tags=service_check_tags)
        return stats

    def _get_pool_stats(self, stats, tags):
        for pool_name in stats:
            for name, value in stats[pool_name]['statistics'].items():
                if name in BrocadeVadcCheck.POOL_GAUGE:
                    self.gauge('brocade_vadc.pool.{}.{}'.format(pool_name, name),
                               float(value),
                               tags=tags)
                elif name in BrocadeVadcCheck.POOL_RATE:
                    self.rate('brocade_vadc.pool.{}.{}'.format(pool_name, name),
                              float(value),
                              tags=tags)

    def _get_virtualserver_stats(self, stats, tags):
        for virtual_server in stats:
            for name, value in stats[virtual_server]['statistics'].items():
                if name in BrocadeVadcCheck.VIRTUAL_SERVER_GAUGE:
                    self.gauge('brocade_vadc.virtual_server.{}.{}'.format(virtual_server, name), float(value),
                               tags=tags)
                elif name in BrocadeVadcCheck.VIRTUAL_SERVER_RATE:
                    self.rate('brocade_vadc.virtual_server.{}.{}'.format(virtual_server, name), float(value), tags=tags)

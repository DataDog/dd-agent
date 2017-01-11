# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

import os


@attr(requires='brocade_vadc')
class TestBrocadeVadcCheck(AgentCheckTest):
    CHECK_NAME = 'brocade_vadc'

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

    METRICS_FORMAT = 'brocade_vadc.{}.{}.{}'

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {"instances": [{
            "host": "127.0.0.1",
            "port": "9070",
            "username": "admin",
            "password": os.getenv('VADC_PASSWORD'),
            "verify_ssl": False,
        }]}

    # Really a basic check to see if all metrics are there
    def test_check(self):
        self.run_check_twice(self.config)

        # Assert metrics
        for metric in self.VIRTUAL_SERVER_GAUGE:
            self.assertMetric(self.METRICS_FORMAT.format("virtual_server",
                                                         "10.1.1.1",
                                                         metric),
                              at_least=0,
                              tags=[])

        for metric in self.VIRTUAL_SERVER_RATE:
            self.assertMetric(self.METRICS_FORMAT.format("virtual_server",
                                                         "10.1.1.1",
                                                         metric),
                              at_least=0,
                              tags=[])

        for pool in ["discard", "pool-1"]:
            for metric in self.POOL_GAUGE:
                self.assertMetric(self.METRICS_FORMAT.format("pool",
                                                             pool,
                                                             metric),
                                  at_least=0,
                                  tags=[])

            for metric in self.POOL_RATE:
                self.assertMetric(self.METRICS_FORMAT.format("pool",
                                                             pool,
                                                             metric),
                                  at_least=0,
                                  tags=[])

        service_check_tags = ['brocade_vadc_host:127.0.0.1', 'brocade_vadc_port:9070']
        self.assertServiceCheckOK('brocade_vadc.can_connect', tags=service_check_tags)

        self.coverage_report()

    def test_tags(self):
        config = self.config.copy()
        tags = ['foo:bar']
        config['instances'][0]['tags'] = ['foo:bar']
        self.run_check_twice(config)

        # Assert metrics
        for metric in self.VIRTUAL_SERVER_GAUGE:
            self.assertMetric(self.METRICS_FORMAT.format("virtual_server",
                                                         "10.1.1.1",
                                                         metric),
                              at_least=0,
                              tags=tags)

        for metric in self.VIRTUAL_SERVER_RATE:
            self.assertMetric(self.METRICS_FORMAT.format("virtual_server",
                                                         "10.1.1.1",
                                                         metric),
                              at_least=0,
                              tags=tags)

        for pool in ["discard", "pool-1"]:
            for metric in self.POOL_GAUGE:
                self.assertMetric(self.METRICS_FORMAT.format("pool",
                                                             pool,
                                                             metric),
                                  at_least=0,
                                  tags=tags)

            for metric in self.POOL_RATE:
                self.assertMetric(self.METRICS_FORMAT.format("pool",
                                                             pool,
                                                             metric),
                                  at_least=0,
                                  tags=tags)

        service_check_tags = ['brocade_vadc_host:127.0.0.1', 'brocade_vadc_port:9070']
        self.assertServiceCheckOK('brocade_vadc.can_connect', tags=service_check_tags)

        self.coverage_report()

    def test_bad_config(self):
        config = self.config.copy()
        config['instances'][0]['port'] = 1111
        service_check_tags = ['brocade_vadc_host:127.0.0.1', 'brocade_vadc_port:1111']
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheckCritical('brocade_vadc.can_connect', tags=service_check_tags)
        self.coverage_report()

    def test_bad_password(self):
        config = self.config.copy()
        config['instances'][0]['password'] = 'nope'
        service_check_tags = ['brocade_vadc_host:127.0.0.1', 'brocade_vadc_port:9070']
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheckCritical('brocade_vadc.can_connect', tags=service_check_tags)
        self.coverage_report()

    def test_very_bad_config(self):
        for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
            self.assertRaises(
                Exception,
                lambda: self.run_check({"instances": [config]})
            )
        self.coverage_report()

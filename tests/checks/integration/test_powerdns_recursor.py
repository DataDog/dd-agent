# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

import os


@attr(requires='powerdns_recursor')
class TestPowerDNSRecursorCheck(AgentCheckTest):
    CHECK_NAME = 'powerdns_recursor'

    GAUGE_METRICS = [
        'cache-entries',
        'concurrent-queries',
        'failed-host-entries',
        'negcache-entries',
        'packetcache-entries',
        'throttle-entries',
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
        'chain-resends',
        'case-mismatches',
        'client-parse-errors',
        'dont-outqueries',
        'ipv6-outqueries',
        'ipv6-questions',
        'malloc-bytes',
        'noerror-answers',
        'nxdomain-answers',
        'max-mthread-stack',
        'outgoing-timeouts',
        'over-capacity-drops',
        'packetcache-hits',
        'packetcache-misses',
        'policy-drops',
        'qa-latency',
        'questions',
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
        'unauthorized-tcp',
        'unauthorized-udp',
        'unexpected-packets',
        'unreachables',
    ]
    GAUGE_METRICS_V4 = [
        'fd-usage',
    ]
    RATE_METRICS_V4 = [
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
        'dlg-only-drops',
        'dnssec-queries',
        'dnssec-result-bogus',
        'dnssec-result-indeterminate',
        'dnssec-result-insecure',
        'dnssec-result-nta',
        'dnssec-result-secure',
        'dnssec-validations',
        'edns-ping-matches',
        'edns-ping-mismatches',
        'ignored-packets',
        'no-packet-error',
        'noedns-outqueries',
        'noping-outqueries',
        'nsset-invalidations',
        'nsspeeds-entries',
        'outgoing4-timeouts',
        'outgoing6-timeouts',
        'policy-result-custom',
        'policy-result-drop',
        'policy-result-noaction',
        'policy-result-nodata',
        'policy-result-nxdomain',
        'policy-result-truncate',
        'real-memory-usage',
        'resource-limits',
        'too-old-drops',
        'udp-in-errors',
        'udp-noport-errors',
        'udp-recvbuf-errors',
        'udp-sndbuf-errors',
        'uptime',
        'user-msec',
    ]

    METRIC_FORMAT = 'powerdns.recursor.{}'

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config_v3 = {"instances": [{
            "host": "127.0.0.1",
            "port": "8082",
            "api_key": "pdns_api_key"
        }]}
        self.config_v4 = {"instances": [{
            "host": "127.0.0.1",
            "port": "8083",
            "api_key": "pdns_api_key",
            "version": 4
        }]}

    # Really a basic check to see if all metrics are there
    def test_check(self):
        # Run Version 3
        flavor = os.environ.get("FLAVOR_VERSION")
        if flavor == "3.7.3":
            self.run_check_twice(self.config_v3)

            # Assert metrics
            for metric in self.GAUGE_METRICS:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            for metric in self.RATE_METRICS:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
            self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)
            self.coverage_report()
        elif flavor is None:
            self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
        else:
            service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
            self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)
            self.coverage_report()

    # The version 4 check extends the base-line v3 metrics with the v4.
    def test_check_v4(self):
        # Run Version 4
        flavor = os.environ.get("FLAVOR_VERSION")
        if flavor == "4.0.3":
            self.run_check_twice(self.config_v4)

            # Assert metrics
            for metric in self.GAUGE_METRICS + self.GAUGE_METRICS_V4:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            for metric in self.RATE_METRICS + self.RATE_METRICS_V4:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8083']
            self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)

            self.coverage_report()
        elif flavor is None:
            self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
        else:
            service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8083']
            self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)

            self.coverage_report()

    def test_tags(self):
        config = self.config_v3.copy()
        tags = ['foo:bar']
        config['instances'][0]['tags'] = ['foo:bar']
        self.run_check_twice(config)

        # Assert metrics v3
        for metric in self.GAUGE_METRICS:
            self.assertMetric(self.METRIC_FORMAT.format(metric), tags=tags)

        for metric in self.RATE_METRICS:
            self.assertMetric(self.METRIC_FORMAT.format(metric), tags=tags)

        service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
        self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)

        self.coverage_report()

    def test_bad_config(self):
        config = self.config_v3.copy()
        config['instances'][0]['port'] = 1111
        service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:1111']
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
        self.coverage_report()

    def test_bad_api_key(self):
        config = self.config_v3.copy()
        config['instances'][0]['api_key'] = 'nope'
        service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
        self.coverage_report()

    def test_very_bad_config(self):
        for config in [{}, {"host": "localhost"}, {"port": 1000}, {"host": "localhost", "port": 1000}]:
            self.assertRaises(
                Exception,
                lambda: self.run_check({"instances": [config]})
            )
        self.coverage_report()

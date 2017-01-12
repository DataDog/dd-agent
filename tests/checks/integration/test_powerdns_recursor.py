# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

import requests


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
        self.config = {"instances": [{
            "host": "127.0.0.1",
            "port": "8082",
            "api_key": "pdns_api_key"
        }]}

    # Really a basic check to see if all metrics are there
    def test_check(self):
        service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']

        # get version and test v3 first.
        version = self._get_pdns_version()
        if version == 3:
            self.run_check_twice(self.config)

            # Assert metrics
            for metric in self.GAUGE_METRICS:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            for metric in self.RATE_METRICS:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)
            self.coverage_report()

        elif version == 4:
            # copy the configuration and set the version to 4
            config = self.config.copy()
            config['instances'][0]['version'] = 4
            self.run_check_twice(config)

            # Assert metrics
            for metric in self.GAUGE_METRICS + self.GAUGE_METRICS_V4:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            for metric in self.RATE_METRICS + self.RATE_METRICS_V4:
                self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

            self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)

            self.coverage_report()
        else:
            print("powerdns_recursor unknown version.")
            self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)

    def test_tags(self):
        config = self.config.copy()
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
        config = self.config.copy()
        config['instances'][0]['port'] = 1111
        service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:1111']
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheckCritical('powerdns.recursor.can_connect', tags=service_check_tags)
        self.coverage_report()

    def test_bad_api_key(self):
        config = self.config.copy()
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

    def _get_pdns_version(self):
        headers = {"X-API-Key": self.config['instances'][0]['api_key']}
        url = "http://{}:{}/api/v1/servers/localhost/statistics".format(self.config['instances'][0]['host'],
                                                                        self.config['instances'][0]['port'])
        request = requests.get(url, headers=headers)
        if request.status_code == 404:
            return 3
        else:
            return 4

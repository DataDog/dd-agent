# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest


@attr(requires='powerdns_recursor')
class TestPowerDNSRecursorCheck(AgentCheckTest):
    CHECK_NAME = 'powerdns_recursor'

    GAUGE_METRICS = [
        'cache-entries',
        'concurrent-queries',
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
        'noerror-answers',
        'outgoing-timeouts',
        'questions',
        'servfail-answers',
        'tcp-outqueries',
        'tcp-questions',
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
        self.run_check_twice(self.config)

        # Assert metrics
        for metric in self.GAUGE_METRICS:
            self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

        for metric in self.RATE_METRICS:
            self.assertMetric(self.METRIC_FORMAT.format(metric), tags=[])

        service_check_tags = ['recursor_host:127.0.0.1', 'recursor_port:8082']
        self.assertServiceCheckOK('powerdns.recursor.can_connect', tags=service_check_tags)

        self.coverage_report()

    def test_tags(self):
        config = self.config.copy()
        tags = ['foo:bar']
        config['instances'][0]['tags'] = ['foo:bar']
        self.run_check_twice(config)

        # Assert metrics
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

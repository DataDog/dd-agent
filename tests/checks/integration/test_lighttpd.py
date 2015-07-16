from nose.plugins.attrib import attr

from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='lighttpd')
class TestLighttpd(AgentCheckTest):
    CHECK_NAME = 'lighttpd'
    CHECK_GAUGES = [
        'lighttpd.net.bytes',
        'lighttpd.net.bytes_per_s',
        'lighttpd.net.hits',
        'lighttpd.net.request_per_s',
        'lighttpd.performance.busy_servers',
        'lighttpd.performance.idle_server',
        'lighttpd.performance.uptime',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {
            'instances': [
                {
                    'lighttpd_status_url': 'http://localhost:9449/server-status',
                    'tags': ['instance:first'],
                }
            ]
        }

    def test_lighttpd(self):
        self.run_check_twice(self.config)
        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.OK,
                                tags=['host:localhost', 'port:9449'])

        for gauge in self.CHECK_GAUGES:
            self.assertMetric(gauge, tags=['instance:first'], count=1)
        self.coverage_report()

    def test_bad_config(self):
        self.assertRaises(
            Exception,
            lambda: self.run_check({"instances": [{'lighttpd_status_url': 'http://localhost:1337',
                                                   'tags': ['instance: first']}]})
        )
        self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                status=AgentCheck.CRITICAL,
                                tags=['host:localhost', 'port:1337'],
                                count=1)

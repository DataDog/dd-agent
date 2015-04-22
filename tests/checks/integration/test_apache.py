# stdlib
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='apache')
class TestCheckApache(AgentCheckTest):
    CHECK_NAME = 'apache'

    CONFIG_STUBS = [
        {
            'apache_status_url': 'http://localhost:8080/server-status',
            'tags': ['instance:first']
        },
        {
            'apache_status_url': 'http://localhost:8080/server-status?auto',
            'tags': ['instance:second']
        },
    ]
    BAD_CONFIG = [
        {
            'apache_status_url': 'http://localhost:1234/server-status',
        }
    ]

    APACHE_GAUGES = [
        'apache.performance.idle_workers',
        'apache.performance.busy_workers',
        'apache.performance.cpu_load',
        'apache.performance.uptime',
        'apache.net.bytes',
        'apache.net.hits'
    ]

    APACHE_RATES = [
        'apache.net.bytes_per_s',
        'apache.net.request_per_s'
    ]

    def test_check(self):
        config = {
            'instances': self.CONFIG_STUBS
        }

        self.run_check_twice(config)

        # Assert metrics
        for stub in self.CONFIG_STUBS:
            expected_tags = stub['tags']

            for mname in self.APACHE_GAUGES + self.APACHE_RATES:
                self.assertMetric(mname, tags=expected_tags, count=1)

        # Assert service checks
        self.assertServiceCheck('apache.can_connect', status=AgentCheck.OK,
                                tags=['host:localhost', 'port:8080'], count=2)

        self.coverage_report()

    def test_connection_failure(self):
        config = {
            'instances': self.BAD_CONFIG
        }

        # Assert service check
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheck('apache.can_connect', status=AgentCheck.CRITICAL,
                                tags=['host:localhost', 'port:1234'], count=1)

        self.coverage_report()

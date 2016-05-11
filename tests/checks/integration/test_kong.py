# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='kong')
class TestKong(AgentCheckTest):
    CHECK_NAME = 'kong'

    CONFIG_STUBS = [
        {
            'kong_status_url': 'http://localhost:8001/status/',
            'tags': ['first_instance']
        },
        {
            'kong_status_url': 'http://localhost:8001/status/',
            'tags': ['second_instance']
        }
    ]

    BAD_CONFIG = [
        {
            'kong_status_url': 'http://localhost:1111/status/'
        }
    ]

    GAUGES = [
        'kong.server.total_requests',
        'kong.server.connections_active',
        'kong.server.connections_waiting',
        'kong.server.connections_reading',
        'kong.server.connections_accepted',
        'kong.server.connections_writing',
        'kong.server.connections_handled',
        'kong.database.acls',
        'kong.database.keyauth_credentials',
        'kong.database.hmacauth_credentials',
        'kong.database.oauth2_credentials',
        'kong.database.consumers',
        'kong.database.nodes',
        'kong.database.response_ratelimiting_metrics',
        'kong.database.ratelimiting_metrics',
        'kong.database.oauth2_tokens',
        'kong.database.plugins',
        'kong.database.oauth2_authorization_codes',
        'kong.database.apis',
        'kong.database.jwt_secrets',
        'kong.database.basicauth_credentials',
    ]

    def test_check(self):
        config = {
            'instances': self.CONFIG_STUBS
        }

        self.run_check_twice(config)

        # Assert metrics
        for stub in self.CONFIG_STUBS:
            for mname in self.GAUGES :
                expected_tags = stub['tags']
                self.assertMetric(mname, tags=expected_tags, count=1)

        # Assert service checks
        self.assertServiceCheck('kong.can_connect', status=AgentCheck.OK,
                                tags=['kong_host:localhost', 'kong_port:8001'], count=2)

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
        self.assertServiceCheck('kong.can_connect', status=AgentCheck.CRITICAL,
                                tags=['kong_host:localhost', 'kong_port:1111'], count=1)

        self.coverage_report()

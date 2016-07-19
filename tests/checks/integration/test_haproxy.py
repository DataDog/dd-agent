# stdlib
import os

# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest
from util import get_hostname


@attr(requires='haproxy')
class HaproxyTest(AgentCheckTest):
    CHECK_NAME = 'haproxy'

    BACKEND_SERVICES = ['anotherbackend', 'datadog']

    BACKEND_LIST = ['singleton:8080', 'singleton:8081', 'otherserver']

    FRONTEND_CHECK_GAUGES = [
        'haproxy.frontend.session.current',
        'haproxy.frontend.session.limit',
        'haproxy.frontend.session.pct',
    ]

    FRONTEND_CHECK_GAUGES_POST_1_4 = [
        'haproxy.frontend.requests.rate',
    ]

    BACKEND_CHECK_GAUGES = [
        'haproxy.backend.queue.current',
        'haproxy.backend.session.current',
    ]

    BACKEND_CHECK_GAUGES_POST_1_5 = [
        'haproxy.backend.queue.time',
        'haproxy.backend.connect.time',
        'haproxy.backend.response.time',
        'haproxy.backend.session.time',
    ]

    FRONTEND_CHECK_RATES = [
        'haproxy.frontend.bytes.in_rate',
        'haproxy.frontend.bytes.out_rate',
        'haproxy.frontend.denied.req_rate',
        'haproxy.frontend.denied.resp_rate',
        'haproxy.frontend.errors.req_rate',
        'haproxy.frontend.session.rate',
    ]

    FRONTEND_CHECK_RATES_POST_1_4 = [
        'haproxy.frontend.response.1xx',
        'haproxy.frontend.response.2xx',
        'haproxy.frontend.response.3xx',
        'haproxy.frontend.response.4xx',
        'haproxy.frontend.response.5xx',
        'haproxy.frontend.response.other',
    ]

    BACKEND_CHECK_RATES = [
        'haproxy.backend.bytes.in_rate',
        'haproxy.backend.bytes.out_rate',
        'haproxy.backend.denied.resp_rate',
        'haproxy.backend.errors.con_rate',
        'haproxy.backend.errors.resp_rate',
        'haproxy.backend.session.rate',
        'haproxy.backend.warnings.redis_rate',
        'haproxy.backend.warnings.retr_rate',
    ]

    BACKEND_CHECK_RATES_POST_1_4 = [
        'haproxy.backend.response.1xx',
        'haproxy.backend.response.2xx',
        'haproxy.backend.response.3xx',
        'haproxy.backend.response.4xx',
        'haproxy.backend.response.5xx',
        'haproxy.backend.response.other',
    ]

    def __init__(self, *args, **kwargs):
        AgentCheckTest.__init__(self, *args, **kwargs)
        self.config = {
            "instances": [{
                'url': 'http://localhost:3835/stats',
                'username': 'datadog',
                'password': 'isdevops',
                'status_check': True,
                'collect_aggregates_only': False,
                'tag_service_check_by_host': True,
            }]
        }
        self.config_open = {
            'instances': [{
                'url': 'http://localhost:3836/stats',
                'collect_aggregates_only': False,
            }]
        }

    def _test_frontend_metrics(self, shared_tag):
        frontend_tags = shared_tag + ['type:FRONTEND', 'service:public']
        for gauge in self.FRONTEND_CHECK_GAUGES:
            self.assertMetric(gauge, tags=frontend_tags, count=1)

        if os.environ.get('FLAVOR_VERSION', '').split('.')[:2] >= ['1', '4']:
            for gauge in self.FRONTEND_CHECK_GAUGES_POST_1_4:
                self.assertMetric(gauge, tags=frontend_tags, count=1)

        for rate in self.FRONTEND_CHECK_RATES:
            self.assertMetric(rate, tags=frontend_tags, count=1)

        if os.environ.get('FLAVOR_VERSION', '').split('.')[:2] >= ['1', '4']:
            for rate in self.FRONTEND_CHECK_RATES_POST_1_4:
                self.assertMetric(rate, tags=frontend_tags, count=1)

    def _test_backend_metrics(self, shared_tag, services=None):
        backend_tags = shared_tag + ['type:BACKEND']
        if not services:
            services = self.BACKEND_SERVICES
        for service in services:
            for backend in self.BACKEND_LIST:
                tags = backend_tags + ['service:' + service, 'backend:' + backend]

                for gauge in self.BACKEND_CHECK_GAUGES:
                    self.assertMetric(gauge, tags=tags, count=1)

                if os.environ.get('FLAVOR_VERSION', '').split('.')[:2] >= ['1', '5']:
                    for gauge in self.BACKEND_CHECK_GAUGES_POST_1_5:
                        self.assertMetric(gauge, tags=tags, count=1)

                for rate in self.BACKEND_CHECK_RATES:
                    self.assertMetric(rate, tags=tags, count=1)

                if os.environ.get('FLAVOR_VERSION', '').split('.')[:2] >= ['1', '4']:
                    for rate in self.BACKEND_CHECK_RATES_POST_1_4:
                        self.assertMetric(rate, tags=tags, count=1)

    def _test_service_checks(self, services=None):
        if not services:
            services = self.BACKEND_SERVICES
        for service in services:
            for backend in self.BACKEND_LIST:
                tags = ['service:' + service, 'backend:' + backend]
                self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                        status=AgentCheck.UNKNOWN,
                                        count=1,
                                        tags=tags)
            tags = ['service:' + service, 'backend:BACKEND']
            self.assertServiceCheck(self.check.SERVICE_CHECK_NAME,
                                    status=AgentCheck.OK,
                                    count=1,
                                    tags=tags)

    def test_check(self):
        self.run_check_twice(self.config)

        shared_tag = ['instance_url:http://localhost:3835/stats']

        self._test_frontend_metrics(shared_tag)
        self._test_backend_metrics(shared_tag)

        # check was run 2 times
        #       - FRONTEND is reporting OPEN that we ignore
        #       - only the BACKEND aggregate is reporting UP -> OK
        #       - The 3 individual servers are returning no check -> UNKNOWN
        self._test_service_checks()

        # Make sure the service checks aren't tagged with an empty hostname.
        self.assertEquals(self.service_checks[0]['host_name'], get_hostname())

        self.coverage_report()

    def test_check_service_filter(self):
        config = self.config
        config['instances'][0]['services_include'] = ['datadog']
        config['instances'][0]['services_exclude'] = ['.*']
        self.run_check_twice(config)
        shared_tag = ['instance_url:http://localhost:3835/stats']

        self._test_backend_metrics(shared_tag, ['datadog'])

        self._test_service_checks(['datadog'])

        self.coverage_report()

    def test_wrong_config(self):
        config = self.config
        config['instances'][0]['username'] = 'fake_username'

        self.assertRaises(Exception, lambda: self.run_check(config))

        # Test that nothing has been emitted
        self.coverage_report()

    def test_open_config(self):
        self.run_check_twice(self.config_open)

        shared_tag = ['instance_url:http://localhost:3836/stats']

        self._test_frontend_metrics(shared_tag)
        self._test_backend_metrics(shared_tag)
        self._test_service_checks()

        # This time, make sure the hostname is empty
        self.assertEquals(self.service_checks[0]['host_name'], '')

        self.coverage_report()

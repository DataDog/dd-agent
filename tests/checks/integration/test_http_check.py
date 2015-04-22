import time
import mock

from checks import AgentCheck
from tests.checks.common import AgentCheckTest

RESULTS_TIMEOUT = 5

CONFIG = {
    'instances': [{
        'name': 'conn_error',
        'url': 'https://thereisnosuchlink.com',
        'check_certificate_expiration': False,
        'timeout': 1,
    }, {
        'name': 'http_error_status_code',
        'url': 'http://httpbin.org/404',
        'check_certificate_expiration': False,
        'timeout': 1,
    }, {
        'name': 'status_code_match',
        'url': 'http://httpbin.org/404',
        'http_response_status_code': '4..',
        'check_certificate_expiration': False,
        'timeout': 1,
    }, {
        'name': 'cnt_mismatch',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': False,
        'content_match': 'thereisnosuchword'
    }, {
        'name': 'cnt_match',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': False,
        'content_match': '(thereisnosuchword|github)'
    }
    ]
}

CONFIG_SSL_ONLY = {
    'instances': [{
        'name': 'good_cert',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': True,
        'days_warning': 14
    }, {
        'name': 'cert_exp_soon',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': True,
        'days_warning': 9999
    }, {
        'name': 'conn_error',
        'url': 'https://thereisnosuchlink.com',
        'timeout': 1,
        'check_certificate_expiration': True,
        'days_warning': 14
    }
    ]
}

CONFIG_EXPIRED_SSL = {
    'instances': [{
        'name': 'expired_cert',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': True,
        'days_warning': 14
    },
    ]
}


FAKE_CERT = {'notAfter': 'Apr 12 12:00:00 2006 GMT'}


class HTTPCheckTest(AgentCheckTest):
    CHECK_NAME = 'http_check'

    def tearDown(self):
        self.check.stop()

    def wait_for_async_service_checks(self, count):
        i = 0
        while i < RESULTS_TIMEOUT:
            self.check._process_results()
            if len(self.check.service_checks) >= count:
                return self.check.get_service_checks()
            time.sleep(1)
            i += 1
        raise Exception("Didn't get the right count of service checks in time {0}"
                        .format(self.check.service_checks))

    def test_check(self):
        self.run_check(CONFIG)
        # Overrides self.service_checks attribute when values are available\
        self.service_checks = self.wait_for_async_service_checks(5)

        # HTTP connection error
        self.assertServiceCheck("http_check.conn_error", status=AgentCheck.CRITICAL,
                                tags=['url:https://thereisnosuchlink.com'])

        # Wrong HTTP response status code
        self.assertServiceCheck("http_check.http_error_status_code", status=AgentCheck.CRITICAL,
                                tags=['url:http://httpbin.org/404'])
        self.assertServiceCheck("http_check.http_error_status_code", status=AgentCheck.OK,
                                tags=['url:http://httpbin.org/404'], count=0)

        # HTTP response status code match
        self.assertServiceCheck("http_check.status_code_match", status=AgentCheck.OK,
                                tags=['url:http://httpbin.org/404'])

        # Content match & mismatching
        self.assertServiceCheck("http_check.cnt_mismatch", status=AgentCheck.CRITICAL,
                                tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.cnt_mismatch", status=AgentCheck.OK,
                                tags=['url:https://github.com'], count=0)
        self.assertServiceCheck("http_check.cnt_match", status=AgentCheck.OK,
                                tags=['url:https://github.com'])

        self.coverage_report()

    def test_check_ssl(self):
        self.run_check(CONFIG_SSL_ONLY)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async_service_checks(6)
        self.assertServiceCheck("http_check.ssl_cert.good_cert", status=AgentCheck.OK,
                                tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.ssl_cert.cert_exp_soon", status=AgentCheck.WARNING,
                                tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.ssl_cert.conn_error", status=AgentCheck.CRITICAL,
                                tags=['url:https://thereisnosuchlink.com'])

        self.coverage_report()

    @mock.patch('ssl.SSLSocket.getpeercert', return_value=FAKE_CERT)
    def test_mock_case(self, getpeercert_func):
        self.run_check(CONFIG_EXPIRED_SSL)
        # Overrides self.service_checks attribute when values are av
        # Needed for the HTTP headers
        self.service_checks = self.wait_for_async_service_checks(2)
        self.assertServiceCheck("http_check.ssl_cert.expired_cert", status=AgentCheck.CRITICAL,
                                tags=['url:https://github.com'])
        self.coverage_report()

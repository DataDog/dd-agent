import time
import mock

from checks import AgentCheck
from tests.common import AgentCheckTest

RESULTS_TIMEOUT = 5

CONFIG = {
    'instances': [{
        'name': 'bad_url',
        'url': 'https://thereisnosuchlink.com',
        'check_certificate_expiration': False,
        'timeout': 1,
    }, {
        'name': 'timing_out',
        'url': 'https://github.com',
        'check_certificate_expiration': False,
        'timeout': 0.0001,
    }, {
        'name': 'content_mismatch',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': False,
        'content_match': 'thereisnosuchcontent'
    }, {
        'name': 'this_one_is_ok',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': False,
        'content_match': 'github'
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
        'name': 'bad_url',
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
        raise Exception("Didn't get the right count of service checks in time {}"
                        .format(self.check.service_checks))

    def test_check(self):
        self.run_check(CONFIG)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async_service_checks(4)

        self.assertServiceCheck("http_check.bad_url", status=AgentCheck.CRITICAL,
                                tags=['url:https://thereisnosuchlink.com'])
        self.assertServiceCheck("http_check.timing_out", status=AgentCheck.CRITICAL,
                                tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.content_mismatch", status=AgentCheck.CRITICAL,
                                tags=['url:https://github.com'])
        self.assertRaises(AssertionError, self.assertServiceCheck, "http_check.content_mismatch",
                          status=AgentCheck.OK, tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.this_one_is_ok", status=AgentCheck.OK,
                                tags=['url:https://github.com'])

    def test_check_ssl(self):
        self.run_check(CONFIG_SSL_ONLY)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async_service_checks(6)
        self.assertServiceCheck("http_check.ssl_cert.good_cert", status=AgentCheck.OK,
                                tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.ssl_cert.cert_exp_soon", status=AgentCheck.WARNING,
                                tags=['url:https://github.com'])
        self.assertServiceCheck("http_check.ssl_cert.bad_url", status=AgentCheck.CRITICAL,
                                tags=['url:https://thereisnosuchlink.com'])

    @mock.patch('ssl.SSLSocket.getpeercert', return_value=FAKE_CERT)
    def test_mock_case(self, getpeercert_func):
        self.run_check(CONFIG_EXPIRED_SSL)
        # Overrides self.service_checks attribute when values are av
        # Needed for the HTTP headers
        self.service_checks = self.wait_for_async_service_checks(2)
        self.assertServiceCheck("http_check.ssl_cert.expired_cert", status=AgentCheck.CRITICAL,
                                tags=['url:https://github.com'])

# stdlibb
import time

# 3p
import mock
from nose.plugins.attrib import attr

# project
from config import AGENT_VERSION
from tests.checks.common import AgentCheckTest
from util import headers as agent_headers

RESULTS_TIMEOUT = 10

AGENT_CONFIG = {
    'version': AGENT_VERSION,
    'api_key': 'toto'
}

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
        'tags': ["foo:bar"]
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
        'url': 'https://google.com',
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

CONFIG_UNORMALIZED_INSTANCE_NAME = {
    'instances': [{
        'name': '_need-to__be_normalized-',
        'url': 'https://github.com',
        'timeout': 1,
        'check_certificate_expiration': True,
        'days_warning': 14
    },
    ]
}

CONFIG_HTTP_HEADERS = {
    'instances': [{
        'url': 'https://google.com',
        'name': 'UpService',
        'timeout': 1,
        'headers': {"X-Auth-Token": "SOME-AUTH-TOKEN"}
    }]
}


FAKE_CERT = {'notAfter': 'Apr 12 12:00:00 2006 GMT'}


@attr(requires='network')
class HTTPCheckTest(AgentCheckTest):
    CHECK_NAME = 'http_check'

    def tearDown(self):
        if self.check:
            self.check.stop()

    def wait_for_async(self, method, attribute, count):
        """
        Loop on `self.check.method` until `self.check.attribute >= count`.

        Raise after
        """
        i = 0
        while i < RESULTS_TIMEOUT:
            self.check._process_results()
            if len(getattr(self.check, attribute)) >= count:
                return getattr(self.check, method)()
            time.sleep(1)
            i += 1
        raise Exception("Didn't get the right count of service checks in time {0}"
                        .format(getattr(self.check, attribute)))

    def test_http_headers(self):
        """
        Headers format.
        """
        # Run the check
        self.load_check(CONFIG_HTTP_HEADERS, AGENT_CONFIG)

        url, username, password, http_response_status_code, timeout,\
            include_content, headers, response_time, content_match,\
            tags, ssl, ssl_expiration,\
            instance_ca_certs = self.check._load_conf(CONFIG_HTTP_HEADERS['instances'][0])

        self.assertEqual(headers["X-Auth-Token"], "SOME-AUTH-TOKEN", headers)
        expected_headers = agent_headers(AGENT_CONFIG).get('User-Agent')
        self.assertEqual(expected_headers, headers.get('User-Agent'), headers)

    def test_check(self):
        """
        Check coverage.
        """
        self.run_check(CONFIG)
        # Overrides self.service_checks attribute when values are available\
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 5)

        # HTTP connection error
        tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']

        self.assertServiceCheckCritical("http.can_connect", tags=tags)

        # Wrong HTTP response status code
        tags = ['url:http://httpbin.org/404', 'instance:http_error_status_code']
        self.assertServiceCheckCritical("http.can_connect", tags=tags)

        self.assertServiceCheckOK("http.can_connect", tags=tags, count=0)

        # HTTP response status code match
        tags = ['url:http://httpbin.org/404', 'instance:status_code_match', 'foo:bar']
        self.assertServiceCheckOK("http.can_connect", tags=tags)

        # Content match & mismatching
        tags = ['url:https://github.com', 'instance:cnt_mismatch']
        self.assertServiceCheckCritical("http.can_connect", tags=tags)
        self.assertServiceCheckOK("http.can_connect", tags=tags, count=0)
        tags = ['url:https://github.com', 'instance:cnt_match']
        self.assertServiceCheckOK("http.can_connect", tags=tags)

        self.coverage_report()

    def test_check_ssl(self):
        self.run_check(CONFIG_SSL_ONLY)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 6)
        tags = ['url:https://github.com', 'instance:good_cert']
        self.assertServiceCheckOK("http.can_connect", tags=tags)
        self.assertServiceCheckOK("http.ssl_cert", tags=tags)

        tags = ['url:https://google.com', 'instance:cert_exp_soon']
        self.assertServiceCheckOK("http.can_connect", tags=tags)
        self.assertServiceCheckWarning("http.ssl_cert", tags=tags)

        tags = ['url:https://thereisnosuchlink.com', 'instance:conn_error']
        self.assertServiceCheckCritical("http.can_connect", tags=tags)
        self.assertServiceCheckCritical("http.ssl_cert", tags=tags)

        self.coverage_report()

    @mock.patch('ssl.SSLSocket.getpeercert', return_value=FAKE_CERT)
    def test_mock_case(self, getpeercert_func):
        self.run_check(CONFIG_EXPIRED_SSL)
        # Overrides self.service_checks attribute when values are av
        # Needed for the HTTP headers
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 2)
        tags = ['url:https://github.com', 'instance:expired_cert']
        self.assertServiceCheckOK("http.can_connect", tags=tags)
        self.assertServiceCheckCritical("http.ssl_cert", tags=tags)
        self.coverage_report()

    def test_service_check_instance_name_normalization(self):
        """
        Service check `instance` tag value is normalized.

        Note: necessary to avoid mismatch and backward incompatiblity.
        """
        # Run the check
        self.run_check(CONFIG_UNORMALIZED_INSTANCE_NAME)

        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 2)

        # Assess instance name normalization
        tags = ['url:https://github.com', 'instance:need_to_be_normalized']
        self.assertServiceCheckOK("http.can_connect", tags=tags)
        self.assertServiceCheckOK("http.ssl_cert", tags=tags)

    def test_warnings(self):
        """
        Deprecate events usage for service checks.
        """
        self.run_check(CONFIG)

        # Overrides self.service_checks attribute when values are available\
        self.warnings = self.wait_for_async('get_warnings', 'warnings', 8)

        # Assess warnings
        self.assertWarning(
            "Skipping SSL certificate validation for "
            "https://github.com based on configuration",
            count=2
        )
        self.assertWarning(
            "Skipping SSL certificate validation for "
            "https://thereisnosuchlink.com based on configuration",
            count=1
        )
        self.assertWarning(
            "Using events for service checks is deprecated in "
            "favor of monitors and will be removed in future versions of the "
            "Datadog Agent.",
            count=5
        )

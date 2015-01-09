import unittest
from tests.common import load_check
from checks import AgentCheck
import time
import mock

RESULTS_TIMEOUT = 5

class HttpSslTestCase(unittest.TestCase):

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
        raise Exception("Didn't get the right count of service checks in time {}".format(self.check.service_checks))

    def test_http_ssl(self):

        config = {
            'instances': [{
            'name' : 'Good Cert',
            'url' : 'https://github.com',
            'timeout' : 1,
            'check_certificate_expiration': True,
            'days_warning': 14
            },
            {
            'name' : 'Warning about Cert expiring',
            'url' : 'https://github.com',
            'timeout' : 1,
            'check_certificate_expiration': True,
            'days_warning': 9999
            },
            {
            'name' : 'Bad Url',
            'url' : 'https://thereisnosuchlink.com',
            'timeout' : 1,
            'check_certificate_expiration': True,
            'days_warning': 14
            }
            ]
        }

        # Needed for the HTTP headers
        agentConfig = {'version': '5.1'}
        self.check = load_check('http_check', config, agentConfig)

        # OK Status
        self.check.check(config['instances'][0])
        # status and ssl_cert
        sc = self.wait_for_async_service_checks(2)
        self.assertEqual(sc[1].get('status'), AgentCheck.OK)

        # Warning Status due to close to expiration date
        self.check.check(config['instances'][1])
        # status and ssl_cert
        sc = self.wait_for_async_service_checks(2)
        self.assertEqual(sc[1].get('status'), AgentCheck.WARNING)

        # Warning Status due to bad link
        self.check.check(config['instances'][2])
        # status and ssl_cert
        sc = self.wait_for_async_service_checks(2)
        self.assertEqual(sc[1].get('status'), AgentCheck.CRITICAL)

    fake_cert = {'notAfter': 'Apr 12 12:00:00 2006 GMT'}
    @mock.patch('ssl.SSLSocket.getpeercert', return_value=fake_cert)
    def test_mock_case(self, getpeercert_func):

        # assert getpeercert_func.called
        config = {
            'instances': [{
            'name' : 'Expired Cert',
            'url' : 'https://github.com',
            'timeout' : 1,
            'check_certificate_expiration': True,
            'days_warning': 14
            },
            ]
        }
        # Needed for the HTTP headers
        agentConfig = {'version' : '5.1'}
        self.check = load_check('http_check', config, agentConfig)

        #Failed Status
        self.check.check(config['instances'][0])
        time.sleep(2)
        self.check._process_results()
        service = self.check.get_service_checks()
        self.assertEqual(service[1].get('status'), AgentCheck.CRITICAL)

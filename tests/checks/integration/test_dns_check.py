# stdlib
import time
import mock

# 3p
from dns.rdatatype import UnknownRdatatype
from dns.resolver import Resolver, Timeout, NXDOMAIN
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

RESULTS_TIMEOUT = 10

CONFIG_SUCCESS = {
    'instances': [{
        'name': 'success',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1'
    }, {
        'name': 'cname',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1',
        'record_type': 'CNAME'
    }]
}

CONFIG_DEFAULT_TIMEOUT = {
    'init_config': {
        'default_timeout': 0.1
    },
    'instances': [{
        'name':'default_timeout',
        'hostname': 'www.example.org',
        'nameserver': '127.0.0.1'
    }]
}

CONFIG_INSTANCE_TIMEOUT = {
    'instances': [{
        'name': 'instance_timeout',
        'hostname': 'www.example.org',
        'timeout': 0.1,
        'nameserver': '127.0.0.1'
    }]
}

CONFIG_INVALID = [
    # invalid hostname
    ({'instances': [{
        'name': 'invalid_hostname',
        'hostname': 'example'}]}, NXDOMAIN),
    # invalid nameserver
    ({'instances': [{
        'name': 'invalid_nameserver',
        'hostname': 'www.example.org',
        'nameserver': '0.0.0.0'}]}, Timeout),
    # invalid record type
    ({'instances': [{
        'name': 'invalid_rcrd_type',
        'hostname': 'www.example.org',
        'record_type': 'FOO'}]}, UnknownRdatatype),
]

SERVICE_CHECK_NAME = 'dns.can_resolve'


class MockDNSAnswer:
    def __init__(self, address):
        self.rrset = MockDNSAnswer.MockRrset(address)

    class MockRrset:
        def __init__(self, address):
            self.items = [MockDNSAnswer.MockItem(address)]

    class MockItem:
        def __init__(self, address):
            self._address = address

        def to_text(self):
            return self._address


def success_query_mock(d_name, rdtype):
    if rdtype == 'A':
        return MockDNSAnswer('127.0.0.1')
    elif rdtype == 'CNAME':
        return MockDNSAnswer('alias.example.org')


@attr(requires='system')
class DNSCheckTest(AgentCheckTest):
    CHECK_NAME = 'dns_check'

    def tearDown(self):
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
        raise Exception("Didn't get the right count of service checks in time, {0}/{1} in {2}s: {3}"
                        .format(len(getattr(self.check, attribute)), count, i,
                                getattr(self.check, attribute)))

    @mock.patch.object(Resolver, 'query', side_effect=success_query_mock)
    def test_success(self, mocked_query):
        self.run_check(CONFIG_SUCCESS)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1)
        tags = ['instance:success', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
        self.assertServiceCheckOK(SERVICE_CHECK_NAME, tags=tags)
        tags = ['instance:cname', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:CNAME']
        self.assertServiceCheckOK(SERVICE_CHECK_NAME, tags=tags)
        self.coverage_report()

    @mock.patch.object(Resolver, 'query', side_effect=Timeout())
    def test_default_timeout(self, mocked_query):
        self.run_check(CONFIG_DEFAULT_TIMEOUT)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1)
        tags = ['instance:default_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
        self.assertServiceCheckCritical(SERVICE_CHECK_NAME, tags=tags)
        self.coverage_report()

    @mock.patch.object(Resolver, 'query', side_effect=Timeout())
    def test_instance_timeout(self, mocked_query):
        self.run_check(CONFIG_INSTANCE_TIMEOUT)
        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1)
        tags = ['instance:instance_timeout', 'resolved_hostname:www.example.org', 'nameserver:127.0.0.1', 'record_type:A']
        self.assertServiceCheckCritical(SERVICE_CHECK_NAME, tags=tags)
        self.coverage_report()

    def test_invalid_config(self):
        for config, exception_class in CONFIG_INVALID:
            self.run_check(config)
            # Overrides self.service_checks attribute when values are available
            self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', 1)
            self.assertRaises(exception_class)
            self.assertServiceCheckCritical(SERVICE_CHECK_NAME)
            self.coverage_report()

# stdlib
import mock

# 3p
from dns.rdatatype import UnknownRdatatype
from dns.resolver import Resolver, Timeout, NXDOMAIN

# project
from tests.checks.common import AgentCheckTest
from checks import AgentCheck


METRICS = [
    'dns.response_time'
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


class TestDns(AgentCheckTest):
    CHECK_NAME = 'dns_check'

    @mock.patch.object(Resolver, 'query', side_effect=success_query_mock)
    def test_success(self, mocked_query):
        config = {
            'instances': [{'hostname': 'www.example.org', 'nameserver': '127.0.0.1'}]
        }
        self.run_check(config)
        self.assertMetric('dns.response_time', count=1,
                          tags=['nameserver:127.0.0.1', 'resolved_hostname:www.example.org'])
        self.assertServiceCheck(SERVICE_CHECK_NAME, status=AgentCheck.OK,
                                tags=['resolved_hostname:www.example.org', 'nameserver:127.0.0.1'])
        self.coverage_report()

    @mock.patch.object(Resolver, 'query', side_effect=success_query_mock)
    def test_success_CNAME(self, mocked_query):
        config = {
            'instances': [{'hostname': 'www.example.org', 'nameserver': '127.0.0.1', 'record_type': 'CNAME'}]
        }
        self.run_check(config)
        self.assertMetric('dns.response_time', count=1,
                          tags=['nameserver:127.0.0.1', 'resolved_hostname:www.example.org'])
        self.assertServiceCheck(SERVICE_CHECK_NAME, status=AgentCheck.OK,
                                tags=['resolved_hostname:www.example.org', 'nameserver:127.0.0.1'])
        self.coverage_report()

    @mock.patch.object(Resolver, 'query', side_effect=Timeout())
    def test_timeout(self, mocked_query):
        configs = [
            # short default timeout
            {'init_config': {'default_timeout': 0.1},
             'instances': [{'hostname': 'www.example.org', 'nameserver': '127.0.0.1'}]},
            # short timeout
            {'instances': [{'hostname': 'www.example.org', 'timeout': 0.1, 'nameserver': '127.0.0.1'}]},
        ]
        for config in configs:
            self.assertRaises(
                Timeout,
                lambda: self.run_check(config)
            )
            self.assertEquals(len(self.metrics), 0)
            self.assertServiceCheck(SERVICE_CHECK_NAME, status=AgentCheck.CRITICAL,
                                    tags=['resolved_hostname:www.example.org', 'nameserver:127.0.0.1'])
            self.coverage_report()

    def test_invalid_config(self):
        configs = [
            # invalid hostname
            ({'instances': [{'hostname': 'example'}]}, NXDOMAIN),
            # invalid nameserver
            ({'instances': [{'hostname': 'www.example.org', 'nameserver': '0.0.0.0'}]}, Timeout),
            # invalid record type
            ({'instances': [{'hostname': 'www.example.org', 'record_type': 'FOO'}]}, UnknownRdatatype),
        ]
        for config, exception_class in configs:
            self.assertRaises(exception_class, self.run_check, config, force_reload=True)
            self.assertEquals(len(self.metrics), 0)
            self.assertServiceCheck(SERVICE_CHECK_NAME, status=AgentCheck.CRITICAL)
            self.coverage_report()

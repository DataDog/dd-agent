# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

INSTANCE = {
    'host': '.',
    'services': ['EventLog', 'Dnscache', 'NonExistingService'],
}

INVALID_HOST_INSTANCE = {
    'host': 'nonexistinghost',
    'services': ['EventLog'],
}


@attr('windows')
@attr(requires='windows')
class WindowsServiceTest(AgentCheckTest):
    CHECK_NAME = 'windows_service'

    SERVICE_CHECK_NAME = 'windows_service.state'

    def test_basic_check(self):
        self.run_check({'instances': [INSTANCE]})
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventLog'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:Dnscache'], count=1)
        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME, tags=['service:NonExistingService'], count=1)
        self.coverage_report()

    def test_invalid_host(self):
        self.run_check({'instances': [INVALID_HOST_INSTANCE]})
        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME, tags=['host:nonexistinghost', 'service:EventLog'], count=1)
        self.coverage_report()

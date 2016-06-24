# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

INSTANCE = {
    'host': '.',
    'services': ['EventLog', 'Dnscache', 'NonExistingService'],
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

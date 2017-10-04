from tests.checks.common import AgentCheckTest, Fixtures

def mock_config(fixture):
    return {'init_config': {}, 'instances' : [{'updates_file': Fixtures.file(fixture)}]}

class TestCheckAPT(AgentCheckTest):
    CHECK_NAME = 'apt'

    def test_no_updates(self):
        self.run_check(mock_config('updates-available.no-updates'))
        self.assertServiceCheckOK('apt.updates')
        self.assertMetric('apt.updates.packages', value=0)
        self.assertMetric('apt.updates.security', value=0)

    def test_package_updates(self):
        self.run_check(mock_config('updates-available.package-updates'))
        self.assertServiceCheckWarning('apt.updates')
        self.assertMetric('apt.updates.packages', value=15)
        self.assertMetric('apt.updates.security', value=0)

    def test_package_security_updates(self):
        self.run_check(mock_config('updates-available.security-updates'))
        self.assertServiceCheckCritical('apt.updates')
        self.assertMetric('apt.updates.packages', value=10)
        self.assertMetric('apt.updates.security', value=2)

    def test_single_update(self):
        self.run_check(mock_config('updates-available.single'))
        self.assertServiceCheckCritical('apt.updates')
        self.assertMetric('apt.updates.packages', value=1)
        self.assertMetric('apt.updates.security', value=1)

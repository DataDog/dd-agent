# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest, load_check

class TestFileUnit(AgentCheckTest):
    CHECK_NAME = 'file'

    def assert_tags(self, expected_tags, present_tags):
        for tag in expected_tags:
            self.assertTrue(tag in present_tags)

    def test_present_success(self):
        conf = {
            'init_config': {},
            'instances': [
                {'path': __file__, 'expect': 'present'}
            ]
        }
        self.check = load_check('file', conf, {})
        self.check.check(conf['instances'][0])
        metrics = self.check.get_metrics()
        self.assertTrue(len(metrics) == 1)
        metric = metrics[0]
        self.assertTrue(metric[2] > 0)
        self.assert_tags(['expected_status:present', 'actual_status:present'], metric[3]['tags'])

        service_checks = self.check.get_service_checks()
        self.assertTrue(service_checks[0]['status'] == AgentCheck.OK)
        self.assert_tags(['expected_status:present', 'actual_status:present'], service_checks[0]['tags'])


    def test_absent_failure(self):
        conf = {
            'init_config': {},
            'instances': [
                {'path': __file__, 'expect': 'absent'}
            ]
        }
        self.check = load_check('file', conf, {})
        self.check.check(conf['instances'][0])
        metrics = self.check.get_metrics()
        self.assertTrue(len(metrics) == 1)
        metric = metrics[0]
        self.assertTrue(metric[2] > 0)
        self.assert_tags(['expected_status:absent', 'actual_status:present'], metric[3]['tags'])

        service_checks = self.check.get_service_checks()
        self.assertTrue(service_checks[0]['status'] == AgentCheck.CRITICAL)
        self.assert_tags(['expected_status:absent', 'actual_status:present'], service_checks[0]['tags'])

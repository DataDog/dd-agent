import unittest
from nose.plugins.attrib import attr
from tests.common import load_check
from checks import AgentCheck

@attr(requires='gearman')
class GearmanTestCase(unittest.TestCase):

    def test_metrics(self):
        config = {
            'instances': [{
                'tags': ['first_tag', 'second_tag']
            }]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('gearmand', config, agentConfig)
        self.check.check(config['instances'][0])

        metrics = self.check.get_metrics()
        self.assertTrue(type(metrics) == type([]), metrics)
        self.assertTrue(len(metrics) == 4)
        self.assertTrue(len([k for k in metrics if "second_tag" in k[3]['tags']]) == 4)

    def test_service_checks(self):
        config = {
            'instances': [
                {'host': '127.0.0.1', 'port': 4730},
                {'host': '127.0.0.1', 'port': 4731}]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('gearmand', config, agentConfig)
        self.check.check(config['instances'][0])
        self.assertRaises(Exception, self.check.check, config['instances'][1])

        service_checks = self.check.get_service_checks()
        self.assertEqual(len(service_checks), 2)

        ok_svc_check = service_checks[0]
        self.assertEqual(ok_svc_check['check'], self.check.SERVICE_CHECK_NAME)
        self.assertEqual(ok_svc_check['status'], AgentCheck.OK)

        cr_svc_check = service_checks[1]
        self.assertEqual(cr_svc_check['check'], self.check.SERVICE_CHECK_NAME)
        self.assertEqual(cr_svc_check['status'], AgentCheck.CRITICAL)

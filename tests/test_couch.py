import unittest
from tests.common import load_check
from nose.plugins.attrib import attr
from checks import AgentCheck

@attr(requires='couchdb')
class CouchDBTestCase(unittest.TestCase):

    def test_metrics(self):
        config = {
            'instances': [{
                'server': 'http://localhost:5984',
            }]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('couch', config, agentConfig)

        self.check.check(config['instances'][0])

        metrics = self.check.get_metrics()
        self.assertTrue(type(metrics) == type([]), metrics)
        self.assertTrue(len(metrics) > 3)
        self.assertTrue(len([k for k in metrics if "instance:http://localhost:5984" in k[3]['tags']]) > 3)

    def test_service_checks(self):
        config = {
            'instances': [
                {'server': 'http://localhost:5984'},
                {'server': 'http://localhost:5985'}]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('couch', config, agentConfig)
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


import unittest
from tests.common import load_check
from nose.plugins.attrib import attr

@attr(requires='couchdb')
class CouchDBTestCase(unittest.TestCase):

    def testMetrics(self):

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

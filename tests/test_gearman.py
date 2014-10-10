import unittest
from nose.plugins.attrib import attr
from tests.common import load_check

@attr(requires='gearman')
class GearmanTestCase(unittest.TestCase):

    def testMetrics(self):

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

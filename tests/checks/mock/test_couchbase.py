from types import ListType
import unittest

from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest

from checks import AgentCheck
from tests.checks.common import load_check

@attr('couchbase')
class CouchbaseTestCase(unittest.TestCase):

    def setUp(self):
        self.config = {
            'instances': [{
                'server': 'http://localhost:8091',
                'user': 'Administrator',
                'password': 'password',
                'timeout': 0.1
            }]
        }
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }
        self.check = load_check('couchbase', self.config, self.agentConfig)

    def test_camel_case_to_joined_lower(self):
        test_pairs = {
            'camelCase' : 'camel_case',
            'FirstCapital' : 'first_capital',
            'joined_lower' : 'joined_lower',
            'joined_Upper1' : 'joined_upper1',
            'Joined_upper2' : 'joined_upper2',
            'Joined_Upper3' : 'joined_upper3',
            '_leading_Underscore' : 'leading_underscore',
            'Trailing_Underscore_' : 'trailing_underscore',
            'DOubleCAps' : 'd_ouble_c_aps',
            '@@@super--$$-Funky__$__$$%' : 'super_funky',
        }

        for test_input, expected_output in test_pairs.items():
            test_output = self.check.camel_case_to_joined_lower(test_input)
            self.assertEqual(test_output, expected_output,
                'Input was %s, expected output was %s, actual output was %s' % (test_input, expected_output, test_output))

    def test_metrics_casing(self):
        raise SkipTest("Skipped for now as it's hard to configure couchbase on travis")
        self.check.check(self.config['instances'][0])

        metrics = self.check.get_metrics()

        camel_cased_metrics = [
            u'couchbase.hdd.used_by_data',
            u'couchbase.ram.used_by_data',
            u'couchbase.ram.quota_total',
            u'couchbase.ram.quota_used',
        ]

        found_metrics = [k[0] for k in metrics if k[0] in camel_cased_metrics]
        self.assertEqual(found_metrics.sort(), camel_cased_metrics.sort())

    def test_metrics(self):
        raise SkipTest("Skipped for now as it's hard to configure couchbase on travis")
        self.check.check(self.config['instances'][0])

        metrics = self.check.get_metrics()

        self.assertTrue(isinstance(metrics, ListType))
        self.assertTrue(len(metrics) > 3)
        self.assertTrue(len([k for k in metrics if "instance:http://localhost:8091" in k[3]['tags']]) > 3)

        self.assertTrue(len([k for k in metrics if -1 != k[0].find('by_node')]) > 1, 'Unable to fund any per node metrics')
        self.assertTrue(len([k for k in metrics if -1 != k[0].find('by_bucket')]) > 1, 'Unable to fund any per node metrics')

    def test_service_check(self):
        try:
            self.check.check(self.config['instances'][0])
        except Exception:
            service_checks = self.check.get_service_checks()
            self.assertEqual(len(service_checks), 1)
            service_check = service_checks[0]
            self.assertEqual(service_check['check'], self.check.SERVICE_CHECK_NAME)
            self.assertEqual(service_check['status'], AgentCheck.CRITICAL)
        else:
            raise Exception('Couchbase check should have failed')

import unittest
import time
import os
from tests.common import load_check


class TestGoExpVar(unittest.TestCase):

    def setUp(self):
        self.agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.config = {
                "init_config": {
                    },
                "instances": [{
                    "expvar_url": os.path.join(os.path.dirname(__file__), "go_expvar", "expvar_output"),
                    "tags": ["optionaltag1", "optionaltag2"],
                    "metrics": [
                        {
                            "path":"memstats/PauseTotalNs",
                            "alias":"go_expvar.gc.pause",
                            "type":"rate"
                        },
                        {
                            "path":"memstats/BySize/1/Mallocs", # Contains list traversal and default values
                        },
                        {
                            "path":"random_walk",
                            "alias":"go_expvar.gauge1",
                            "type":"gauge"
                        }
                        ]
                    }]
                }

        self.check = load_check('go_expvar', self.config, self.agentConfig)

        def _get_data_mock(instance):
            with open(instance.get('expvar_url'), 'r') as go_output:
                return go_output.read()

        self.check._get_data = _get_data_mock

    def testGoExpVar(self):

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        # The rate is not here so only 2
        self.assertEqual(len(metrics), 2)
        metrics.sort(key=lambda x:x[0])
        self.assertEqual(metrics[0][0], 'go_expvar.gauge1')
        self.assertEqual(metrics[1][0], 'go_expvar.memstats.by_size.1.mallocs') # Verify the correct default value for metric name

        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rate
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        self.assertEqual(len(metrics) ,3)
        metrics.sort(key=lambda x:x[0])
        self.check.log.info(metrics)
        self.assertEqual(metrics[0][0], 'go_expvar.gauge1')
        self.assertEqual(metrics[1][0], 'go_expvar.gc.pause')
        self.assertEqual(metrics[2][0], 'go_expvar.memstats.by_size.1.mallocs') # Verify the correct default value for metric name
        for metric in metrics:
            tags = metric[3]['tags']
            self.assertEqual(len(tags), 2)
            self.assertTrue("optionaltag1" in tags)
            self.assertTrue("optionaltag2" in tags)

    def test_deepget(self):
        # Wildcard for dictkeys
        content = {
                    'a' : {
                        'one': 1,
                        'two': 2
                        },
                    'b': {
                        'three': 3,
                        'four':  4
                        }
                    }
        expected = [
                         (['a', 'two'], 2),
                         (['b', 'three'], 3),
                    ]
        results = self.check.deep_get(content,['.','t.*'], [])
        self.assertEqual(sorted(results), sorted(expected))

        expected = [(['a', 'one'], 1)]
        results = self.check.deep_get(content, ['.','one'], [])
        self.assertEqual(results, expected)

        # Wildcard for list index
        content = { 'list':
                    [ {'timestamp': 10,
                         'value':     5},
                      {'timestamp': 10,
                       'value':     10},
                      {'timestamp': 10,
                       'value':     20}
                      ]
                    }
        expected = [ (['list','0','value'], 5),
                     (['list','1','value'], 10),
                     (['list','2','value'], 20)]

        results = self.check.deep_get(content, ['list','.*','value'], [])
        self.assertEqual(sorted(results), sorted(expected))

if __name__ == "__main__":
    unittest.main()

import unittest
import time
import os
from tests.common import load_check
import simplejson as json


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
                            "path":"memstats/BySize/1/Mallocs", # Contains list traversal and default values
                        },
                        {
                            "path":"memstats/PauseTotalNs",
                            "alias":"go_expvar.gc.pause",
                            "type":"rate"
                        },
                        {
                            "path":"random_walk",
                            "alias":"go_expvar.gauge1",
                            "type":"gauge",
                            "tags": ["metric_tag1:metric_value1", "metric_tag2:metric_value2"]
                        }
                        ]
                    }]
                }

        self.check = load_check('go_expvar', self.config, self.agentConfig)

        def _get_data_mock(url):
            with open(url, 'r') as go_output:
                return json.loads(go_output.read())

        self.check._get_data = _get_data_mock

    def _assert_metric_number(self, metrics, metric_name, count):
        self.assertEqual(len([m for m in metrics if m[0] == metric_name]), count, metrics)

    def testGoExpVar(self):

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        # The rate is not here so only 2
        self.assertEqual(len(metrics), 15, metrics)
        self._assert_metric_number(metrics, 'go_expvar.gauge1', 1)
        self._assert_metric_number(metrics, 'go_expvar.memstats.by_size.1.mallocs', 1)

        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rate
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        self.assertEqual(len(metrics) ,16, metrics)
        self._assert_metric_number(metrics, 'go_expvar.gauge1', 1)
        self._assert_metric_number(metrics, 'go_expvar.gc.pause', 1)
        self._assert_metric_number(metrics, 'go_expvar.memstats.by_size.1.mallocs', 1)

        tags_count = {
            "go_expvar.memstats.total_alloc" : 3,
            "go_expvar.memstats.heap_inuse" : 3,
            "go_expvar.memstats.alloc" : 3,
            "go_expvar.memstats.mallocs" : 3,
            "go_expvar.memstats.heap_objects" : 3,
            "go_expvar.memstats.by_size.1.mallocs" : 3,
            "go_expvar.memstats.heap_released" : 3,
            "go_expvar.memstats.pause_total_ns" : 3,
            "go_expvar.memstats.heap_alloc" : 3,
            "go_expvar.gc.pause" : 4,
            "go_expvar.memstats.heap_sys" : 3,
            "go_expvar.memstats.lookups" : 3,
            "go_expvar.memstats.num_gc" : 3,
            "go_expvar.memstats.frees" : 3,
            "go_expvar.memstats.heap_idle" : 3,
            "go_expvar.gauge1" : 6}

        for metric in metrics:
            tags = metric[3]['tags']
            self.assertEqual(len(tags), tags_count[metric[0]], metric)
            self.assertTrue("optionaltag1" in tags)
            self.assertTrue("optionaltag2" in tags)
            self.assertTrue("expvar_url:%s" % self.config['instances'][0]['expvar_url'] in tags)

            if metric[0] == "go_expvar.gauge1":
                self.assertTrue("metric_tag1:metric_value1" in tags, metric)
                self.assertTrue("metric_tag2:metric_value2" in tags, metric)




        # Verify that the max number of metrics is respected
        self.config['instances'][0]['max_returned_metrics'] = 1
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()
        self.assertEqual(len(metrics), 1)

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

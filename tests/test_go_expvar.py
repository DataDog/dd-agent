import unittest
import time
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
                    "expvar_url": "http://localhost/expvar_output", # piggyback on the fact that the other tests run a webserver
                    "tags": ["optionaltag1", "optionaltag2"],
                    "metrics": [
                        {
                            "path":"memstats/PauseTotalNs",
                            "name":"gc.pause",
                            "type":"rate"
                        },
                        {
                            "path":"memstats/BySize/1/Mallocs", # Contains list traversal and default values
                        },
                        {
                            "path":"random_walk",
                            "name":"gauge1",
                            "type":"gauge"
                        }
                        ]
                    }]
                }

        self.check = load_check('go_expvar', self.config, self.agentConfig)

    def testGoExpVar(self):

        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        # The rate is not here so only 2
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0][0], 'go_expvar.Mallocs')
        self.assertEqual(metrics[1][0], 'go_expvar.gauge1') # Verify the correct default value for metric name

        # Sleep for 1 second so the rate interval >=1
        time.sleep(1)
        # Run the check again so we get the rate
        self.check.check(self.config['instances'][0])
        metrics = self.check.get_metrics()

        self.assertEqual(len(metrics) ,3)
        self.assertEqual(metrics[0][0], 'go_expvar.gc.pause')
        self.assertEqual(metrics[0][3]['type'],'rate')
        self.assertEqual(metrics[1][0], 'go_expvar.Mallocs') # Verify the correct default value for metric name
        self.assertEqual(metrics[1][3]['type'],'gauge')
        self.assertEqual(metrics[2][0], 'go_expvar.gauge1')
        self.assertEqual(metrics[2][3]['type'],'gauge')
        for metric in metrics:
            tags = metric[3]['tags']
            self.assertEqual(len(tags), 2)
            self.assertTrue("optionaltag1" in tags)
            self.assertTrue("optionaltag2" in tags)

if __name__ == "__main__":
    unittest.main()

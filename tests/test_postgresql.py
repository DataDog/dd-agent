import unittest
from tests.common import load_check
import time

class TestPostgres(unittest.TestCase):

    def testChecks(self):

        config = {
            'instances': [
                {
                'host': 'localhost',
                'port': 5432,
                'username': 'datadog',
                'password': 'datadog',
                'dbname': 'datadog_test',
                'relations': ['persons'],
                }
            ]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('postgres', config, agentConfig)

        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.connections']) == 1, metrics)
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.dead_rows']) == 1, metrics)
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.live_rows']) == 1, metrics)
        self.assertTrue(4 <= len(metrics) <= 6, metrics)
        self.assertTrue(4 <= len([m for m in metrics if 'db:datadog_test' in str(m[3]['tags']) ]) <= 4, metrics)
        self.assertTrue(len([m for m in metrics if 'table:persons' in str(m[3]['tags'])]) == 2, metrics)

        time.sleep(1)
        self.check.run()
        metrics = self.check.get_metrics()

        self.assertTrue(len(metrics) == 18, metrics)
        self.assertTrue(len([m for m in metrics if 'db:datadog_test' in str(m[3]['tags']) ]) == 18, metrics)
        self.assertTrue(len([m for m in metrics if 'table:persons' in str(m[3]['tags']) ]) == 8, metrics)

if __name__ == '__main__':
    unittest.main()

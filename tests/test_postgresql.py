import unittest
from tests.common import load_check
import time

class TestMySql(unittest.TestCase):

    def testChecks(self):
        agentConfig = { 
            'version': '0.1',
            'api_key': 'toto' }

        # Initialize the check from checks.d
        c = load_check('mysql', {'init_config': {}, 'instances': [{
            'host': 'localhost',
            'port': 5432,
            'username': 'datadog',
            'password': 'datadog',
            'dbname': 'datadog_test',
            'relations': ['persons'],
            }]}, agentConfig)
        conf = c.parse_agent_config(agentConfig)
        self.check = load_check('postgres', conf, agentConfig)

        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.connection']) == 1, metrics)
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.dead_rows']) == 1, metrics)
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.live_rows']) == 1, metrics)
        self.assertTrue(3 <= len(metrics) <= 4, metrics)
        self.assertTrue(3 <= len([m for m in metrics if 'db:datadog_test' in str(m[3]['tags']) ]) <= 4, metrics)
        self.assertTrue(len([m for m in metrics if 'table:persons' in str(m[3]['tags'])]) == 2, metrics)

        time.sleep(1)
        self.check.run()
        metrics = self.check.get_metrics()

        self.assertTrue(23 <= len(metrics) <= 26, metrics)

if __name__ == '__main__':
    unittest.main()

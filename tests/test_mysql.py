import unittest
from tests.common import load_check
import time

class TestMySql(unittest.TestCase):
    def setUp(self):
        # This should run on pre-2.7 python so no skiptest
        self.skip = False
        try:
            import pymysql
        except ImportError:
            self.skip = True

    def testChecks(self):
        if not self.skip:
            agentConfig = { 'mysql_server': 'localhost',
                'mysql_user': "dog",
                'mysql_pass': "dog",
                'version': '0.1',
                'api_key': 'toto' }

            # Initialize the check from checks.d
            c = load_check('mysql', {'init_config': {}, 'instances': {}}, agentConfig)
            conf = c.parse_agent_config(agentConfig)
            self.check = load_check('mysql', conf, agentConfig)

            self.check.run()
            metrics = self.check.get_metrics()
            self.assertTrue(len(metrics) >= 8, metrics)
            time.sleep(1)
            self.check.run()
            metrics = self.check.get_metrics()
            self.assertTrue(len(metrics) >= 16, metrics)
        
if __name__ == '__main__':
    unittest.main()

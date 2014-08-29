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
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.bgwriter.sync_time']) == 1, metrics)
        self.assertTrue(len([m for m in metrics if m[0] == 'postgresql.locks']) == 1, metrics)
        self.assertTrue(4 <= len(metrics) <= 6, metrics)
        self.assertTrue(4 <= len([m for m in metrics if 'db:datadog_test' in str(m[3]['tags']) ]) <= 5, metrics)
        self.assertTrue(len([m for m in metrics if 'table:persons' in str(m[3]['tags'])]) == 2, metrics)

        # Service checks
        service_checks = self.check.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == "postgres.can_connect"]), 1, service_checks)
        # Assert that all service checks have the proper tags: host, port and db
        self.assertEquals(len([sc for sc in service_checks if "host:localhost" in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "port:%s" % config['instances'][0]['port'] in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "db:%s" % config['instances'][0]['dbname'] in sc['tags']]), service_checks_count, service_checks)

        time.sleep(1)
        self.check.run()
        metrics = self.check.get_metrics()

        self.assertTrue(len(metrics) == 20, metrics)
        self.assertTrue(len([m for m in metrics if 'db:datadog_test' in str(m[3]['tags']) ]) == 20, metrics)
        self.assertTrue(len([m for m in metrics if 'table:persons' in str(m[3]['tags']) ]) == 8, metrics)

if __name__ == '__main__':
    unittest.main()

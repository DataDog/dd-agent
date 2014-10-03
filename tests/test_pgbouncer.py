import unittest
from tests.common import load_check
import time
from pprint import pprint

class TestPgbouncer(unittest.TestCase):

    def testChecks(self):

        config = {
            'instances': [
                {
                'host': 'localhost',
                'port': 15433,
                'username': 'toto',
                'password': 'toto'
                }
            ]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        self.check = load_check('pgbouncer', config, agentConfig)

        self.check.run()
        metrics = self.check.get_metrics()
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.total_requests'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.total_received'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.total_sent'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.total_query_time'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.cl_active'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.cl_waiting'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.sv_active'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.sv_idle'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.sv_used'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.sv_tested'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.sv_login'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.pools.maxwait'])       >= 1, pprint(metrics))

        # Rate metrics, need 2 collection rounds
        time.sleep(1)
        metrics = self.check.get_metrics()
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.avg_req'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.avg_recv'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.avg_sent'])       >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'pgbouncer.stats.avg_query'])       >= 1, pprint(metrics))

        # Service checks
        service_checks = self.check.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == "pgbouncer.can_connect"]), 1, service_checks)
        # Assert that all service checks have the proper tags: host, port and db
        self.assertEquals(len([sc for sc in service_checks if "host:localhost" in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "port:%s" % config['instances'][0]['port'] in sc['tags']]), service_checks_count, service_checks)

if __name__ == '__main__':
    unittest.main()

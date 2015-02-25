import unittest
from tests.common import load_check, AgentCheckTest

from nose.plugins.attrib import attr

import time
from pprint import pprint

@attr(requires='postgres')
class TestPostgres(AgentCheckTest):

    CHECK_NAME = "postgres"

    def test_checks(self):
        host = 'localhost'
        port = 15432
        dbname = 'datadog_test'

        config = {
            'instances': [
                {
                'host': host,
                'port': port,
                'username': 'datadog',
                'password': 'datadog',
                'dbname': dbname,
                'relations': ['persons'],
                'custom_metrics': [
                    {
                        "descriptors": [
                            ("datname", "customdb")
                        ],
                        "metrics": {
                            "numbackends": ["custom.numbackends", "Gauge"],
                        },
                        "query": "SELECT datname, %s FROM pg_stat_database WHERE datname = 'datadog_test' LIMIT(1)", 
                        "relation": False,
                    }
                ]
                }
            ]
        }
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }


        self.check = load_check('postgres', config, agentConfig)

        self.check.run()

        # FIXME: Not great, should have a function like that available
        key = '%s:%s:%s' % (host, port, dbname)
        db = self.check.dbs[key]

        metrics = self.check.get_metrics()
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.connections'])               >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.dead_rows'])                 >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.live_rows'])                 >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.table_size'])                >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.index_size'])                >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.total_size'])                >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.max_connections'])           >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.percent_usage_connections']) >= 1, pprint(metrics))
        self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.db.count']) == 1, pprint(metrics))
        # Don't test for locks
        # self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.locks'])              >= 1, pprint(metrics))
        # Brittle tests
        # self.assertTrue(4 <= len(metrics) <= 6, metrics)
        # self.assertTrue(4 <= len([m for m in metrics if 'db:datadog_test' in str(m[3]['tags']) ]) <= 5, pprint(metrics))
        # self.assertTrue(len([m for m in metrics if 'table:persons' in str(m[3]['tags'])]) == 2, pprint(metrics))

        # Rate metrics, need 2 collection rounds
        time.sleep(1)
        self.check.run()
        metrics = self.check.get_metrics()

        exp_metrics = 39
        exp_db_tagged_metrics = 26

        if self.check._is_9_2_or_above(key, db):
            self.assertTrue(len([m for m in metrics if m[0] == u'postgresql.bgwriter.sync_time']) >= 1, pprint(metrics))
        else:
            if not self.check._is_9_1_or_above(key, db):
                # No replication metric
                exp_metrics -= 1

            # Not all bgw metrics
            exp_metrics -= 2
            # Not all common metrics see NEWER_92_METRICS
            exp_metrics -= 3
            exp_db_tagged_metrics -= 3

        # Service checks
        service_checks = self.check.get_service_checks()
        service_checks_count = len(service_checks)
        self.assertTrue(type(service_checks) == type([]))
        self.assertTrue(service_checks_count > 0)
        self.assertEquals(len([sc for sc in service_checks if sc['check'] == "postgres.can_connect"]), 2, service_checks)
        # Assert that all service checks have the proper tags: host, port and db
        self.assertEquals(len([sc for sc in service_checks if "host:localhost" in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "port:%s" % config['instances'][0]['port'] in sc['tags']]), service_checks_count, service_checks)
        self.assertEquals(len([sc for sc in service_checks if "db:%s" % config['instances'][0]['dbname'] in sc['tags']]), service_checks_count, service_checks)

        time.sleep(1)
        self.check.run()
        metrics = self.check.get_metrics()

        self.assertEquals(len(metrics), exp_metrics, metrics)
        self.assertEquals(len([m for m in metrics if 'db:datadog_test' in str(m[3].get('tags', []))]), exp_db_tagged_metrics, metrics)
        self.assertEquals(len([m for m in metrics if 'table:persons' in str(m[3].get('tags', [])) ]), 11, metrics)

        self.metrics = metrics
        self.assertMetric("custom.numbackends")

if __name__ == '__main__':
    unittest.main()

# stdlib
import time
from types import ListType

# 3p
from nose.plugins.attrib import attr
try:
    import psycopg2 as pg
except ImportError:
    pg = None

# project
from tests.checks.common import AgentCheckTest


@attr(requires='pgbouncer')
class TestPgbouncer(AgentCheckTest):
    CHECK_NAME = 'pgbouncer'

    def test_checks(self):
        config = {
            'init_config': {},
            'instances': [
                {
                    'host': 'localhost',
                    'port': 15433,
                    'username': 'datadog',
                    'password': 'datadog'
                }
            ]
        }

        self.run_check(config)

        self.assertMetric('pgbouncer.pools.cl_active')
        self.assertMetric('pgbouncer.pools.cl_waiting')
        self.assertMetric('pgbouncer.pools.sv_active')
        self.assertMetric('pgbouncer.pools.sv_idle')
        self.assertMetric('pgbouncer.pools.sv_used')
        self.assertMetric('pgbouncer.pools.sv_tested')
        self.assertMetric('pgbouncer.pools.sv_login')
        self.assertMetric('pgbouncer.pools.maxwait')

        self.assertMetric('pgbouncer.stats.total_query_time')
        self.assertMetric('pgbouncer.stats.avg_req')
        self.assertMetric('pgbouncer.stats.avg_recv')
        self.assertMetric('pgbouncer.stats.avg_sent')
        self.assertMetric('pgbouncer.stats.avg_query')
        # Rate metrics, need 2 collection rounds
        try:
            connection = pg.connect(
                host='localhost',
                port='15433',
                user='datadog',
                password='datadog',
                database='datadog_test')
            connection.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = connection.cursor()
            cur.execute('SELECT * FROM persons;')
        except Exception:
            pass
        time.sleep(1)
        self.run_check(config)
        self.assertMetric('pgbouncer.stats.requests_per_second')
        self.assertMetric('pgbouncer.stats.bytes_received_per_second')
        self.assertMetric('pgbouncer.stats.bytes_sent_per_second')

        # Service checks
        service_checks_count = len(self.service_checks)
        self.assertTrue(isinstance(self.service_checks, ListType))
        self.assertTrue(service_checks_count > 0)
        self.assertServiceCheckOK(
            'pgbouncer.can_connect',
            tags=['host:localhost', 'port:15433', 'db:pgbouncer'],
            count=service_checks_count)

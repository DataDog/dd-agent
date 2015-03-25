# stdlib
import time

# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.common import AgentCheckTest


@attr(requires='postgres')
class TestPostgres(AgentCheckTest):
    CHECK_NAME = 'postgres'

    def test_checks(self):
        host = 'localhost'
        port = 15432
        dbname = 'datadog_test'

        instances = [
            {
                'host': host,
                'port': port,
                'username': 'datadog',
                'password': 'datadog',
                'dbname': dbname,
                'relations': ['persons'],
                'custom_metrics': [{
                    'descriptors': [('datname', 'customdb')],
                    'metrics': {
                        'numbackends': ['custom.numbackends', 'Gauge'],
                    },
                    'query': "SELECT datname, %s FROM pg_stat_database WHERE datname = 'datadog_test' LIMIT(1)",
                    'relation': False,
                }]
            },
            {
                'host': host,
                'port': port,
                'username': 'datadog',
                'password': 'datadog',
                'dbname': 'dogs',
                'relations': ['breed', 'kennel']
            }
        ]

        self.run_check(dict(instances=instances))
        # Rate metrics, need 2 collection rounds
        time.sleep(1)
        self.run_check(dict(instances=instances))

        # Useful to get server version
        # FIXME: Not great, should have a function like that available
        key = (host, port, dbname)
        db = self.check.dbs[key]

        # Testing DB_METRICS scope
        COMMON_METRICS = [
            'postgresql.connections',
            'postgresql.commits',
            'postgresql.rollbacks',
            'postgresql.disk_read',
            'postgresql.buffer_hit',
            'postgresql.rows_returned',
            'postgresql.rows_fetched',
            'postgresql.rows_inserted',
            'postgresql.rows_updated',
            'postgresql.rows_deleted',
            'postgresql.database_size',
        ]

        for mname in COMMON_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=1, tags=['db:%s' % db])

        NEWER_92_METRICS = [
            'postgresql.deadlocks',
            'postgresql.temp_bytes',
            'postgresql.temp_files',
        ]

        if self.check._is_9_2_or_above(key, db):
            for mname in NEWER_92_METRICS:
                for db in ('datadog_test', 'dogs'):
                    self.assertMetric(mname, count=1, tags=['db:%s' % db])

        # Testing BGW_METRICS scope
        COMMON_BGW_METRICS = [
            'postgresql.bgwriter.checkpoints_timed',
            'postgresql.bgwriter.checkpoints_requested',
            'postgresql.bgwriter.buffers_checkpoint',
            'postgresql.bgwriter.buffers_clean',
            'postgresql.bgwriter.maxwritten_clean',
            'postgresql.bgwriter.buffers_backend',
            'postgresql.bgwriter.buffers_alloc',
        ]

        for mname in COMMON_BGW_METRICS:
            self.assertMetric(mname, count=1)

        NEWER_91_BGW_METRICS = [
            'postgresql.bgwriter.buffers_backend_fsync',
        ]

        if self.check._is_9_1_or_above(key, db):
            for mname in NEWER_91_BGW_METRICS:
                self.assertMetric(mname, count=1)

        NEWER_92_BGW_METRICS = [
            'postgresql.bgwriter.write_time',
            'postgresql.bgwriter.sync_time',
        ]

        if self.check._is_9_2_or_above(key, db):
            for mname in NEWER_92_BGW_METRICS:
                self.assertMetric(mname, count=1)

        # FIXME: Test postgresql.locks

        # Relation specific metrics
        RELATION_METRICS = [
            'postgresql.seq_scans',
            'postgresql.seq_rows_read',
            'postgresql.index_scans',
            'postgresql.index_rows_fetched',
            'postgresql.rows_inserted',
            'postgresql.rows_updated',
            'postgresql.rows_deleted',
            'postgresql.rows_hot_updated',
            'postgresql.live_rows',
            'postgresql.dead_rows',
        ]

        SIZE_METRICS = [
            'postgresql.table_size',
            'postgresql.index_size',
            'postgresql.total_size',
        ]

        STATIO_METRICS = [
            'postgresql.heap_blocks_read',
            'postgresql.heap_blocks_hit',
            'postgresql.index_blocks_read',
            'postgresql.index_blocks_hit',
            'postgresql.toast_blocks_read',
            'postgresql.toast_blocks_hit',
            'postgresql.toast_index_blocks_read',
            'postgresql.toast_index_blocks_hit',
        ]

        for inst in instances:
            for rel in inst.get('relations', []):
                expected_tags = ['db:%s' % inst['dbname'], 'table:%s' % rel]
                for mname in RELATION_METRICS:
                    count = 1
                    # We only build a test index and stimulate it on breed
                    # in the dogs DB, so the other index metrics shouldn't be
                    # here.
                    if 'index' in mname and rel != 'breed':
                        count = 0
                    self.assertMetric(mname, count=count, tags=expected_tags)

                for mname in SIZE_METRICS:
                    self.assertMetric(mname, count=1, tags=expected_tags)

                for mname in STATIO_METRICS:
                    at_least = None
                    count = 1
                    if '.index' in mname and rel != 'breed':
                        count = 0
                    # FIXME: toast are not reliable, need to do some more setup
                    # to get some values here I guess
                    if 'toast' in mname:
                        at_least = 0  # how to set easily a flaky metric, w/o impacting coverage
                        count = None
                    self.assertMetric(mname, count=count, at_least=at_least, tags=expected_tags)

        # Index metrics
        IDX_METRICS = [
            'postgresql.index_scans',
            'postgresql.index_rows_read',
            'postgresql.index_rows_fetched',
        ]

        # we have a single index defined!
        expected_tags = ['db:dogs', 'table:breed', 'index:breed_names']
        for mname in IDX_METRICS:
            self.assertMetric(mname, count=1, tags=expected_tags)

        # instance connection metrics
        CONNECTION_METRICS = [
            'postgresql.max_connections',
            'postgresql.percent_usage_connections',
        ]
        for mname in CONNECTION_METRICS:
            self.assertMetric(mname, count=1)

        # db level connections
        for inst in instances:
            expected_tags = ['db:%s' % inst['dbname']]
            self.assertMetric('postgresql.connections', count=1, tags=expected_tags)

        # By schema metrics
        self.assertMetric('postgresql.table.count', value=2, count=1, tags=['schema:public'])
        self.assertMetric('postgresql.db.count', value=2, count=1)

        # Our custom metric
        self.assertMetric('custom.numbackends', value=1, tags=['customdb:datadog_test'])

        # Test service checks
        self.assertServiceCheck('postgres.can_connect',
            count=1, status=AgentCheck.OK,
            tags=['host:localhost', 'port:15432', 'db:datadog_test']
        )
        self.assertServiceCheck('postgres.can_connect',
            count=1, status=AgentCheck.OK,
            tags=['host:localhost', 'port:15432', 'db:dogs']
        )

        self.coverage_report()
        return

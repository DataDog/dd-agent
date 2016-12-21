# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='postgres')
class TestPostgres(AgentCheckTest):
    CHECK_NAME = 'postgres'

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
    ]

    DATABASE_SIZE_METRICS = [
        'postgresql.database_size',
    ]

    NEWER_92_METRICS = [
        'postgresql.deadlocks',
        'postgresql.temp_bytes',
        'postgresql.temp_files',
    ]

    NEWER_91_BGW_METRICS = [
        'postgresql.bgwriter.buffers_backend_fsync',
    ]

    NEWER_92_BGW_METRICS = [
        'postgresql.bgwriter.write_time',
        'postgresql.bgwriter.sync_time',
    ]

    COMMON_BGW_METRICS = [
        'postgresql.bgwriter.checkpoints_timed',
        'postgresql.bgwriter.checkpoints_requested',
        'postgresql.bgwriter.buffers_checkpoint',
        'postgresql.bgwriter.buffers_clean',
        'postgresql.bgwriter.maxwritten_clean',
        'postgresql.bgwriter.buffers_backend',
        'postgresql.bgwriter.buffers_alloc',
    ]

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

    IDX_METRICS = [
        'postgresql.index_scans',
        'postgresql.index_rows_read',
        'postgresql.index_rows_fetched',
    ]

    CONNECTION_METRICS = [
        'postgresql.max_connections',
        'postgresql.percent_usage_connections',
    ]

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

        self.run_check_twice(dict(instances=instances), force_reload=True)

        # Useful to get server version
        # FIXME: Not great, should have a function like that available
        key = (host, port, dbname)
        db = self.check.dbs[key]

        # Testing DB_METRICS scope
        for mname in self.COMMON_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=1, tags=['db:%s' % db])

        for mname in self.DATABASE_SIZE_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=1, tags=['db:%s' % db])

        if self.check._is_9_2_or_above(key, db):
            for mname in self.NEWER_92_METRICS:
                for db in ('datadog_test', 'dogs'):
                    self.assertMetric(mname, count=1, tags=['db:%s' % db])

        # Testing BGW_METRICS scope
        for mname in self.COMMON_BGW_METRICS:
            self.assertMetric(mname, count=1)

        if self.check._is_9_1_or_above(key, db):
            for mname in self.NEWER_91_BGW_METRICS:
                self.assertMetric(mname, count=1)

        if self.check._is_9_2_or_above(key, db):
            for mname in self.NEWER_92_BGW_METRICS:
                self.assertMetric(mname, count=1)

        # FIXME: Test postgresql.locks

        # Relation specific metrics
        for inst in instances:
            for rel in inst.get('relations', []):
                expected_tags = ['db:%s' % inst['dbname'], 'table:%s' % rel]
                expected_rel_tags = ['db:%s' % inst['dbname'], 'table:%s' % rel, 'schema:public']
                for mname in self.RELATION_METRICS:
                    count = 1
                    # We only build a test index and stimulate it on breed
                    # in the dogs DB, so the other index metrics shouldn't be
                    # here.
                    if 'index' in mname and rel != 'breed':
                        count = 0
                    self.assertMetric(mname, count=count, tags=expected_rel_tags)

                for mname in self.SIZE_METRICS:
                    self.assertMetric(mname, count=1, tags=expected_tags)

                for mname in self.STATIO_METRICS:
                    at_least = None
                    count = 1
                    if '.index' in mname and rel != 'breed':
                        count = 0
                    # FIXME: toast are not reliable, need to do some more setup
                    # to get some values here I guess
                    if 'toast' in mname:
                        at_least = 0  # how to set easily a flaky metric, w/o impacting coverage
                        count = None
                    self.assertMetric(mname, count=count, at_least=at_least, tags=expected_rel_tags)

        # Index metrics
        # we have a single index defined!
        expected_tags = ['db:dogs', 'table:breed', 'index:breed_names', 'schema:public']
        for mname in self.IDX_METRICS:
            self.assertMetric(mname, count=1, tags=expected_tags)

        # instance connection metrics
        for mname in self.CONNECTION_METRICS:
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

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=2)

        self.coverage_report()
        from pg8000.core import Connection
        self.assertTrue(type(self.check.dbs[key]) == Connection)
        self.check.dbs[key].close()

    def test_psycopg2(self):
        host = 'localhost'
        port = 15432
        dbname = 'datadog_test'

        instances = [
            {
                'host': host,
                'port': port,
                'username': 'datadog',
                'password': 'datadog',
                'use_psycopg2': 'yes',
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

        self.run_check_twice(dict(instances=instances), force_reload=True)

        # Useful to get server version
        # FIXME: Not great, should have a function like that available
        key = (host, port, dbname)
        db = self.check.dbs[key]

        # Testing DB_METRICS scope
        for mname in self.COMMON_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=1, tags=['db:%s' % db])

        for mname in self.DATABASE_SIZE_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=1, tags=['db:%s' % db])

        if self.check._is_9_2_or_above(key, db):
            for mname in self.NEWER_92_METRICS:
                for db in ('datadog_test', 'dogs'):
                    self.assertMetric(mname, count=1, tags=['db:%s' % db])

        # Testing BGW_METRICS scope
        for mname in self.COMMON_BGW_METRICS:
            self.assertMetric(mname, count=1)

        if self.check._is_9_1_or_above(key, db):
            for mname in self.NEWER_91_BGW_METRICS:
                self.assertMetric(mname, count=1)

        if self.check._is_9_2_or_above(key, db):
            for mname in self.NEWER_92_BGW_METRICS:
                self.assertMetric(mname, count=1)

        # FIXME: Test postgresql.locks

        # Relation specific metrics
        for inst in instances:
            for rel in inst.get('relations', []):
                expected_tags = ['db:%s' % inst['dbname'], 'table:%s' % rel]
                expected_rel_tags = ['db:%s' % inst['dbname'], 'table:%s' % rel, 'schema:public']
                for mname in self.RELATION_METRICS:
                    count = 1
                    # We only build a test index and stimulate it on breed
                    # in the dogs DB, so the other index metrics shouldn't be
                    # here.
                    if 'index' in mname and rel != 'breed':
                        count = 0
                    self.assertMetric(mname, count=count, tags=expected_rel_tags)

                for mname in self.SIZE_METRICS:
                    self.assertMetric(mname, count=1, tags=expected_tags)

                for mname in self.STATIO_METRICS:
                    at_least = None
                    count = 1
                    if '.index' in mname and rel != 'breed':
                        count = 0
                    # FIXME: toast are not reliable, need to do some more setup
                    # to get some values here I guess
                    if 'toast' in mname:
                        at_least = 0  # how to set easily a flaky metric, w/o impacting coverage
                        count = None
                    self.assertMetric(mname, count=count, at_least=at_least, tags=expected_rel_tags)

        # Index metrics
        # we have a single index defined!
        expected_tags = ['db:dogs', 'table:breed', 'index:breed_names', 'schema:public']
        for mname in self.IDX_METRICS:
            self.assertMetric(mname, count=1, tags=expected_tags)

        # instance connection metrics
        for mname in self.CONNECTION_METRICS:
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

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=2)

        self.coverage_report()

        from psycopg2.extensions import connection
        self.assertTrue(type(self.check.dbs[key]) == connection)
        self.check.dbs[key].close()

    def test_collect_database_size_metrics_disabled(self):
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
                'collect_database_size_metrics': False
            },
            {
                'host': host,
                'port': port,
                'username': 'datadog',
                'password': 'datadog',
                'dbname': 'dogs',
                'collect_database_size_metrics': False
            }
        ]

        self.run_check_twice(dict(instances=instances), force_reload=True)

        # Useful to get server version
        # FIXME: Not great, should have a function like that available
        key = (host, port, dbname)
        db = self.check.dbs[key]

        for mname in self.COMMON_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=1, tags=['db:%s' % db])

        for mname in self.DATABASE_SIZE_METRICS:
            for db in ('datadog_test', 'dogs'):
                self.assertMetric(mname, count=0, tags=['db:%s' % db])

        if self.check._is_9_2_or_above(key, db):
            for mname in self.NEWER_92_METRICS:
                for db in ('datadog_test', 'dogs'):
                    self.assertMetric(mname, count=1, tags=['db:%s' % db])

        # Testing BGW_METRICS scope
        for mname in self.COMMON_BGW_METRICS:
            self.assertMetric(mname, count=1)

        if self.check._is_9_1_or_above(key, db):
            for mname in self.NEWER_91_BGW_METRICS:
                self.assertMetric(mname, count=1)

        if self.check._is_9_2_or_above(key, db):
            for mname in self.NEWER_92_BGW_METRICS:
                self.assertMetric(mname, count=1)

        # FIXME: Test postgresql.locks

        # instance connection metrics
        for mname in self.CONNECTION_METRICS:
            self.assertMetric(mname, count=1)

        # db level connections
        for inst in instances:
            expected_tags = ['db:%s' % inst['dbname']]
            self.assertMetric('postgresql.connections', count=1, tags=expected_tags)

        # By schema metrics
        self.assertMetric('postgresql.table.count', value=2, count=1, tags=['schema:public'])
        self.assertMetric('postgresql.db.count', value=2, count=1)

        # Test service checks
        self.assertServiceCheck('postgres.can_connect',
            count=1, status=AgentCheck.OK,
            tags=['host:localhost', 'port:15432', 'db:datadog_test']
        )
        self.assertServiceCheck('postgres.can_connect',
            count=1, status=AgentCheck.OK,
            tags=['host:localhost', 'port:15432', 'db:dogs']
        )

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=2)

        self.coverage_report()
        self.check.dbs[key].close()

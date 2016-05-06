# stdlib
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from utils.platform import Platform
from tests.checks.common import AgentCheckTest


@attr(requires='mysql')
class TestMySql(AgentCheckTest):
    CHECK_NAME = 'mysql'

    METRIC_TAGS = ['tag1', 'tag2']
    SC_TAGS = ['server:localhost', 'port:unix_socket']

    MYSQL_MINIMAL_CONFIG = [{
        'server': 'localhost',
        'user': 'dog',
        'pass': 'dog'
    }]

    MYSQL_COMPLEX_CONFIG = [{
        'server': 'localhost',
        'user': 'dog',
        'pass': 'dog',
        'options': {
            'replication': True,
            'extra_status_metrics': True,
            'extra_innodb_metrics': True,
            'extra_performance_metrics': True,
            'schema_size_metrics': True,
        },
        'tags': METRIC_TAGS,
        'queries': [
            {
                'query': "SELECT * from testdb.users where name='Alice' limit 1;",
                'metric': 'alice.age',
                'type': 'gauge',
                'field': 'age'
            },
            {
                'query': "SELECT * from testdb.users where name='Bob' limit 1;",
                'metric': 'bob.age',
                'type': 'gauge',
                'field': 'age'
            }
        ]
    }]

    CONNECTION_FAILURE = [{
        'server': 'localhost',
        'user': 'unknown',
        'pass': 'dog',
    }]

    STATUS_VARS = [
        # Command Metrics
        'mysql.performance.slow_queries',
        'mysql.performance.questions',
        'mysql.performance.queries',
        'mysql.performance.com_select',
        'mysql.performance.com_insert',
        'mysql.performance.com_update',
        'mysql.performance.com_delete',
        'mysql.performance.com_replace',
        'mysql.performance.com_load',
        'mysql.performance.com_insert_select',
        'mysql.performance.com_update_multi',
        'mysql.performance.com_delete_multi',
        'mysql.performance.com_replace_select',
        # Connection Metrics
        'mysql.net.connections',
        'mysql.net.max_connections',
        'mysql.net.aborted_clients',
        'mysql.net.aborted_connects',
        # Table Cache Metrics
        'mysql.performance.open_files',
        'mysql.performance.open_tables',
        # Network Metrics
        'mysql.performance.bytes_sent',
        'mysql.performance.bytes_received',
        # Query Cache Metrics
        'mysql.performance.qcache_hits',
        'mysql.performance.qcache_inserts',
        'mysql.performance.qcache_lowmem_prunes',
        # Table Lock Metrics
        'mysql.performance.table_locks_waited',
        'mysql.performance.table_locks_waited.rate',
        # Temporary Table Metrics
        'mysql.performance.created_tmp_tables',
        'mysql.performance.created_tmp_disk_tables',
        'mysql.performance.created_tmp_files',
        # Thread Metrics
        'mysql.performance.threads_connected',
        'mysql.performance.threads_running',
        # MyISAM Metrics
        'mysql.myisam.key_buffer_bytes_unflushed',
        'mysql.myisam.key_buffer_bytes_used',
        'mysql.myisam.key_read_requests',
        'mysql.myisam.key_reads',
        'mysql.myisam.key_write_requests',
        'mysql.myisam.key_writes',
    ]

    # Possibly from SHOW GLOBAL VARIABLES
    VARIABLES_VARS = [
        'mysql.myisam.key_buffer_size',
        'mysql.performance.key_cache_utilization',
        'mysql.net.max_connections_available',
        'mysql.performance.qcache_size',
        'mysql.performance.table_open_cache',
        'mysql.performance.thread_cache_size'
    ]

    INNODB_VARS = [
        # InnoDB metrics
        'mysql.innodb.data_reads',
        'mysql.innodb.data_writes',
        'mysql.innodb.os_log_fsyncs',
        'mysql.innodb.mutex_spin_waits',
        'mysql.innodb.mutex_spin_rounds',
        'mysql.innodb.mutex_os_waits',
        'mysql.innodb.row_lock_waits',
        'mysql.innodb.row_lock_time',
        'mysql.innodb.row_lock_current_waits',
        # 'mysql.innodb.current_row_locks', MariaDB status
        'mysql.innodb.buffer_pool_dirty',
        'mysql.innodb.buffer_pool_free',
        'mysql.innodb.buffer_pool_used',
        'mysql.innodb.buffer_pool_total',
        'mysql.innodb.buffer_pool_read_requests',
        'mysql.innodb.buffer_pool_reads',
        'mysql.innodb.buffer_pool_utilization',
    ]

    # Calculated from "SHOW MASTER LOGS;"
    BINLOG_VARS = [
        # 'mysql.binlog.disk_use', Only collected if log_bin is true
    ]

    SYSTEM_METRICS = [
        'mysql.performance.user_time',
        'mysql.performance.kernel_time',
        'mysql.performance.cpu_time',
    ]

    OPTIONAL_REPLICATION_METRICS = [
        'mysql.replication.slave_running',
        'mysql.replication.seconds_behind_master',
        'mysql.replication.slaves_connected',
    ]

    # Additional Vars found in "SHOW STATUS;"
    # Will collect if [FLAG NAME] is True
    OPTIONAL_STATUS_VARS = [
        'mysql.binlog.cache_disk_use',
        'mysql.binlog.cache_use',
        'mysql.performance.handler_commit',
        'mysql.performance.handler_delete',
        'mysql.performance.handler_prepare',
        'mysql.performance.handler_read_first',
        'mysql.performance.handler_read_key',
        'mysql.performance.handler_read_next',
        'mysql.performance.handler_read_prev',
        'mysql.performance.handler_read_rnd',
        'mysql.performance.handler_read_rnd_next',
        'mysql.performance.handler_rollback',
        'mysql.performance.handler_update',
        'mysql.performance.handler_write',
        'mysql.performance.opened_tables',
        'mysql.performance.qcache_total_blocks',
        'mysql.performance.qcache_free_blocks',
        'mysql.performance.qcache_free_memory',
        'mysql.performance.qcache_not_cached',
        'mysql.performance.qcache_queries_in_cache',
        'mysql.performance.select_full_join',
        'mysql.performance.select_full_range_join',
        'mysql.performance.select_range',
        'mysql.performance.select_range_check',
        'mysql.performance.select_scan',
        'mysql.performance.sort_merge_passes',
        'mysql.performance.sort_range',
        'mysql.performance.sort_rows',
        'mysql.performance.sort_scan',
        'mysql.performance.table_locks_immediate',
        'mysql.performance.table_locks_immediate.rate',
        'mysql.performance.threads_cached',
        'mysql.performance.threads_created'
    ]

    OPTIONAL_STATUS_VARS_5_6_6 = [
        'mysql.performance.table_cache_hits',
        'mysql.performance.table_cache_misses',

    ]

    # Will collect if [FLAG NAME] is True
    OPTIONAL_INNODB_VARS = [
        'mysql.innodb.active_transactions',
        'mysql.innodb.buffer_pool_data',
        'mysql.innodb.buffer_pool_pages_data',
        'mysql.innodb.buffer_pool_pages_dirty',
        'mysql.innodb.buffer_pool_pages_flushed',
        'mysql.innodb.buffer_pool_pages_free',
        'mysql.innodb.buffer_pool_pages_total',
        'mysql.innodb.buffer_pool_read_ahead',
        'mysql.innodb.buffer_pool_read_ahead_evicted',
        'mysql.innodb.buffer_pool_read_ahead_rnd',
        'mysql.innodb.buffer_pool_wait_free',
        'mysql.innodb.buffer_pool_write_requests',
        'mysql.innodb.checkpoint_age',
        'mysql.innodb.current_transactions',
        'mysql.innodb.data_fsyncs',
        'mysql.innodb.data_pending_fsyncs',
        'mysql.innodb.data_pending_reads',
        'mysql.innodb.data_pending_writes',
        'mysql.innodb.data_read',
        'mysql.innodb.data_written',
        'mysql.innodb.dblwr_pages_written',
        'mysql.innodb.dblwr_writes',
        'mysql.innodb.hash_index_cells_total',
        'mysql.innodb.hash_index_cells_used',
        'mysql.innodb.history_list_length',
        'mysql.innodb.ibuf_free_list',
        'mysql.innodb.ibuf_merged',
        'mysql.innodb.ibuf_merged_delete_marks',
        'mysql.innodb.ibuf_merged_deletes',
        'mysql.innodb.ibuf_merged_inserts',
        'mysql.innodb.ibuf_merges',
        'mysql.innodb.ibuf_segment_size',
        'mysql.innodb.ibuf_size',
        'mysql.innodb.lock_structs',
        'mysql.innodb.locked_tables',
        'mysql.innodb.locked_transactions',
        'mysql.innodb.log_waits',
        'mysql.innodb.log_write_requests',
        'mysql.innodb.log_writes',
        'mysql.innodb.lsn_current',
        'mysql.innodb.lsn_flushed',
        'mysql.innodb.lsn_last_checkpoint',
        'mysql.innodb.mem_adaptive_hash',
        'mysql.innodb.mem_additional_pool',
        'mysql.innodb.mem_dictionary',
        'mysql.innodb.mem_file_system',
        'mysql.innodb.mem_lock_system',
        'mysql.innodb.mem_page_hash',
        'mysql.innodb.mem_recovery_system',
        'mysql.innodb.mem_thread_hash',
        'mysql.innodb.mem_total',
        'mysql.innodb.os_file_fsyncs',
        'mysql.innodb.os_file_reads',
        'mysql.innodb.os_file_writes',
        'mysql.innodb.os_log_pending_fsyncs',
        'mysql.innodb.os_log_pending_writes',
        'mysql.innodb.os_log_written',
        'mysql.innodb.pages_created',
        'mysql.innodb.pages_read',
        'mysql.innodb.pages_written',
        'mysql.innodb.pending_aio_log_ios',
        'mysql.innodb.pending_aio_sync_ios',
        'mysql.innodb.pending_buffer_pool_flushes',
        'mysql.innodb.pending_checkpoint_writes',
        'mysql.innodb.pending_ibuf_aio_reads',
        'mysql.innodb.pending_log_flushes',
        'mysql.innodb.pending_log_writes',
        'mysql.innodb.pending_normal_aio_reads',
        'mysql.innodb.pending_normal_aio_writes',
        'mysql.innodb.queries_inside',
        'mysql.innodb.queries_queued',
        'mysql.innodb.read_views',
        'mysql.innodb.rows_deleted',
        'mysql.innodb.rows_inserted',
        'mysql.innodb.rows_read',
        'mysql.innodb.rows_updated',
        'mysql.innodb.s_lock_os_waits',
        'mysql.innodb.s_lock_spin_rounds',
        'mysql.innodb.s_lock_spin_waits',
        'mysql.innodb.semaphore_wait_time',
        'mysql.innodb.semaphore_waits',
        'mysql.innodb.tables_in_use',
        'mysql.innodb.x_lock_os_waits',
        'mysql.innodb.x_lock_spin_rounds',
        'mysql.innodb.x_lock_spin_waits',
    ]

    PERFORMANCE_VARS = [
        'mysql.performance.query_run_time.avg',
        'mysql.performance.digest_95th_percentile.avg_us',
    ]

    SCHEMA_VARS = [
        'mysql.info.schema.size'
    ]

    SYNTHETIC_VARS = [
        'mysql.performance.qcache.utilization',
        'mysql.performance.qcache.utilization.instant',
    ]

    def _test_optional_metrics(self, optional_metrics, at_least):
        """
        Check optional metrics - there should be at least `at_least` matches
        """

        before = len(filter(lambda m: m[3].get('tested'), self.metrics))

        for mname in optional_metrics:
            self.assertMetric(mname, tags=self.METRIC_TAGS, at_least=0)

        # Compute match rate
        after = len(filter(lambda m: m[3].get('tested'), self.metrics))

        self.assertTrue(after - before > at_least)

    def test_minimal_config(self):
        config = {'instances': self.MYSQL_MINIMAL_CONFIG}
        self.run_check_twice(config)

        # Test service check
        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS, count=1)

        # Test metrics
        testable_metrics = (self.STATUS_VARS + self.VARIABLES_VARS + self.INNODB_VARS
                            + self.BINLOG_VARS + self.SYSTEM_METRICS + self.SYNTHETIC_VARS)

        for mname in testable_metrics:
            self.assertMetric(mname, count=1)

    def test_complex_config(self):
        config = {'instances': self.MYSQL_COMPLEX_CONFIG}
        self.run_check_twice(config)

        # Test service check
        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS, count=1)

        # Travis MySQL not running replication - FIX in flavored test.
        self.assertServiceCheck('mysql.replication.slave_running', status=AgentCheck.CRITICAL,
                                tags=self.SC_TAGS, count=1)

        ver = map(lambda x: int(x), self.service_metadata[0]['version'].split("."))
        ver = tuple(ver)

        testable_metrics = (self.STATUS_VARS + self.VARIABLES_VARS + self.INNODB_VARS
                            + self.BINLOG_VARS + self.SYSTEM_METRICS + self.SCHEMA_VARS + self.SYNTHETIC_VARS)

        if ver >= (5, 6, 0):
            testable_metrics.extend(self.PERFORMANCE_VARS)

        # Test metrics
        for mname in testable_metrics:
            # These two are currently not guaranteed outside of a Linux
            # environment.
            if mname == 'mysql.performance.user_time' and not Platform.is_linux():
                continue
            if mname == 'mysql.performance.kernel_time' and not Platform.is_linux():
                continue
            if mname == 'mysql.performance.cpu_time' and Platform.is_windows():
                continue

            if mname == 'mysql.performance.query_run_time.avg':
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
            elif mname == 'mysql.info.schema.size':
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:testdb'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:information_schema'], count=1)
                self.assertMetric(mname, tags=self.METRIC_TAGS+['schema:performance_schema'], count=1)
            else:
                self.assertMetric(mname, tags=self.METRIC_TAGS, count=1)

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=1)

        # test custom query metrics
        self.assertMetric('alice.age', value=25)
        self.assertMetric('bob.age', value=20)

        # test optional metrics
        self._test_optional_metrics((self.OPTIONAL_REPLICATION_METRICS
                                     + self.OPTIONAL_INNODB_VARS
                                     + self.OPTIONAL_STATUS_VARS
                                     + self.OPTIONAL_STATUS_VARS_5_6_6), 1)

        # Raises when coverage < 100%
        self.coverage_report()

    def test_connection_failure(self):
        """
        Service check reports connection failure
        """
        config = {'instances': self.CONNECTION_FAILURE}

        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )

        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.CRITICAL,
                                tags=self.SC_TAGS, count=1)
        self.coverage_report()

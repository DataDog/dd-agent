# stdlib
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest


@attr(requires='mysql')
class TestMySql(AgentCheckTest):
    CHECK_NAME = 'mysql'

    METRIC_TAGS = ['tag1', 'tag2']
    SC_TAGS = ['host:localhost', 'port:0']

    MYSQL_CONFIG = [{
        'server': 'localhost',
        'user': 'dog',
        'pass': 'dog',
        'options': {'replication': True},
        'tags': METRIC_TAGS
    }]

    CONNECTION_FAILURE = [{
        'server': 'localhost',
        'user': 'unknown',
        'pass': 'dog',
    }]

    # Available by default on MySQL > 5.5
    INNODB_METRICS = [
        'mysql.innodb.buffer_pool_free',
        'mysql.innodb.buffer_pool_used',
        'mysql.innodb.buffer_pool_total',
        'mysql.innodb.buffer_pool_utilization'
    ]

    REPLICATION_METRICS = [
        'mysql.replication.slave_running'
    ]

    KEY_CACHE = [
        'mysql.performance.key_cache_utilization'
    ]

    # Available on Linux
    SYSTEM_METRICS = [
        'mysql.performance.user_time',
        'mysql.performance.kernel_time'
    ]

    COMMON_GAUGES = [
        'mysql.net.max_connections',
        'mysql.performance.open_files',
        'mysql.performance.table_locks_waited',
        'mysql.performance.threads_connected',
        'mysql.performance.threads_running',
        # 'mysql.innodb.current_row_locks',  MariaDB status
        'mysql.performance.open_tables',
    ]

    COMMON_RATES = [
        'mysql.net.connections',
        'mysql.innodb.data_reads',
        'mysql.innodb.data_writes',
        'mysql.innodb.os_log_fsyncs',
        'mysql.performance.slow_queries',
        'mysql.performance.questions',
        'mysql.performance.queries',
        'mysql.performance.com_select',
        'mysql.performance.com_insert',
        'mysql.performance.com_update',
        'mysql.performance.com_delete',
        'mysql.performance.com_insert_select',
        'mysql.performance.com_update_multi',
        'mysql.performance.com_delete_multi',
        'mysql.performance.com_replace_select',
        'mysql.performance.qcache_hits',
        # 'mysql.innodb.mutex_spin_waits',  MariaDB status
        # 'mysql.innodb.mutex_spin_rounds', MariaDB status
        # 'mysql.innodb.mutex_os_waits',  MariaDB status
        'mysql.performance.created_tmp_tables',
        'mysql.performance.created_tmp_disk_tables',
        'mysql.performance.created_tmp_files',
        'mysql.innodb.row_lock_waits',
        'mysql.innodb.row_lock_time',
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

    def test_check(self):
        config = {'instances': self.MYSQL_CONFIG}
        self.run_check_twice(config)

        # Test service check
        self.assertServiceCheck('mysql.can_connect', status=AgentCheck.OK,
                                tags=self.SC_TAGS, count=1)

        # Test metrics
        for mname in (self.INNODB_METRICS + self.SYSTEM_METRICS + self.REPLICATION_METRICS +
                      self.KEY_CACHE + self.COMMON_GAUGES + self.COMMON_RATES):
            self.assertMetric(mname, tags=self.METRIC_TAGS, count=1)

        # Assert service metadata
        self.assertServiceMetadata(['version'], count=1)

        # Raises when COVERAGE=true and coverage < 100%
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

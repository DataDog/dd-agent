# stdlib
import os
import sys
import re
import traceback

# 3p
import pymysql

# project
from checks import AgentCheck
from utils.platform import Platform
from utils.subprocess_output import get_subprocess_output

GAUGE = "gauge"
RATE = "rate"

# Vars found in "SHOW STATUS;"
STATUS_VARS = {
    # Command Metrics
    'Slow_queries': ('mysql.performance.slow_queries', RATE),
    'Questions': ('mysql.performance.questions', RATE),
    'Queries': ('mysql.performance.queries', RATE),
    'Com_select': ('mysql.performance.com_select', RATE),
    'Com_insert': ('mysql.performance.com_insert', RATE),
    'Com_update': ('mysql.performance.com_update', RATE),
    'Com_delete': ('mysql.performance.com_delete', RATE),
    'Com_replace': ('mysql.performance.com_replace', RATE),
    'Com_load': ('mysql.performance.com_load', RATE),
    'Com_insert_select': ('mysql.performance.com_insert_select', RATE),
    'Com_update_multi': ('mysql.performance.com_update_multi', RATE),
    'Com_delete_multi': ('mysql.performance.com_delete_multi', RATE),
    'Com_replace_select': ('mysql.performance.com_replace_select', RATE),
    # Connection Metrics
    'Connections': ('mysql.net.connections', RATE),
    'Max_used_connections': ('mysql.net.max_connections', RATE),
    'Aborted_clients': ('mysql.net.aborted_clients', RATE),
    'Aborted_connects': ('mysql.net.aborted_connects', RATE),
    # Table Cache Metrics
    'Open_files': ('mysql.performance.open_files', GAUGE),
    'Open_tables': ('mysql.performance.open_tables', GAUGE),
    # Network Metrics
    'Bytes_sent': ('mysql.performance.bytes_sent', RATE),
    'Bytes_received': ('mysql.performance.bytes_received', RATE),
    # Query Cache Metrics
    'Qcache_hits': ('mysql.performance.qcache_hits', RATE),
    'Qcache_inserts': ('mysql.performance.qcache_inserts', RATE),
    'Qcache_lowmem_prunes': ('mysql.performance.qcache_lowmem_prunes', RATE),
    # Table Lock Metrics
    'Table_locks_waited': ('mysql.performance.table_locks_waited', GAUGE),
    # Temporary Table Metrics
    'Created_tmp_tables': ('mysql.performance.created_tmp_tables', RATE),
    'Created_tmp_disk_tables': ('mysql.performance.created_tmp_disk_tables', RATE),
    'Created_tmp_files': ('mysql.performance.created_tmp_files', RATE),
    # Thread Metrics
    'Threads_connected': ('mysql.performance.threads_connected', GAUGE),
    'Threads_running': ('mysql.performance.threads_running', GAUGE),
    # MyISAM Metrics
    'Key_buffer_bytes_unflushed': ('mysql.myisam.key_buffer_bytes_unflushed', RATE),
    'Key_buffer_bytes_used': ('mysql.myisam.key_buffer_bytes_used', GAUGE),
    'Key_read_requests': ('mysql.myisam.key_read_requests', RATE),
    'Key_reads': ('mysql.myisam.key_reads', RATE),
    'Key_write_requests': ('mysql.myisam.key_write_requests', RATE),
    'Key_writes': ('mysql.myisam.key_writes', RATE),
}

# Possibly from SHOW GLOBAL VARIABLES
VARIABLES_VARS = {
    'Key_buffer_size': ('mysql.myisam.key_buffer_size', GAUGE),
    'Key_cache_utilization': ('mysql.performance.key_cache_utilization', GAUGE),
    'max_connections': ('mysql.net.max_connections_available', GAUGE),
    'query_cache_size': ('mysql.performance.qcache_size', GAUGE),
    'table_open_cache': ('mysql.performance.table_open_cache', GAUGE),
    'thread_cache_size': ('mysql.performance.thread_cache_size', GAUGE)


}

INNODB_VARS = {
    # InnoDB metrics
    'Innodb_data_reads': ('mysql.innodb.data_reads', RATE),
    'Innodb_data_writes': ('mysql.innodb.data_writes', RATE),
    'Innodb_os_log_fsyncs': ('mysql.innodb.os_log_fsyncs', RATE),
    'Innodb_mutex_spin_waits': ('mysql.innodb.mutex_spin_waits', RATE),
    'Innodb_mutex_spin_rounds': ('mysql.innodb.mutex_spin_rounds', RATE),
    'Innodb_mutex_os_waits': ('mysql.innodb.mutex_os_waits', RATE),
    'Innodb_row_lock_waits': ('mysql.innodb.row_lock_waits', RATE),
    'Innodb_row_lock_time': ('mysql.innodb.row_lock_time', RATE),
    'Innodb_row_lock_current_waits': ('mysql.innodb.row_lock_current_waits', GAUGE),
    'Innodb_current_row_locks': ('mysql.innodb.current_row_locks', GAUGE),
    'Innodb_buffer_pool_bytes_dirty': ('mysql.innodb.buffer_pool_dirty', GAUGE),
    'Innodb_buffer_pool_bytes_free': ('mysql.innodb.buffer_pool_free', GAUGE),
    'Innodb_buffer_pool_bytes_used': ('mysql.innodb.buffer_pool_used', GAUGE),
    'Innodb_buffer_pool_bytes_total': ('mysql.innodb.buffer_pool_total', GAUGE),
    'Innodb_buffer_pool_read_requests': ('mysql.innodb.buffer_pool_read_requests', RATE),
    'Innodb_buffer_pool_reads': ('mysql.innodb.buffer_pool_reads', RATE),
    'Innodb_buffer_pool_pages_utilization': ('mysql.innodb.buffer_pool_utilization', GAUGE),
}


# Calculated from "SHOW MASTER LOGS;"
BINLOG_VARS = {
    'Binlog_space_usage_bytes': ('mysql.binlog.disk_use', GAUGE),
}

# Additional Vars found in "SHOW STATUS;"
# Will collect if [FLAG NAME] is True
OPTIONAL_STATUS_VARS = {
    'Binlog_cache_disk_use': ('mysql.binlog.cache_disk_use', GAUGE),
    'Binlog_cache_use': ('mysql.binlog.cache_use', GAUGE),
    'Handler_commit': ('mysql.performance.handler_commit', RATE),
    'Handler_delete': ('mysql.performance.handler_delete', RATE),
    'Handler_read_first': ('mysql.performance.handler_read_first', RATE),
    'Handler_read_key': ('mysql.performance.handler_read_key', RATE),
    'Handler_read_next': ('mysql.performance.handler_read_next', RATE),
    'Handler_read_prev': ('mysql.performance.handler_read_prev', RATE),
    'Handler_read_rnd': ('mysql.performance.handler_read_rnd', RATE),
    'Handler_read_rnd_next': ('mysql.performance.handler_read_rnd_next', RATE),
    'Handler_rollback': ('mysql.performance.handler_rollback', RATE),
    'Handler_update': ('mysql.performance.handler_update', RATE),
    'Handler_write': ('mysql.performance.handler_write', RATE),
    'Opened_tables': ('mysql.performance.opened_tables', RATE),
    'Qcache_free_memory': ('mysql.performance.qcache_free_memory', GAUGE),
    'Qcache_not_cached': ('mysql.performance.qcache_not_cached', RATE),
    'Qcache_queries_in_cache': ('mysql.performance.qcache_queries_in_cache', GAUGE),
    'Select_full_join': ('mysql.performance.select_full_join', RATE),
    'Select_full_range_join': ('mysql.performance.select_full_range_join', RATE),
    'Select_range': ('mysql.performance.select_range', RATE),
    'Select_range_check': ('mysql.performance.select_range_check', RATE),
    'Select_scan': ('mysql.performance.select_scan', RATE),
    'Sort_merge_passes': ('mysql.performance.sort_merge_passes', RATE),
    'Sort_range': ('mysql.performance.sort_range', RATE),
    'Sort_rows': ('mysql.performance.sort_rows', RATE),
    'Sort_scan': ('mysql.performance.sort_scan', RATE),
    'Table_locks_immediate': ('mysql.performance.table_locks_immediate', RATE),
    'Threads_cached': ('mysql.performance.threads_cached', GAUGE),
    'Threads_created': ('mysql.performance.threads_created', GAUGE)
}

# Status Vars added in Mysql 5.6.6
OPTIONAL_STATUS_VARS_5_6_6 = {
    'Table_open_cache_hits': ('mysql.performance.table_cache_hits', RATE),
    'Table_open_cache_misses': ('mysql.performance.table_cache_misses', RATE),
}

# Will collect if [FLAG NAME] is True
OPTIONAL_INNODB_VARS = {
    'Innodb_active_transactions': ('mysql.innodb.active_transactions', GAUGE),
    'Innodb_buffer_pool_bytes_data': ('mysql.innodb.buffer_pool_data', GAUGE),
    'Innodb_buffer_pool_pages_data': ('mysql.innodb.buffer_pool_pages_data', GAUGE),
    'Innodb_buffer_pool_pages_dirty': ('mysql.innodb.buffer_pool_pages_dirty', GAUGE),
    'Innodb_buffer_pool_pages_flushed': ('mysql.innodb.buffer_pool_pages_flushed', RATE),
    'Innodb_buffer_pool_pages_free': ('mysql.innodb.buffer_pool_pages_free', GAUGE),
    'Innodb_buffer_pool_pages_total': ('mysql.innodb.buffer_pool_pages_total', GAUGE),
    'Innodb_buffer_pool_read_ahead': ('mysql.innodb.buffer_pool_read_ahead', RATE),
    'Innodb_buffer_pool_read_ahead_evicted': ('mysql.innodb.buffer_pool_read_ahead_evicted', GAUGE),
    'Innodb_buffer_pool_read_ahead_rnd': ('mysql.innodb.buffer_pool_read_ahead_rnd', GAUGE),
    'Innodb_buffer_pool_wait_free': ('mysql.innodb.buffer_pool_wait_free', GAUGE),
    'Innodb_buffer_pool_write_requests': ('mysql.innodb.buffer_pool_write_requests', RATE),
    'Innodb_checkpoint_age': ('mysql.innodb.checkpoint_age', GAUGE),
    'Innodb_current_transactions': ('mysql.innodb.current_transactions', GAUGE),
    'Innodb_data_fsyncs': ('mysql.innodb.data_fsyncs', GAUGE),
    'Innodb_data_pending_fsyncs': ('mysql.innodb.data_pending_fsyncs', GAUGE),
    'Innodb_data_pending_reads': ('mysql.innodb.data_pending_reads', GAUGE),
    'Innodb_data_pending_writes': ('mysql.innodb.data_pending_writes', GAUGE),
    'Innodb_data_read': ('mysql.innodb.data_read', GAUGE),
    'Innodb_data_written': ('mysql.innodb.data_written', GAUGE),
    'Innodb_dblwr_pages_written': ('mysql.innodb.dblwr_pages_written', GAUGE),
    'Innodb_dblwr_writes': ('mysql.innodb.dblwr_writes', GAUGE),
    'Innodb_hash_index_cells_total': ('mysql.innodb.hash_index_cells_total', GAUGE),
    'Innodb_hash_index_cells_used': ('mysql.innodb.hash_index_cells_used', GAUGE),
    'Innodb_history_list_length': ('mysql.innodb.history_list_length', GAUGE),
    'Innodb_ibuf_free_list': ('mysql.innodb.ibuf_free_list', GAUGE),
    'Innodb_ibuf_merged': ('mysql.innodb.ibuf_merged', RATE),
    'Innodb_ibuf_merged_delete_marks': ('mysql.innodb.ibuf_merged_delete_marks', RATE),
    'Innodb_ibuf_merged_deletes': ('mysql.innodb.ibuf_merged_deletes', RATE),
    'Innodb_ibuf_merged_inserts': ('mysql.innodb.ibuf_merged_inserts', RATE),
    'Innodb_ibuf_merges': ('mysql.innodb.ibuf_merges', RATE),
    'Innodb_ibuf_segment_size': ('mysql.innodb.ibuf_segment_size', GAUGE),
    'Innodb_ibuf_size': ('mysql.innodb.ibuf_size', GAUGE),
    'Innodb_lock_structs': ('mysql.innodb.lock_structs', RATE),
    'Innodb_locked_tables': ('mysql.innodb.locked_tables', GAUGE),
    'Innodb_locked_transactions': ('mysql.innodb.locked_transactions', GAUGE),
    'Innodb_log_waits': ('mysql.innodb.log_waits', RATE),
    'Innodb_log_write_requests': ('mysql.innodb.log_write_requests', RATE),
    'Innodb_log_writes': ('mysql.innodb.log_writes', RATE),
    'Innodb_lsn_current': ('mysql.innodb.lsn_current', RATE),
    'Innodb_lsn_flushed': ('mysql.innodb.lsn_flushed', RATE),
    'Innodb_lsn_last_checkpoint': ('mysql.innodb.lsn_last_checkpoint', RATE),
    'Innodb_mem_adaptive_hash': ('mysql.innodb.mem_adaptive_hash', GAUGE),
    'Innodb_mem_additional_pool': ('mysql.innodb.mem_additional_pool', GAUGE),
    'Innodb_mem_dictionary': ('mysql.innodb.mem_dictionary', GAUGE),
    'Innodb_mem_file_system': ('mysql.innodb.mem_file_system', GAUGE),
    'Innodb_mem_lock_system': ('mysql.innodb.mem_lock_system', GAUGE),
    'Innodb_mem_page_hash': ('mysql.innodb.mem_page_hash', GAUGE),
    'Innodb_mem_recovery_system': ('mysql.innodb.mem_recovery_system', GAUGE),
    'Innodb_mem_thread_hash': ('mysql.innodb.mem_thread_hash', GAUGE),
    'Innodb_mem_total': ('mysql.innodb.mem_total', GAUGE),
    'Innodb_os_file_fsyncs': ('mysql.innodb.os_file_fsyncs', RATE),
    'Innodb_os_file_reads': ('mysql.innodb.os_file_reads', RATE),
    'Innodb_os_file_writes': ('mysql.innodb.os_file_writes', RATE),
    'Innodb_os_log_pending_fsyncs': ('mysql.innodb.os_log_pending_fsyncs', RATE),
    'Innodb_os_log_pending_writes': ('mysql.innodb.os_log_pending_writes', RATE),
    'Innodb_os_log_written': ('mysql.innodb.os_log_written', RATE),
    'Innodb_pages_created': ('mysql.innodb.pages_created', RATE),
    'Innodb_pages_read': ('mysql.innodb.pages_read', RATE),
    'Innodb_pages_written': ('mysql.innodb.pages_written', RATE),
    'Innodb_pending_aio_log_ios': ('mysql.innodb.pending_aio_log_ios', RATE),
    'Innodb_pending_aio_sync_ios': ('mysql.innodb.pending_aio_sync_ios', RATE),
    'Innodb_pending_buffer_pool_flushes': ('mysql.innodb.pending_buffer_pool_flushes', RATE),
    'Innodb_pending_checkpoint_writes': ('mysql.innodb.pending_checkpoint_writes', RATE),
    'Innodb_pending_ibuf_aio_reads': ('mysql.innodb.pending_ibuf_aio_reads', RATE),
    'Innodb_pending_log_flushes': ('mysql.innodb.pending_log_flushes', RATE),
    'Innodb_pending_log_writes': ('mysql.innodb.pending_log_writes', RATE),
    'Innodb_pending_normal_aio_reads': ('mysql.innodb.pending_normal_aio_reads', RATE),
    'Innodb_pending_normal_aio_writes': ('mysql.innodb.pending_normal_aio_writes', RATE),
    'Innodb_queries_inside': ('mysql.innodb.queries_inside', RATE),
    'Innodb_queries_queued': ('mysql.innodb.queries_queued', RATE),
    'Innodb_read_views': ('mysql.innodb.read_views', GAUGE),
    'Innodb_rows_deleted': ('mysql.innodb.rows_deleted', RATE),
    'Innodb_rows_inserted': ('mysql.innodb.rows_inserted', RATE),
    'Innodb_rows_read': ('mysql.innodb.rows_read', RATE),
    'Innodb_rows_updated': ('mysql.innodb.rows_updated', RATE),
    'Innodb_s_lock_os_waits': ('mysql.innodb.s_lock_os_waits', RATE),
    'Innodb_s_lock_spin_rounds': ('mysql.innodb.s_lock_spin_rounds', RATE),
    'Innodb_s_lock_spin_waits': ('mysql.innodb.s_lock_spin_waits', RATE),
    'Innodb_semaphore_wait_time': ('mysql.innodb.semaphore_wait_time', GAUGE),
    'Innodb_semaphore_waits': ('mysql.innodb.semaphore_waits', GAUGE),
    'Innodb_tables_in_use': ('mysql.innodb.tables_in_use', GAUGE),
    'Innodb_x_lock_os_waits': ('mysql.innodb.x_lock_os_waits', RATE),
    'Innodb_x_lock_spin_rounds': ('mysql.innodb.x_lock_spin_rounds', RATE),
    'Innodb_x_lock_spin_waits': ('mysql.innodb.x_lock_spin_waits', RATE),
}


class MySql(AgentCheck):
    SERVICE_CHECK_NAME = 'mysql.can_connect'
    MAX_CUSTOM_QUERIES = 20

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.mysql_version = {}
        self.greater_502 = {}

    def get_library_versions(self):
        return {"pymysql": pymysql.__version__}

    def check(self, instance):
        host, port, user, password, mysql_sock, defaults_file, tags, options, queries = \
            self._get_config(instance)

        if (not host or not user) and not defaults_file:
            raise Exception("Mysql host and user are needed.")

        db = self._connect(host, port, mysql_sock, user,
                           password, defaults_file)

        # Metadata collection
        self._collect_metadata(db, host)

        # Metric collection
        self._collect_metrics(host, db, tags, options, queries)
        if Platform.is_linux():
            self._collect_system_metrics(host, db, tags)

        # Close connection
        db.close()

    def _get_config(self, instance):
        host = instance.get('server', '')
        user = instance.get('user', '')
        port = int(instance.get('port', 0))
        password = instance.get('pass', '')
        mysql_sock = instance.get('sock', '')
        defaults_file = instance.get('defaults_file', '')
        tags = instance.get('tags', None)
        options = instance.get('options', {})
        queries = instance.get('queries', [])

        return host, port, user, password, mysql_sock, defaults_file, tags, options, queries

    def _connect(self, host, port, mysql_sock, user, password, defaults_file):
        service_check_tags = [
            'host:%s' % host,
            'port:%s' % port
        ]

        try:
            if defaults_file != '':
                db = pymysql.connect(read_default_file=defaults_file)
            elif mysql_sock != '':
                db = pymysql.connect(
                    unix_socket=mysql_sock,
                    user=user,
                    passwd=password
                )
                service_check_tags = [
                    'host:%s' % mysql_sock,
                    'port:unix_socket'
                ]
            elif port:
                db = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    passwd=password
                )
            else:
                db = pymysql.connect(
                    host=host,
                    user=user,
                    passwd=password
                )
            self.log.debug("Connected to MySQL")
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=service_check_tags)
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            raise

        return db

    def _collect_metrics(self, host, db, tags, options, queries):

        # collect results from db
        results = self._get_stats_from_status(db)
        results.update(self._get_stats_from_variables(db))

        if self._is_innodb_engine_enabled(db):
            results.update(self._get_stats_from_innodb_status(db))
            innodb_page_size = self._collect_scalar(
                'Innodb_page_size', results)
            innodb_buffer_pool_pages_data = self._collect_scalar(
                'Innodb_buffer_pool_pages_data', results)
            innodb_buffer_pool_pages_dirty = self._collect_scalar(
                'Innodb_buffer_pool_pages_dirty', results)
            innodb_buffer_pool_pages_total = self._collect_scalar(
                'Innodb_buffer_pool_pages_total', results)
            innodb_buffer_pool_pages_free = self._collect_scalar(
                'Innodb_buffer_pool_pages_free', results)
            innodb_buffer_pool_pages_used = innodb_buffer_pool_pages_total - \
                innodb_buffer_pool_pages_free

            if 'Innodb_buffer_pool_bytes_data' not in results:
                results[
                    'Innodb_buffer_pool_bytes_data'] = innodb_buffer_pool_pages_data * innodb_page_size

            if 'Innodb_buffer_pool_bytes_dirty' not in results:
                results[
                    'Innodb_buffer_pool_bytes_dirty'] = innodb_buffer_pool_pages_dirty * innodb_page_size

            if 'Innodb_buffer_pool_bytes_free' not in results:
                results[
                    'Innodb_buffer_pool_bytes_free'] = innodb_buffer_pool_pages_free * innodb_page_size

            if 'Innodb_buffer_pool_bytes_total' not in results:
                results[
                    'Innodb_buffer_pool_bytes_total'] = innodb_buffer_pool_pages_total * innodb_page_size

            if 'Innodb_buffer_pool_pages_utilization' not in results:
                results['Innodb_buffer_pool_pages_utilization'] = innodb_buffer_pool_pages_used / \
                    innodb_buffer_pool_pages_total

            if 'Innodb_buffer_pool_bytes_used' not in results:
                results[
                    'Innodb_buffer_pool_bytes_used'] = innodb_buffer_pool_pages_used * innodb_page_size

        # Binary log statistics
        binlog_enabled = self._collect_string('log_bin', results)
        if binlog_enabled is not None and binlog_enabled.lower().strip() == 'on':
            results[
                'Binlog_space_usage_bytes'] = self._get_binary_log_stats(db)

        # Compute key cache utilization metric
        key_blocks_unused = self._collect_scalar('Key_blocks_unused', results)
        key_cache_block_size = self._collect_scalar(
            'key_cache_block_size', results)
        key_buffer_size = self._collect_scalar('key_buffer_size', results)
        key_cache_utilization = 1 - \
            ((key_blocks_unused * key_cache_block_size) / key_buffer_size)

        results['Key_buffer_size'] = key_buffer_size
        results['Key_buffer_bytes_used'] = self._collect_scalar(
            'Key_blocks_used', results) * key_cache_block_size
        results['Key_buffer_bytes_unflushed'] = self._collect_scalar(
            'Key_blocks_not_flushed', results) * key_cache_block_size
        results['Key_cache_utilization'] = key_cache_utilization

        # Get aggregate of all VARS we want to collect
        VARS = STATUS_VARS
        VARS.update(VARIABLES_VARS)
        VARS.update(INNODB_VARS)
        VARS.update(BINLOG_VARS)

        if 'extra_status_metrics' in options and options['extra_status_metrics']:
            self.log.debug("Collecting Extra Status Metrics")
            VARS.update(OPTIONAL_STATUS_VARS)

            if self._version_compatible(db, host, "5.6.6"):
                VARS.update(OPTIONAL_STATUS_VARS_5_6_6)

        if 'extra_innodb_metrics' in options and options['extra_innodb_metrics']:
            self.log.debug("Collecting Extra Innodb Metrics")
            VARS.update(OPTIONAL_INNODB_VARS)

        self._rate_or_gauge_vars(VARS, results, tags)

        if 'galera_cluster' in options and options['galera_cluster']:
            value = self._collect_scalar('wsrep_cluster_size', results)
            self.gauge('mysql.galera.wsrep_cluster_size', value, tags=tags)

        if 'replication' in options and options['replication']:
            # get slave running form global status page
            slave_running = self._collect_string('Slave_running', results)
            if slave_running is not None:
                if slave_running.lower().strip() == 'on':
                    slave_running = 1
                else:
                    slave_running = 0
                self.gauge("mysql.replication.slave_running",
                           slave_running, tags=tags)
            self._collect_dict(
                GAUGE,
                {"Seconds_behind_master": "mysql.replication.seconds_behind_master"},
                "SHOW SLAVE STATUS", db, tags=tags
            )

        # Collect custom query metrics
        # Max of 20 queries allowed
        if isinstance(queries, list):
            for index, check in enumerate(queries[:self.MAX_CUSTOM_QUERIES]):
                self._collect_dict(check['type'], {check['field']: check[
                                   'metric']}, check['query'], db, tags=tags)

            if len(queries) > self.MAX_CUSTOM_QUERIES:
                self.warning("Maximum number (%s) of custom queries reached.  Skipping the rest."
                             % self.MAX_CUSTOM_QUERIES)

    def _collect_metadata(self, db, host):
        self._get_version(db, host)

    def _rate_or_gauge_vars(self, variables, dbResults, tags):
        for variable, metric in variables.iteritems():
            metric_name, metric_type = metric
            value = self._collect_scalar(variable, dbResults)
            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, tags=tags)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=tags)

    def _version_compatible(self, db, host, compat_version):
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number

        compatible = False
        try:
            mysql_version = self._get_version(db, host)
            self.log.debug("MySQL version %s" % mysql_version)

            major = int(mysql_version[0])
            minor = int(mysql_version[1])
            patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))

            compat_version = compat_version.split('.')
            compat_major = int(compat_version[0])
            compat_minor = int(compat_version[1])
            compat_patchlevel = int(compat_version[2])

            if (major, minor, patchlevel) > (compat_major, compat_minor, compat_patchlevel):
                compatible = True

        except Exception, exception:
            self.warning("Cannot compute mysql version, assuming older than 5.0.2: %s"
                         % str(exception))

        return compatible

    def _get_version(self, db, host):
        if host in self.mysql_version:
            version = self.mysql_version[host]
            self.service_metadata('version', ".".join(version))
            return version

        # Get MySQL version
        cursor = db.cursor()
        cursor.execute('SELECT VERSION()')
        result = cursor.fetchone()
        cursor.close()
        del cursor
        # Version might include a description e.g. 4.1.26-log.
        # See
        # http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
        version = result[0].split('-')
        version = version[0].split('.')
        self.mysql_version[host] = version
        self.service_metadata('version', ".".join(version))
        return version

    def _collect_scalar(self, key, dict):
        return self._collect_type(key, dict, float)

    def _collect_string(self, key, dict):
        return self._collect_type(key, dict, unicode)

    def _collect_type(self, key, dict, the_type):
        self.log.debug("Collecting data with %s" % key)
        if key not in dict:
            self.log.debug("%s returned None" % key)
            return None
        self.log.debug("Collecting done, value %s" % dict[key])
        return the_type(dict[key])

    def _collect_dict(self, metric_type, field_metric_map, query, db, tags):
        """
        Query status and get a dictionary back.
        Extract each field out of the dictionary
        and stuff it in the corresponding metric.

        query: show status...
        field_metric_map: {"Seconds_behind_master": "mysqlSecondsBehindMaster"}
        """
        try:
            cursor = db.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            if result is not None:
                for field in field_metric_map.keys():
                    # Get the agent metric name from the column name
                    metric = field_metric_map[field]
                    # Find the column name in the cursor description to identify the column index
                    # http://www.python.org/dev/peps/pep-0249/
                    # cursor.description is a tuple of (column_name, ..., ...)
                    try:
                        col_idx = [d[0].lower()
                                   for d in cursor.description].index(field.lower())
                        self.log.debug("Collecting metric: %s" % metric)
                        if result[col_idx] is not None:
                            self.log.debug(
                                "Collecting done, value %s" % result[col_idx])
                            if metric_type == GAUGE:
                                self.gauge(metric, float(
                                    result[col_idx]), tags=tags)
                            elif metric_type == RATE:
                                self.rate(metric, float(
                                    result[col_idx]), tags=tags)
                            else:
                                self.gauge(metric, float(
                                    result[col_idx]), tags=tags)
                        else:
                            self.log.debug(
                                "Received value is None for index %d" % col_idx)
                    except ValueError:
                        self.log.exception("Cannot find %s in the columns %s"
                                           % (field, cursor.description))
            cursor.close()
            del cursor
        except Exception:
            self.warning("Error while running %s\n%s" %
                         (query, traceback.format_exc()))
            self.log.exception("Error while running %s" % query)

    def _collect_system_metrics(self, host, db, tags):
        pid = None
        # The server needs to run locally, accessed by TCP or socket
        if host in ["localhost", "127.0.0.1"] or db.port == long(0):
            pid = self._get_server_pid(db)

        if pid:
            self.log.debug("pid: %s" % pid)
            # At last, get mysql cpu data out of procfs
            try:
                # See http://www.kernel.org/doc/man-pages/online/pages/man5/proc.5.html
                # for meaning: we get 13 & 14: utime and stime, in clock ticks and convert
                # them with the right sysconf value (SC_CLK_TCK)
                proc_file = open("/proc/%d/stat" % pid)
                data = proc_file.readline()
                proc_file.close()
                fields = data.split(' ')
                ucpu = fields[13]
                kcpu = fields[14]
                clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                # Convert time to s (number of second of CPU used by mysql)
                # It's a counter, it will be divided by the period, multiply by 100
                # to get the percentage of CPU used by mysql over the period
                self.rate("mysql.performance.user_time",
                          int((float(ucpu) / float(clk_tck)) * 100), tags=tags)
                self.rate("mysql.performance.kernel_time",
                          int((float(kcpu) / float(clk_tck)) * 100), tags=tags)
            except Exception:
                self.warning("Error while reading mysql (pid: %s) procfs data\n%s"
                             % (pid, traceback.format_exc()))

    def _get_server_pid(self, db):
        pid = None

        # Try to get pid from pid file, it can fail for permission reason
        pid_file = None
        try:
            cursor = db.cursor()
            cursor.execute("SHOW VARIABLES LIKE 'pid_file'")
            pid_file = cursor.fetchone()[1]
            cursor.close()
            del cursor
        except Exception:
            self.warning("Error while fetching pid_file variable of MySQL.")

        if pid_file is not None:
            self.log.debug("pid file: %s" % str(pid_file))
            try:
                f = open(pid_file)
                pid = int(f.readline())
                f.close()
            except IOError:
                self.log.debug("Cannot read mysql pid file %s" % pid_file)

        # If pid has not been found, read it from ps
        if pid is None:
            try:
                if sys.platform.startswith("linux"):
                    ps, _, _ = get_subprocess_output(['ps', '-C', 'mysqld', '-o', 'pid'], self.log)
                    pslines = ps.strip().splitlines()
                    # First line is header, second line is mysql pid
                    if len(pslines) == 2:
                        pid = int(pslines[1])
            except Exception:
                self.log.exception("Error while fetching mysql pid from ps")

        return pid

    def _get_stats_from_status(self, db):
        cursor = db.cursor()
        cursor.execute("SHOW /*!50002 GLOBAL */ STATUS;")
        results = dict(cursor.fetchall())
        cursor.close()
        del cursor
        return results

    def _get_stats_from_variables(self, db):
        cursor = db.cursor()
        cursor.execute("SHOW GLOBAL VARIABLES;")
        results = dict(cursor.fetchall())
        cursor.close()
        del cursor
        return results

    def _get_binary_log_stats(self, db):
        cursor = db.cursor()
        cursor.execute("SHOW MASTER LOGS;")
        master_logs = dict(cursor.fetchall())

        cursor.close()
        del cursor

        binary_log_space = 0
        for key, value in master_logs.iteritems():
            binary_log_space += value

        return binary_log_space

    def _is_innodb_engine_enabled(self, db):
        # Whether InnoDB engine is available or not can be found out either
        # from the output of SHOW ENGINES or from information_schema.ENGINES
        # table. Later is choosen because that involves no string parsing.
        cursor = db.cursor()
        cursor.execute(
            "select engine from information_schema.ENGINES where engine='InnoDB'")

        return_val = True if cursor.rowcount > 0 else False

        cursor.close()
        del cursor

        return return_val

    def _get_stats_from_innodb_status(self, db):
        # There are a number of important InnoDB metrics that are reported in
        # InnoDB status but are not otherwise present as part of the STATUS
        # variables in MySQL. Majority of these metrics are reported though
        # as a part of STATUS variables in Percona Server and MariaDB.
        cursor = db.cursor()
        cursor.execute("SHOW /*!50000 ENGINE*/ INNODB STATUS")

        innodb_status = cursor.fetchone()
        innodb_status_text = innodb_status[2]

        cursor.close()
        del cursor

        results = {
            'Innodb_mutex_spin_waits': 0,
            'Innodb_mutex_spin_rounds': 0,
            'Innodb_mutex_os_waits': 0,
            'Innodb_s_lock_spin_waits': 0,
            'Innodb_x_lock_spin_waits': 0,
            'Innodb_s_lock_os_waits': 0,
            'Innodb_x_lock_os_waits': 0,
            'Innodb_s_lock_spin_rounds': 0,
            'Innodb_semaphore_waits': 0,
            'Innodb_semaphore_wait_time': 0,
            'Innodb_history_list_length': 0,
            'Innodb_current_transactions': 0,
            'Innodb_active_transactions': 0,
            'Innodb_row_lock_time': 0,
            'Innodb_read_views': 0,
            'Innodb_tables_in_use': 0,
            'Innodb_locked_tables': 0,
            'Innodb_lock_structs': 0,
            'Innodb_locked_transactions': 0,
            'Innodb_os_file_reads': 0,
            'Innodb_os_file_writes': 0,
            'Innodb_os_file_fsyncs': 0,
            'Innodb_pending_normal_aio_reads': 0,
            'Innodb_pending_normal_aio_writes': 0,
            'Innodb_pending_ibuf_aio_reads': 0,
            'Innodb_pending_aio_log_ios': 0,
            'Innodb_pending_aio_sync_ios': 0,
            'Innodb_pending_log_flushes': 0,
            'Innodb_pending_buffer_pool_flushes': 0,
            'Innodb_ibuf_size': 0,
            'Innodb_ibuf_free_list': 0,
            'Innodb_ibuf_segment_size': 0,
            'Innodb_ibuf_merges': 0,
            'Innodb_ibuf_merged_inserts': 0,
            'Innodb_ibuf_merged_delete_marks': 0,
            'Innodb_ibuf_merged_deletes': 0,
            'Innodb_ibuf_merged': 0,
            'Innodb_ibuf_merged_inserts': 0,
            'Innodb_ibuf_merged': 0,
            'Innodb_ibuf_merges': 0,
            'Innodb_hash_index_cells_total': 0,
            'Innodb_hash_index_cells_used': 0,
            'Innodb_log_writes': 0,
            'Innodb_pending_log_writes': 0,
            'Innodb_pending_checkpoint_writes': 0,
            'Innodb_lsn_current': 0,
            'Innodb_lsn_flushed': 0,
            'Innodb_lsn_last_checkpoint': 0,
            'Innodb_mem_total': 0,
            'Innodb_mem_additional_pool': 0,
            'Innodb_mem_adaptive_hash': 0,
            'Innodb_mem_page_hash': 0,
            'Innodb_mem_dictionary': 0,
            'Innodb_mem_file_system': 0,
            'Innodb_mem_lock_system': 0,
            'Innodb_mem_recovery_system': 0,
            'Innodb_mem_thread_hash': 0,
            'Innodb_buffer_pool_pages_total': 0,
            'Innodb_buffer_pool_pages_free': 0,
            'Innodb_buffer_pool_pages_data': 0,
            'Innodb_buffer_pool_pages_dirty': 0,
            'Innodb_pages_read': 0,
            'Innodb_pages_created': 0,
            'Innodb_pages_written': 0,
            'Innodb_rows_inserted': 0,
            'Innodb_rows_updated': 0,
            'Innodb_rows_deleted': 0,
            'Innodb_rows_read': 0,
            'Innodb_queries_inside': 0,
            'Innodb_queries_queued': 0,
            'Innodb_checkpoint_age': 0
        }

        # Here we now parse InnoDB STATUS one line at a time
        # This is heavily inspired by the Percona monitoring plugins work
        txn_seen = False
        prev_line = ''

        for line in innodb_status_text.splitlines():
            line = line.strip()
            row = re.split(" +", line)
            row = [item.strip(',') for item in row]
            row = [item.strip(';') for item in row]

            # SEMAPHORES
            if line.find('Mutex spin waits') == 0:
                # Mutex spin waits 79626940, rounds 157459864, OS waits 698719
                # Mutex spin waits 0, rounds 247280272495, OS waits 316513438
                results['Innodb_mutex_spin_waits'] = long(row[3])
                results['Innodb_mutex_spin_rounds'] = long(row[5])
                results['Innodb_mutex_os_waits'] = long(row[8])
            elif line.find('RW-shared spins') == 0 and line.find(';') > 0:
                # RW-shared spins 3859028, OS waits 2100750; RW-excl spins
                # 4641946, OS waits 1530310
                results['Innodb_s_lock_spin_waits'] = long(row[2])
                results['Innodb_x_lock_spin_waits'] = long(row[8])
                results['Innodb_s_lock_os_waits'] = long(row[5])
                results['Innodb_x_lock_os_waits'] = long(row[11])
            elif line.find('RW-shared spins') == 0 and line.find('; RW-excl spins') == -1:
                # Post 5.5.17 SHOW ENGINE INNODB STATUS syntax
                # RW-shared spins 604733, rounds 8107431, OS waits 241268
                results['Innodb_s_lock_spin_waits'] = long(row[2])
                results['Innodb_s_lock_spin_rounds'] = long(row[4])
                results['Innodb_s_lock_os_waits'] = long(row[7])
            elif line.find('RW-excl spins') == 0:
                # Post 5.5.17 SHOW ENGINE INNODB STATUS syntax
                # RW-excl spins 604733, rounds 8107431, OS waits 241268
                results['Innodb_x_lock_spin_waits'] = long(row[2])
                results['Innodb_x_lock_spin_rounds'] = long(row[4])
                results['Innodb_x_lock_os_waits'] = long(row[7])
            elif line.find('seconds the semaphore:') > 0:
                # --Thread 907205 has waited at handler/ha_innodb.cc line 7156 for 1.00 seconds the semaphore:
                results['Innodb_semaphore_waits'] += 1
                results[
                    'Innodb_semaphore_wait_time'] += long(float(row[9])) * 1000

            # TRANSACTIONS
            elif line.find('Trx id counter') == 0:
                # The beginning of the TRANSACTIONS section: start counting
                # transactions
                # Trx id counter 0 1170664159
                # Trx id counter 861B144C
                txn_seen = True
            elif line.find('History list length') == 0:
                # History list length 132
                results['Innodb_history_list_length'] = long(row[3])
            elif txn_seen and line.find('---TRANSACTION') == 0:
                # ---TRANSACTION 0, not started, process no 13510, OS thread id 1170446656
                results['Innodb_current_transactions'] += 1
                if line.find('ACTIVE') > 0:
                    results['Innodb_active_transactions'] += 1
            elif txn_seen and line.find('------- TRX HAS BEEN') == 0:
                # ------- TRX HAS BEEN WAITING 32 SEC FOR THIS LOCK TO BE GRANTED:
                results['Innodb_row_lock_time'] += long(row[5]) * 1000
            elif line.find('read views open inside InnoDB') > 0:
                # 1 read views open inside InnoDB
                results['Innodb_read_views'] = long(row[0])
            elif line.find('mysql tables in use') == 0:
                # mysql tables in use 2, locked 2
                results['Innodb_tables_in_use'] += long(row[4])
                results['Innodb_locked_tables'] += long(row[6])
            elif txn_seen and line.find('lock struct(s)') > 0:
                # 23 lock struct(s), heap size 3024, undo log entries 27
                # LOCK WAIT 12 lock struct(s), heap size 3024, undo log entries 5
                # LOCK WAIT 2 lock struct(s), heap size 368
                if line.find('LOCK WAIT') == 0:
                    results['Innodb_lock_structs'] += long(row[2])
                    results['Innodb_locked_transactions'] += 1
                elif line.find('ROLLING BACK') == 0:
                    # ROLLING BACK 127539 lock struct(s), heap size 15201832,
                    # 4411492 row lock(s), undo log entries 1042488
                    results['Innodb_lock_structs'] += long(row[2])
                else:
                    results['Innodb_lock_structs'] += long(row[0])

            # FILE I/O
            elif line.find(' OS file reads, ') > 0:
                # 8782182 OS file reads, 15635445 OS file writes, 947800 OS
                # fsyncs
                results['Innodb_os_file_reads'] = long(row[0])
                results['Innodb_os_file_writes'] = long(row[4])
                results['Innodb_os_file_fsyncs'] = long(row[8])
            elif line.find('Pending normal aio reads:') == 0:
                # Pending normal aio reads: 0, aio writes: 0,
                results['Innodb_pending_normal_aio_reads'] = long(row[4])
                results['Innodb_pending_normal_aio_writes'] = long(row[7])
            elif line.find('ibuf aio reads') == 0:
                #  ibuf aio reads: 0, log i/o's: 0, sync i/o's: 0
                results['Innodb_pending_ibuf_aio_reads'] = long(row[3])
                results['Innodb_pending_aio_log_ios'] = long(row[6])
                results['Innodb_pending_aio_sync_ios'] = long(row[9])
            elif line.find('Pending flushes (fsync)') == 0:
                # Pending flushes (fsync) log: 0; buffer pool: 0
                results['Innodb_pending_log_flushes'] = long(row[4])
                results['Innodb_pending_buffer_pool_flushes'] = long(row[7])

            # INSERT BUFFER AND ADAPTIVE HASH INDEX
            elif line.find('Ibuf for space 0: size ') == 0:
                # Older InnoDB code seemed to be ready for an ibuf per tablespace.  It
                # had two lines in the output.  Newer has just one line, see below.
                # Ibuf for space 0: size 1, free list len 887, seg size 889, is not empty
                # Ibuf for space 0: size 1, free list len 887, seg size 889,
                results['Innodb_ibuf_size'] = long(row[5])
                results['Innodb_ibuf_free_list'] = long(row[9])
                results['Innodb_ibuf_segment_size'] = long(row[12])
            elif line.find('Ibuf: size ') == 0:
                # Ibuf: size 1, free list len 4634, seg size 4636,
                results['Innodb_ibuf_size'] = long(row[2])
                results['Innodb_ibuf_free_list'] = long(row[6])
                results['Innodb_ibuf_segment_size'] = long(row[9])

                if line.find('merges') > -1:
                    results['Innodb_ibuf_merges'] = long(row[10])
            elif line.find(', delete mark ') > 0 and prev_line.find('merged operations:') == 0:
                # Output of show engine innodb status has changed in 5.5
                # merged operations:
                # insert 593983, delete mark 387006, delete 73092
                results['Innodb_ibuf_merged_inserts'] = long(row[1])
                results['Innodb_ibuf_merged_delete_marks'] = long(row[4])
                results['Innodb_ibuf_merged_deletes'] = long(row[6])
                results['Innodb_ibuf_merged'] = results['Innodb_ibuf_merged_inserts'] + results[
                    'Innodb_ibuf_merged_delete_marks'] + results['Innodb_ibuf_merged_deletes']
            elif line.find(' merged recs, ') > 0:
                # 19817685 inserts, 19817684 merged recs, 3552620 merges
                results['Innodb_ibuf_merged_inserts'] = long(row[0])
                results['Innodb_ibuf_merged'] = long(row[2])
                results['Innodb_ibuf_merges'] = long(row[5])
            elif line.find('Hash table size ') == 0:
                # In some versions of InnoDB, the used cells is omitted.
                # Hash table size 4425293, used cells 4229064, ....
                # Hash table size 57374437, node heap has 72964 buffer(s) <--
                # no used cells
                results['Innodb_hash_index_cells_total'] = long(row[3])
                results['Innodb_hash_index_cells_used'] = long(
                    row[6]) if line.find('used cells') > 0 else 0

            # LOG
            elif line.find(" log i/o's done, ") > 0:
                # 3430041 log i/o's done, 17.44 log i/o's/second
                # 520835887 log i/o's done, 17.28 log i/o's/second, 518724686
                # syncs, 2980893 checkpoints
                results['Innodb_log_writes'] = long(row[0])
            elif line.find(" pending log writes, ") > 0:
                # 0 pending log writes, 0 pending chkp writes
                results['Innodb_pending_log_writes'] = long(row[0])
                results['Innodb_pending_checkpoint_writes'] = long(row[4])
            elif line.find("Log sequence number") == 0:
                # This number is NOT printed in hex in InnoDB plugin.
                # Log sequence number 272588624
                results['Innodb_lsn_current'] = long(row[3])
            elif line.find("Log flushed up to") == 0:
                # This number is NOT printed in hex in InnoDB plugin.
                # Log flushed up to   272588624
                results['Innodb_lsn_flushed'] = long(row[4])
            elif line.find("Last checkpoint at") == 0:
                # Last checkpoint at  272588624
                results['Innodb_lsn_last_checkpoint'] = long(row[3])

            # BUFFER POOL AND MEMORY
            elif line.find("Total memory allocated") == 0 and line.find("in additional pool allocated") > 0:
                # Total memory allocated 29642194944; in additional pool allocated 0
                # Total memory allocated by read views 96
                results['Innodb_mem_total'] = long(row[3])
                results['Innodb_mem_additional_pool'] = long(row[8])
            elif line.find('Adaptive hash index ') == 0:
                #   Adaptive hash index 1538240664     (186998824 + 1351241840)
                results['Innodb_mem_adaptive_hash'] = long(row[3])
            elif line.find('Page hash           ') == 0:
                #   Page hash           11688584
                results['Innodb_mem_page_hash'] = long(row[2])
            elif line.find('Dictionary cache    ') == 0:
                #   Dictionary cache    145525560      (140250984 + 5274576)
                results['Innodb_mem_dictionary'] = long(row[2])
            elif line.find('File system         ') == 0:
                #   File system         313848         (82672 + 231176)
                results['Innodb_mem_file_system'] = long(row[2])
            elif line.find('Lock system         ') == 0:
                #   Lock system         29232616       (29219368 + 13248)
                results['Innodb_mem_lock_system'] = long(row[2])
            elif line.find('Recovery system     ') == 0:
                #   Recovery system     0      (0 + 0)
                results['Innodb_mem_recovery_system'] = long(row[2])
            elif line.find('Threads             ') == 0:
                #   Threads             409336         (406936 + 2400)
                results['Innodb_mem_thread_hash'] = long(row[1])
            elif line.find("Buffer pool size ") == 0:
                # The " " after size is necessary to avoid matching the wrong line:
                # Buffer pool size        1769471
                # Buffer pool size, bytes 28991012864
                results['Innodb_buffer_pool_pages_total'] = long(row[3])
            elif line.find("Free buffers") == 0:
                # Free buffers            0
                results['Innodb_buffer_pool_pages_free'] = long(row[2])
            elif line.find("Database pages") == 0:
                # Database pages          1696503
                results['Innodb_buffer_pool_pages_data'] = long(row[2])
            elif line.find("Modified db pages") == 0:
                # Modified db pages       160602
                results['Innodb_buffer_pool_pages_dirty'] = long(row[3])
            elif line.find("Pages read ahead") == 0:
                # Must do this BEFORE the next test, otherwise it'll get fooled by this
                # line from the new plugin:
                # Pages read ahead 0.00/s, evicted without access 0.06/s
                pass
            elif line.find("Pages read") == 0:
                # Pages read 15240822, created 1770238, written 21705836
                results['Innodb_pages_read'] = long(row[2])
                results['Innodb_pages_created'] = long(row[4])
                results['Innodb_pages_written'] = long(row[6])

            # ROW OPERATIONS
            elif line.find('Number of rows inserted') == 0:
                # Number of rows inserted 50678311, updated 66425915, deleted
                # 20605903, read 454561562
                results['Innodb_rows_inserted'] = long(row[4])
                results['Innodb_rows_updated'] = long(row[6])
                results['Innodb_rows_deleted'] = long(row[8])
                results['Innodb_rows_read'] = long(row[10])
            elif line.find(" queries inside InnoDB, ") > 0:
                # 0 queries inside InnoDB, 0 queries in queue
                results['Innodb_queries_inside'] = long(row[0])
                results['Innodb_queries_queued'] = long(row[4])

            prev_line = line

        # We need to calculate this metric separately
        results['Innodb_checkpoint_age'] = results[
            'Innodb_lsn_current'] - results['Innodb_lsn_last_checkpoint']

        # Finally we change back the metrics values to string to make the values
        # consistent with how they are reported by SHOW GLOBAL STATUS
        for metric, value in results.iteritems():
            results[metric] = str(value)

        return results

# (C) Datadog, Inc. 2010-2016
# (C) Datadog, Inc. Patrick Galbraith <patg@patg.net> 2013
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import re
import traceback
from contextlib import closing, contextmanager
from collections import defaultdict

# 3p
import pymysql
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# project
from config import _is_affirmative
from checks import AgentCheck

GAUGE = "gauge"
RATE = "rate"
COUNT = "count"
MONOTONIC = "monotonic_count"

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
    'Max_used_connections': ('mysql.net.max_connections', GAUGE),
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
    'Table_locks_waited_rate': ('mysql.performance.table_locks_waited.rate', RATE),
    # Temporary Table Metrics
    'Created_tmp_tables': ('mysql.performance.created_tmp_tables', RATE),
    'Created_tmp_disk_tables': ('mysql.performance.created_tmp_disk_tables', RATE),
    'Created_tmp_files': ('mysql.performance.created_tmp_files', RATE),
    # Thread Metrics
    'Threads_connected': ('mysql.performance.threads_connected', GAUGE),
    'Threads_running': ('mysql.performance.threads_running', GAUGE),
    # MyISAM Metrics
    'Key_buffer_bytes_unflushed': ('mysql.myisam.key_buffer_bytes_unflushed', GAUGE),
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
    'Handler_prepare': ('mysql.performance.handler_prepare', RATE),
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
    'Qcache_total_blocks': ('mysql.performance.qcache_total_blocks', GAUGE),
    'Qcache_free_blocks': ('mysql.performance.qcache_free_blocks', GAUGE),
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
    'Table_locks_immediate': ('mysql.performance.table_locks_immediate', GAUGE),
    'Table_locks_immediate_rate': ('mysql.performance.table_locks_immediate.rate', RATE),
    'Threads_cached': ('mysql.performance.threads_cached', GAUGE),
    'Threads_created': ('mysql.performance.threads_created', MONOTONIC)
}

# Status Vars added in Mysql 5.6.6
OPTIONAL_STATUS_VARS_5_6_6 = {
    'Table_open_cache_hits': ('mysql.performance.table_cache_hits', RATE),
    'Table_open_cache_misses': ('mysql.performance.table_cache_misses', RATE),
}

# Will collect if [extra_innodb_metrics] is True
OPTIONAL_INNODB_VARS = {
    'Innodb_active_transactions': ('mysql.innodb.active_transactions', GAUGE),
    'Innodb_buffer_pool_bytes_data': ('mysql.innodb.buffer_pool_data', GAUGE),
    'Innodb_buffer_pool_pages_data': ('mysql.innodb.buffer_pool_pages_data', GAUGE),
    'Innodb_buffer_pool_pages_dirty': ('mysql.innodb.buffer_pool_pages_dirty', GAUGE),
    'Innodb_buffer_pool_pages_flushed': ('mysql.innodb.buffer_pool_pages_flushed', RATE),
    'Innodb_buffer_pool_pages_free': ('mysql.innodb.buffer_pool_pages_free', GAUGE),
    'Innodb_buffer_pool_pages_total': ('mysql.innodb.buffer_pool_pages_total', GAUGE),
    'Innodb_buffer_pool_read_ahead': ('mysql.innodb.buffer_pool_read_ahead', RATE),
    'Innodb_buffer_pool_read_ahead_evicted': ('mysql.innodb.buffer_pool_read_ahead_evicted', RATE),
    'Innodb_buffer_pool_read_ahead_rnd': ('mysql.innodb.buffer_pool_read_ahead_rnd', GAUGE),
    'Innodb_buffer_pool_wait_free': ('mysql.innodb.buffer_pool_wait_free', MONOTONIC),
    'Innodb_buffer_pool_write_requests': ('mysql.innodb.buffer_pool_write_requests', RATE),
    'Innodb_checkpoint_age': ('mysql.innodb.checkpoint_age', GAUGE),
    'Innodb_current_transactions': ('mysql.innodb.current_transactions', GAUGE),
    'Innodb_data_fsyncs': ('mysql.innodb.data_fsyncs', RATE),
    'Innodb_data_pending_fsyncs': ('mysql.innodb.data_pending_fsyncs', GAUGE),
    'Innodb_data_pending_reads': ('mysql.innodb.data_pending_reads', GAUGE),
    'Innodb_data_pending_writes': ('mysql.innodb.data_pending_writes', GAUGE),
    'Innodb_data_read': ('mysql.innodb.data_read', RATE),
    'Innodb_data_written': ('mysql.innodb.data_written', RATE),
    'Innodb_dblwr_pages_written': ('mysql.innodb.dblwr_pages_written', RATE),
    'Innodb_dblwr_writes': ('mysql.innodb.dblwr_writes', RATE),
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
    'Innodb_os_log_pending_fsyncs': ('mysql.innodb.os_log_pending_fsyncs', GAUGE),
    'Innodb_os_log_pending_writes': ('mysql.innodb.os_log_pending_writes', GAUGE),
    'Innodb_os_log_written': ('mysql.innodb.os_log_written', RATE),
    'Innodb_pages_created': ('mysql.innodb.pages_created', RATE),
    'Innodb_pages_read': ('mysql.innodb.pages_read', RATE),
    'Innodb_pages_written': ('mysql.innodb.pages_written', RATE),
    'Innodb_pending_aio_log_ios': ('mysql.innodb.pending_aio_log_ios', GAUGE),
    'Innodb_pending_aio_sync_ios': ('mysql.innodb.pending_aio_sync_ios', GAUGE),
    'Innodb_pending_buffer_pool_flushes': ('mysql.innodb.pending_buffer_pool_flushes', GAUGE),
    'Innodb_pending_checkpoint_writes': ('mysql.innodb.pending_checkpoint_writes', GAUGE),
    'Innodb_pending_ibuf_aio_reads': ('mysql.innodb.pending_ibuf_aio_reads', GAUGE),
    'Innodb_pending_log_flushes': ('mysql.innodb.pending_log_flushes', GAUGE),
    'Innodb_pending_log_writes': ('mysql.innodb.pending_log_writes', GAUGE),
    'Innodb_pending_normal_aio_reads': ('mysql.innodb.pending_normal_aio_reads', GAUGE),
    'Innodb_pending_normal_aio_writes': ('mysql.innodb.pending_normal_aio_writes', GAUGE),
    'Innodb_queries_inside': ('mysql.innodb.queries_inside', GAUGE),
    'Innodb_queries_queued': ('mysql.innodb.queries_queued', GAUGE),
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

GALERA_VARS = {
    'wsrep_cluster_size': ('mysql.galera.wsrep_cluster_size', GAUGE),
    'wsrep_local_recv_queue_avg': ('mysql.galera.wsrep_local_recv_queue_avg', GAUGE),
    'wsrep_flow_control_paused': ('mysql.galera.wsrep_flow_control_paused', GAUGE),
    'wsrep_cert_deps_distance': ('mysql.galera.wsrep_cert_deps_distance', GAUGE),
    'wsrep_local_send_queue_avg': ('mysql.galera.wsrep_local_send_queue_avg', GAUGE),
}

PERFORMANCE_VARS = {
    'query_run_time_avg': ('mysql.performance.query_run_time.avg', GAUGE),
    'perf_digest_95th_percentile_avg_us': ('mysql.performance.digest_95th_percentile.avg_us', GAUGE),
}

SCHEMA_VARS = {
    'information_schema_size': ('mysql.info.schema.size', GAUGE),
}

REPLICA_VARS = {
    'Seconds_Behind_Master': ('mysql.replication.seconds_behind_master', GAUGE),
    'Slaves_connected': ('mysql.replication.slaves_connected', COUNT),
}

SYNTHETIC_VARS = {
    'Qcache_utilization': ('mysql.performance.qcache.utilization', GAUGE),
    'Qcache_instant_utilization': ('mysql.performance.qcache.utilization.instant', GAUGE),
}


class MySql(AgentCheck):
    SERVICE_CHECK_NAME = 'mysql.can_connect'
    SLAVE_SERVICE_CHECK_NAME = 'mysql.replication.slave_running'
    MAX_CUSTOM_QUERIES = 20

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.mysql_version = {}
        self.qcache_stats = {}

    def get_library_versions(self):
        return {"pymysql": pymysql.__version__}

    def check(self, instance):
        host, port, user, password, mysql_sock, defaults_file, tags, options, queries, ssl = \
            self._get_config(instance)

        self._set_qcache_stats()

        if (not host or not user) and not defaults_file:
            raise Exception("Mysql host and user are needed.")

        with self._connect(host, port, mysql_sock, user,
                           password, defaults_file, ssl) as db:
            try:
                # Metadata collection
                self._collect_metadata(db, host)

                # Metric collection
                self._collect_metrics(host, db, tags, options, queries)
                self._collect_system_metrics(host, db, tags)

                # keeping track of these:
                self._put_qcache_stats()

            except Exception as e:
                self.log.exception("error!")
                raise e

    def _get_config(self, instance):
        self.host = instance.get('server', '')
        self.port = int(instance.get('port', 0))
        self.mysql_sock = instance.get('sock', '')
        self.defaults_file = instance.get('defaults_file', '')
        user = instance.get('user', '')
        password = instance.get('pass', '')
        tags = instance.get('tags', [])
        options = instance.get('options', {})
        queries = instance.get('queries', [])
        ssl = instance.get('ssl', {})

        return (self.host, self.port, user, password, self.mysql_sock,
                self.defaults_file, tags, options, queries, ssl)

    def _set_qcache_stats(self):
        host_key = self._get_host_key()
        qcache_st = self.qcache_stats.get(host_key, (None, None, None))

        self._qcache_hits = qcache_st[0]
        self._qcache_inserts = qcache_st[1]
        self._qcache_not_cached = qcache_st[2]

    def _put_qcache_stats(self):
        host_key = self._get_host_key()
        self.qcache_stats[host_key] = (
            self._qcache_hits,
            self._qcache_inserts,
            self._qcache_not_cached
        )

    def _get_host_key(self):
        if self.defaults_file:
            return self.defaults_file

        hostkey = self.host
        if self.mysql_sock:
            hostkey = "{0}:{1}".format(hostkey, self.mysql_sock)
        elif self.port:
            hostkey = "{0}:{1}".format(hostkey, self.port)

        return hostkey

    @contextmanager
    def _connect(self, host, port, mysql_sock, user, password, defaults_file, ssl):
        self.service_check_tags = [
            'server:%s' % (mysql_sock if mysql_sock != '' else host),
            'port:%s' % ('unix_socket' if port == 0 else port)
        ]

        db = None
        try:
            ssl = dict(ssl) if ssl else None

            if defaults_file != '':
                db = pymysql.connect(read_default_file=defaults_file, ssl=ssl)
            elif mysql_sock != '':
                self.service_check_tags = [
                    'server:{0}'.format(mysql_sock),
                    'port:unix_socket'
                ]
                db = pymysql.connect(
                    unix_socket=mysql_sock,
                    user=user,
                    passwd=password
                )
            elif port:
                db = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    passwd=password,
                    ssl=ssl
                )
            else:
                db = pymysql.connect(
                    host=host,
                    user=user,
                    passwd=password,
                    ssl=ssl
                )
            self.log.debug("Connected to MySQL")
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=self.service_check_tags)
            yield db
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=self.service_check_tags)
            raise
        finally:
            if db:
                db.close()

    def _collect_metrics(self, host, db, tags, options, queries):

        # Get aggregate of all VARS we want to collect
        metrics = STATUS_VARS

        # collect results from db
        results = self._get_stats_from_status(db)
        results.update(self._get_stats_from_variables(db))

        if (not _is_affirmative(options.get('disable_innodb_metrics', False)) and self._is_innodb_engine_enabled(db)):
            results.update(self._get_stats_from_innodb_status(db))

            innodb_keys = [
                'Innodb_page_size',
                'Innodb_buffer_pool_pages_data',
                'Innodb_buffer_pool_pages_dirty',
                'Innodb_buffer_pool_pages_total',
                'Innodb_buffer_pool_pages_free',
            ]

            for inno_k in innodb_keys:
                results[inno_k] = self._collect_scalar(inno_k, results)

            try:
                innodb_page_size = results['Innodb_page_size']
                innodb_buffer_pool_pages_used = results['Innodb_buffer_pool_pages_total'] - \
                    results['Innodb_buffer_pool_pages_free']

                if 'Innodb_buffer_pool_bytes_data' not in results:
                    results[
                        'Innodb_buffer_pool_bytes_data'] = results['Innodb_buffer_pool_pages_data'] * innodb_page_size

                if 'Innodb_buffer_pool_bytes_dirty' not in results:
                    results[
                        'Innodb_buffer_pool_bytes_dirty'] = results['Innodb_buffer_pool_pages_dirty'] * innodb_page_size

                if 'Innodb_buffer_pool_bytes_free' not in results:
                    results[
                        'Innodb_buffer_pool_bytes_free'] = results['Innodb_buffer_pool_pages_free'] * innodb_page_size

                if 'Innodb_buffer_pool_bytes_total' not in results:
                    results[
                        'Innodb_buffer_pool_bytes_total'] = results['Innodb_buffer_pool_pages_total'] * innodb_page_size

                if 'Innodb_buffer_pool_pages_utilization' not in results:
                    results['Innodb_buffer_pool_pages_utilization'] = innodb_buffer_pool_pages_used / \
                        results['Innodb_buffer_pool_pages_total']

                if 'Innodb_buffer_pool_bytes_used' not in results:
                    results[
                        'Innodb_buffer_pool_bytes_used'] = innodb_buffer_pool_pages_used * innodb_page_size
            except (KeyError, TypeError) as e:
                self.log.error("Not all InnoDB buffer pool metrics are available, unable to compute: {0}".format(e))

            if _is_affirmative(options.get('extra_innodb_metrics', False)):
                self.log.debug("Collecting Extra Innodb Metrics")
                metrics.update(OPTIONAL_INNODB_VARS)

        # Binary log statistics
        if self._get_variable_enabled(results, 'log_bin'):
            results[
                'Binlog_space_usage_bytes'] = self._get_binary_log_stats(db)

        # Compute key cache utilization metric
        key_blocks_unused = self._collect_scalar('Key_blocks_unused', results)
        key_cache_block_size = self._collect_scalar('key_cache_block_size', results)
        key_buffer_size = self._collect_scalar('key_buffer_size', results)
        results['Key_buffer_size'] = key_buffer_size

        try:
            key_cache_utilization = 1 - ((key_blocks_unused * key_cache_block_size) / key_buffer_size)

            results['Key_buffer_bytes_used'] = self._collect_scalar(
                'Key_blocks_used', results) * key_cache_block_size
            results['Key_buffer_bytes_unflushed'] = self._collect_scalar(
                'Key_blocks_not_flushed', results) * key_cache_block_size
            results['Key_cache_utilization'] = key_cache_utilization
        except TypeError as e:
            self.log.error("Not all Key metrics are available, unable to compute: {0}".format(e))

        metrics.update(VARIABLES_VARS)
        metrics.update(INNODB_VARS)
        metrics.update(BINLOG_VARS)

        if _is_affirmative(options.get('extra_status_metrics', False)):
            self.log.debug("Collecting Extra Status Metrics")
            metrics.update(OPTIONAL_STATUS_VARS)

            if self._version_compatible(db, host, "5.6.6"):
                metrics.update(OPTIONAL_STATUS_VARS_5_6_6)

        if _is_affirmative(options.get('galera_cluster', False)):
            # already in result-set after 'SHOW STATUS' just add vars to collect
            self.log.debug("Collecting Galera Metrics.")
            metrics.update(GALERA_VARS)

        performance_schema_enabled = self._get_variable_enabled(results, 'performance_schema')
        if _is_affirmative(options.get('extra_performance_metrics', False)) and \
                self._version_compatible(db, host, "5.6.0") and \
                performance_schema_enabled:
            # report avg query response time per schema to Datadog
            results['perf_digest_95th_percentile_avg_us'] = self._get_query_exec_time_95th_us(db)
            results['query_run_time_avg'] = self._query_exec_time_per_schema(db)
            metrics.update(PERFORMANCE_VARS)

        if _is_affirmative(options.get('schema_size_metrics', False)):
            # report avg query response time per schema to Datadog
            results['information_schema_size'] = self._query_size_per_schema(db)
            metrics.update(SCHEMA_VARS)

        if _is_affirmative(options.get('replication', False)):
            # Get replica stats
            results.update(self._get_replica_stats(db))
            results.update(self._get_slave_status(db))
            metrics.update(REPLICA_VARS)

            # get slave running form global status page
            slave_running_status = AgentCheck.UNKNOWN
            slave_running = self._collect_string('Slave_running', results)
            binlog_running = results.get('Binlog_enabled', False)
            # slaves will only be collected iff user has PROCESS privileges.
            slaves = self._collect_scalar('Slaves_connected', results)

            # MySQL 5.7.x might not have 'Slave_running'. See: https://bugs.mysql.com/bug.php?id=78544
            # look at replica vars collected at the top of if-block
            if self._version_compatible(db, host, "5.7.0"):
                slave_io_running = self._collect_string('Slave_IO_Running', results)
                slave_sql_running = self._collect_string('Slave_SQL_Running', results)
                if slave_io_running:
                    slave_io_running = (slave_io_running.lower().strip() == "yes")
                if slave_sql_running:
                    slave_sql_running = (slave_sql_running.lower().strip() == "yes")

                if not (slave_io_running is None and slave_sql_running is None):
                    if slave_io_running and slave_sql_running:
                        slave_running_status = AgentCheck.OK
                    elif not slave_io_running and not slave_sql_running:
                        slave_running_status = AgentCheck.CRITICAL
                    else:
                        # not everything is running smoothly
                        slave_running_status = AgentCheck.WARNING

            # if we don't yet have a status - inspect
            if slave_running_status == AgentCheck.UNKNOWN:
                if self._is_master(slaves, binlog_running):  # master
                    if slaves > 0 and binlog_running:
                        slave_running_status = AgentCheck.OK
                    else:
                        slave_running_status = AgentCheck.WARNING
                elif slave_running:  # slave (or standalone)
                    if slave_running.lower().strip() == 'on':
                        slave_running_status = AgentCheck.OK
                    else:
                        slave_running_status = AgentCheck.CRITICAL

            # deprecated in favor of service_check("mysql.replication.slave_running")
            self.gauge(self.SLAVE_SERVICE_CHECK_NAME, (1 if slave_running_status == AgentCheck.OK else 0), tags=tags)
            self.service_check(self.SLAVE_SERVICE_CHECK_NAME, slave_running_status, tags=self.service_check_tags)

        # "synthetic" metrics
        metrics.update(SYNTHETIC_VARS)
        self._compute_synthetic_results(results)

        # remove uncomputed metrics
        for k in SYNTHETIC_VARS:
            if k not in results:
                metrics.pop(k, None)

        # add duped metrics - reporting some as both rate and gauge
        dupes = [('Table_locks_waited', 'Table_locks_waited_rate'),
                 ('Table_locks_immediate', 'Table_locks_immediate_rate')]
        for src, dst in dupes:
            if src in results:
                results[dst] = results[src]

        self._submit_metrics(metrics, results, tags)

        # Collect custom query metrics
        # Max of 20 queries allowed
        if isinstance(queries, list):
            for index, check in enumerate(queries[:self.MAX_CUSTOM_QUERIES]):
                total_tags = tags + check.get('tags', [])
                self._collect_dict(check['type'], {check['field']: check['metric']}, check['query'], db, tags=total_tags)

            if len(queries) > self.MAX_CUSTOM_QUERIES:
                self.warning("Maximum number (%s) of custom queries reached.  Skipping the rest."
                             % self.MAX_CUSTOM_QUERIES)


    def _is_master(self, slaves, binlog):
        if slaves > 0 or binlog:
            return True

        return False


    def _collect_metadata(self, db, host):
        version = self._get_version(db, host)
        self.service_metadata('version', ".".join(version))

    def _submit_metrics(self, variables, dbResults, tags):
        for variable, metric in variables.iteritems():
            metric_name, metric_type = metric
            for tag, value in self._collect_all_scalars(variable, dbResults):
                metric_tags = list(tags)
                if tag:
                    metric_tags.append(tag)
                if value is not None:
                    if metric_type == RATE:
                        self.rate(metric_name, value, tags=metric_tags)
                    elif metric_type == GAUGE:
                        self.gauge(metric_name, value, tags=metric_tags)
                    elif metric_type == COUNT:
                        self.count(metric_name, value, tags=metric_tags)
                    elif metric_type == MONOTONIC:
                        self.monotonic_count(metric_name, value, tags=metric_tags)

    def _version_compatible(self, db, host, compat_version):
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number

        try:
            mysql_version = self._get_version(db, host)
        except Exception, e:
            self.warning("Cannot compute mysql version, assuming it's older.: %s"
                         % str(e))
            return False
        self.log.debug("MySQL version %s" % mysql_version)

        patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))
        version = (int(mysql_version[0]), int(mysql_version[1]), patchlevel)

        return version > compat_version

    def _get_version(self, db, host):
        hostkey = self._get_host_key()
        if hostkey in self.mysql_version:
            version = self.mysql_version[hostkey]
            return version

        # Get MySQL version
        with closing(db.cursor()) as cursor:
            cursor.execute('SELECT VERSION()')
            result = cursor.fetchone()

            # Version might include a description e.g. 4.1.26-log.
            # See
            # http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
            version = result[0].split('-')
            version = version[0].split('.')
            self.mysql_version[hostkey] = version
            return version

    def _collect_all_scalars(self, key, dictionary):
        if key not in dictionary or dictionary[key] is None:
            yield None, None
        elif isinstance(dictionary[key], dict):
            for tag, _ in dictionary[key].iteritems():
                yield tag, self._collect_type(tag, dictionary[key], float)
        else:
            yield None, self._collect_type(key, dictionary, float)

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
            with closing(db.cursor()) as cursor:
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
                            col_idx = [d[0].lower() for d in cursor.description].index(field.lower())
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
            self.log.debug("System metrics for mysql w\ pid: %s" % pid)
            # At last, get mysql cpu data out of psutil or procfs

            try:
                ucpu, scpu = None, None
                if PSUTIL_AVAILABLE:
                    proc = psutil.Process(pid)

                    ucpu = proc.cpu_times()[0]
                    scpu = proc.cpu_times()[1]

                if ucpu and scpu:
                    self.rate("mysql.performance.user_time", ucpu, tags=tags)
                    # should really be system_time
                    self.rate("mysql.performance.kernel_time", scpu, tags=tags)
                    self.rate("mysql.performance.cpu_time", ucpu+scpu, tags=tags)

            except Exception:
                self.warning("Error while reading mysql (pid: %s) procfs data\n%s"
                             % (pid, traceback.format_exc()))

    def _get_server_pid(self, db):
        pid = None

        # Try to get pid from pid file, it can fail for permission reason
        pid_file = None
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW VARIABLES LIKE 'pid_file'")
                pid_file = cursor.fetchone()[1]
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
        if pid is None and PSUTIL_AVAILABLE:
            try:
                for proc in psutil.process_iter():
                    if proc.name() == "mysqld":
                        pid = proc.pid
            except Exception:
                self.log.exception("Error while fetching mysql pid from psutil")

        return pid

    def _get_stats_from_status(self, db):
        with closing(db.cursor()) as cursor:
            cursor.execute("SHOW /*!50002 GLOBAL */ STATUS;")
            results = dict(cursor.fetchall())

            return results

    def _get_stats_from_variables(self, db):
        with closing(db.cursor()) as cursor:
            cursor.execute("SHOW GLOBAL VARIABLES;")
            results = dict(cursor.fetchall())

            return results

    def _get_binary_log_stats(self, db):
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW BINARY LOGS;")
                master_logs = dict(cursor.fetchall())

                binary_log_space = 0
                for key, value in master_logs.iteritems():
                    binary_log_space += value

                return binary_log_space
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the BINARY LOGS (must grant REPLICATION CLIENT): %s" % str(e))
            return None

    def _is_innodb_engine_enabled(self, db):
        # Whether InnoDB engine is available or not can be found out either
        # from the output of SHOW ENGINES or from information_schema.ENGINES
        # table. Later is choosen because that involves no string parsing.
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(
                    "select engine from information_schema.ENGINES where engine='InnoDB' and \
                    support != 'no' and support != 'disabled'"
                )

                return (cursor.rowcount > 0)

        except (pymysql.err.InternalError, pymysql.err.OperationalError, pymysql.err.NotSupportedError) as e:
            self.warning("Possibly innodb stats unavailable - error querying engines table: %s" % str(e))
            return False

    def _get_replica_stats(self, db):
        try:
            with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
                replica_results = {}
                cursor.execute("SHOW SLAVE STATUS;")
                slave_results = cursor.fetchone()
                if slave_results:
                    replica_results.update(slave_results)
                cursor.execute("SHOW MASTER STATUS;")
                binlog_results = cursor.fetchone()
                if binlog_results:
                    replica_results.update({'Binlog_enabled': True})

                return replica_results

        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error getting replication status (must grant REPLICATION CLIENT): %s" % str(e))
            return {}

    def _get_slave_status(self, db, nonblocking=True):
        try:
            with closing(db.cursor()) as cursor:
                # querying threads instead of PROCESSLIST to avoid mutex impact on
                # performance.
                if nonblocking:
                    cursor.execute("SELECT THREAD_ID, NAME FROM performance_schema.threads WHERE NAME LIKE '%worker'")
                else:
                    cursor.execute("SELECT * FROM INFORMATION_SCHEMA.PROCESSLIST WHERE COMMAND LIKE '%Binlog dump%'")
                slave_results = cursor.fetchall()
                slaves = 0
                for row in slave_results:
                    slaves += 1

                return {'Slaves_connected': slaves}

        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Privileges error accessing the process tables (must grant PROCESS): %s" % str(e))
            return {}

    def _get_stats_from_innodb_status(self, db):
        # There are a number of important InnoDB metrics that are reported in
        # InnoDB status but are not otherwise present as part of the STATUS
        # variables in MySQL. Majority of these metrics are reported though
        # as a part of STATUS variables in Percona Server and MariaDB.
        # Requires querying user to have PROCESS privileges.
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute("SHOW /*!50000 ENGINE*/ INNODB STATUS")
                innodb_status = cursor.fetchone()
                innodb_status_text = innodb_status[2]
        except (pymysql.err.InternalError, pymysql.err.OperationalError, pymysql.err.NotSupportedError) as e:
            self.warning("Privilege error or engine unavailable accessing the INNODB status \
                         tables (must grant PROCESS): %s" % str(e))
            return {}

        results = defaultdict(int)

        # Here we now parse InnoDB STATUS one line at a time
        # This is heavily inspired by the Percona monitoring plugins work
        txn_seen = False
        prev_line = ''

        for line in innodb_status_text.splitlines():
            line = line.strip()
            row = re.split(" +", line)
            row = [item.strip(',') for item in row]
            row = [item.strip(';') for item in row]
            row = [item.strip('[') for item in row]
            row = [item.strip(']') for item in row]

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
                # or Pending normal aio reads: [0, 0, 0, 0] , aio writes: [0, 0, 0, 0] ,
                # or Pending normal aio reads: 0 [0, 0, 0, 0] , aio writes: 0 [0, 0, 0, 0] ,
                if len(row) == 16:
                    results['Innodb_pending_normal_aio_reads'] = (long(row[4]) + long(row[5]) +
                                                                  long(row[6]) + long(row[7]))
                    results['Innodb_pending_normal_aio_writes'] = (long(row[11]) + long(row[12]) +
                                                                   long(row[13]) + long(row[14]))
                elif len(row) == 18:
                    results['Innodb_pending_normal_aio_reads'] = long(row[4])
                    results['Innodb_pending_normal_aio_writes'] = long(row[12])
                else:
                    results['Innodb_pending_normal_aio_reads'] = long(row[4])
                    results['Innodb_pending_normal_aio_writes'] = long(row[7])
            elif line.find('ibuf aio reads') == 0:
                #  ibuf aio reads: 0, log i/o's: 0, sync i/o's: 0
                #  or ibuf aio reads:, log i/o's:, sync i/o's:
                if len(row) == 10:
                    results['Innodb_pending_ibuf_aio_reads'] = long(row[3])
                    results['Innodb_pending_aio_log_ios'] = long(row[6])
                    results['Innodb_pending_aio_sync_ios'] = long(row[9])
                elif len(row) == 7:
                    results['Innodb_pending_ibuf_aio_reads'] = 0
                    results['Innodb_pending_aio_log_ios'] = 0
                    results['Innodb_pending_aio_sync_ios'] = 0
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
        try:
            results['Innodb_checkpoint_age'] = results[
                'Innodb_lsn_current'] - results['Innodb_lsn_last_checkpoint']
        except KeyError as e:
            self.log.error("Not all InnoDB LSN metrics available, unable to compute: {0}".format(e))

        # Finally we change back the metrics values to string to make the values
        # consistent with how they are reported by SHOW GLOBAL STATUS
        for metric, value in results.iteritems():
            results[metric] = str(value)

        return results

    def _get_variable_enabled(self, results, var):
        enabled = self._collect_string(var, results)
        return (enabled and enabled.lower().strip() == 'on')

    def _get_query_exec_time_95th_us(self, db):
        # Fetches the 95th percentile query execution time and returns the value
        # in microseconds

        sql_95th_percentile = """SELECT s2.avg_us avg_us,
                IFNULL(SUM(s1.cnt)/NULLIF((SELECT COUNT(*) FROM performance_schema.events_statements_summary_by_digest), 0), 0) percentile
            FROM (SELECT COUNT(*) cnt, ROUND(avg_timer_wait/1000000) AS avg_us
                    FROM performance_schema.events_statements_summary_by_digest
                    GROUP BY avg_us) AS s1
            JOIN (SELECT COUNT(*) cnt, ROUND(avg_timer_wait/1000000) AS avg_us
                    FROM performance_schema.events_statements_summary_by_digest
                    GROUP BY avg_us) AS s2
            ON s1.avg_us <= s2.avg_us
            GROUP BY s2.avg_us
            HAVING percentile > 0.95
            ORDER BY percentile
            LIMIT 1"""

        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(sql_95th_percentile)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the perf schema 'events_statements_summary_by_digest' table.")
                    return None

                row = cursor.fetchone()
                query_exec_time_95th_per = row[0]

                return query_exec_time_95th_per
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("95th percentile performance metrics unavailable at this time: %s" % str(e))
            return None

    def _query_exec_time_per_schema(self, db):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds

        sql_avg_query_run_time = """SELECT schema_name, ROUND((SUM(sum_timer_wait) / SUM(count_star)) / 1000000) AS avg_us
            FROM performance_schema.events_statements_summary_by_digest
            WHERE schema_name IS NOT NULL
            GROUP BY schema_name"""

        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(sql_avg_query_run_time)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the perf schema 'events_statements_summary_by_digest' table.")
                    return None

                schema_query_avg_run_time = {}
                for row in cursor.fetchall():
                    schema_name = str(row[0])
                    avg_us = long(row[1])

                    # set the tag as the dictionary key
                    schema_query_avg_run_time["schema:{0}".format(schema_name)] = avg_us

                return schema_query_avg_run_time
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Avg exec time performance metrics unavailable at this time: %s" % str(e))
            return None

    def _query_size_per_schema(self, db):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds

        sql_query_schema_size = """
        SELECT   table_schema,
                 SUM(data_length+index_length)/1024/1024 AS total_mb
                 FROM     information_schema.tables
                 GROUP BY table_schema;
        """

        try:
            with closing(db.cursor()) as cursor:
                cursor.execute(sql_query_schema_size)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the information schema 'tables' table.")
                    return None

                schema_size = {}
                for row in cursor.fetchall():
                    schema_name = str(row[0])
                    size = long(row[1])

                    # set the tag as the dictionary key
                    schema_size["schema:{0}".format(schema_name)] = size

                return schema_size
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Avg exec time performance metrics unavailable at this time: %s" % str(e))

        return {}

    def _compute_synthetic_results(self, results):
        if ('Qcache_hits' in results) and ('Qcache_inserts' in results) and ('Qcache_not_cached' in results):
            if not int(results['Qcache_hits']):
                results['Qcache_utilization'] = 0
            else:
                results['Qcache_utilization'] = (float(results['Qcache_hits']) /
                                                (int(results['Qcache_inserts']) +
                                                int(results['Qcache_not_cached']) +
                                                int(results['Qcache_hits'])) * 100)

            if all(v is not None for v in (self._qcache_hits, self._qcache_inserts, self._qcache_not_cached)):
                if not (int(results['Qcache_hits']) - self._qcache_hits):
                    results['Qcache_instant_utilization'] = 0
                else:
                    results['Qcache_instant_utilization'] = ((float(results['Qcache_hits']) - self._qcache_hits) /
                                                    ((int(results['Qcache_inserts']) - self._qcache_inserts) +
                                                    (int(results['Qcache_not_cached']) - self._qcache_not_cached) +
                                                    (int(results['Qcache_hits']) - self._qcache_hits)) * 100)

            # update all three, or none - for consistent samples.
            self._qcache_hits = int(results['Qcache_hits'])
            self._qcache_inserts = int(results['Qcache_inserts'])
            self._qcache_not_cached = int(results['Qcache_not_cached'])

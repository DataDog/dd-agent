# (C) Ovais Tariq <ovaistariq@twindb.com> 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from contextlib import closing, contextmanager
from collections import defaultdict

# 3p
import pymysql
import pymysql.cursors

# project
from checks import AgentCheck

GAUGE = "gauge"
RATE = "rate"
COUNT = "count"
MONOTONIC = "monotonic_count"

# ProxySQL Metrics
PROXYSQL_MYSQL_STATS_GLOBAL = {
    'Active_Transactions': ('proxysql.active_transactions', GAUGE),
    'Query_Processor_time_nsec': ('proxysql.query_processor_time_nsec', RATE),
    'Questions': ('proxysql.questions', RATE),
    'Slow_queries': ('proxysql.slow_queries', RATE),
    'SQLite3_memory_bytes': ('proxysql.sqlite3_memory_bytes', RATE),

    'Client_Connections_aborted': ('proxysql.client.connections_aborted', RATE),
    'Client_Connections_connected': ('proxysql.client.connections_connected', GAUGE),
    'Client_Connections_created': ('proxysql.client.connections_created', RATE),
    'Client_Connections_non_idle': ('proxysql.client.connections_non_idle', GAUGE),

    'ConnPool_get_conn_failure': ('proxysql.pool.conn_failure', RATE),
    'ConnPool_get_conn_immediate': ('proxysql.pool.conn_immediate', RATE),
    'ConnPool_get_conn_success': ('proxysql.pool.conn_success', RATE),
    'ConnPool_memory_bytes': ('proxysql.pool.memory_bytes', GAUGE),

    'mysql_backend_buffers_bytes': ('proxysql.mysql.backend_buffers_bytes', GAUGE),
    'mysql_frontend_buffers_bytes': ('proxysql.mysql.frontend_buffers_bytes', GAUGE),
    'mysql_session_internal_bytes': ('proxysql.mysql.session_internal_bytes', GAUGE),

    'Backend_query_time_nsec': ('proxysql.backend.query_time_nsec', RATE),
    'Queries_backends_bytes_recv': ('proxysql.backend.queries_bytes_recv', RATE),
    'Queries_backends_bytes_sent': ('proxysql.backend.queries_bytes_sent', RATE),

    'Server_Connections_aborted': ('proxysql.server.connections_aborted', RATE),
    'Server_Connections_connected': ('proxysql.server.connections_connected', GAUGE),
    'Server_Connections_created': ('proxysql.server.connections_created', RATE),
}

# ProxySQL metrics that we fetch by querying stats_mysql_commands_counters
PROXYSQL_MYSQL_STATS_COMMAND_COUNTERS = {
    'Query_sum_time': ('proxysql.performance.query_sum_time', RATE),
    'Query_count': ('proxysql.performance.query_count', RATE),
}

# ProxySQL metrics that we fetch by querying stats_mysql_connection_pool
PROXYSQL_CONNECTION_POOL_STATS = {
    'Connections_used': ('proxysql.pool.connections_used', GAUGE),
    'Connections_free': ('proxysql.pool.connections_free', GAUGE),
    'Connections_ok': ('proxysql.pool.connections_ok', RATE),
    'Connections_error': ('proxysql.pool.connections_error', RATE),
    'Queries': ('proxysql.pool.queries', RATE),
    'Bytes_data_sent': ('proxysql.pool.bytes_data_sent', RATE),
    'Bytes_data_recv': ('proxysql.pool.bytes_data_recv', RATE),
    'Latency_ms': ('proxysql.pool.latency_ms', GAUGE),
}


class ProxySQL(AgentCheck):
    SERVICE_CHECK_NAME = 'proxysql.can_connect'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def get_library_versions(self):
        return {"pymysql": pymysql.__version__}

    def check(self, instance):
        host, port, user, password, socket, tags, options, connect_timeout = self._get_config(instance)

        if not host or not port or not user or not password:
            raise Exception("ProxySQL host, port, user and password are needed")

        with self._connect(host, port, socket, user, password, connect_timeout) as conn:
            try:
                # Metric Collection
                self._collect_metrics(conn, tags, options)
            except Exception as e:
                self.log.exception("error!")
                raise e

    def _collect_metrics(self, conn, tags, options):
        """Collects all the different types of ProxySQL metrics and submits them to Datadog"""
        global_stats = self._get_global_stats(conn)
        for proxysql_metric_name, metric_details in PROXYSQL_MYSQL_STATS_GLOBAL.iteritems():
            metric_name, metric_type = metric_details
            metric_tags = list(tags)
            self._submit_metric(metric_name, metric_type, int(global_stats.get(proxysql_metric_name)), metric_tags)

        report_command_counters = options.get('extra_command_counter_metrics', True)
        if report_command_counters:
            command_counters = self._get_command_counters(conn)
            for proxysql_metric_name, metric_details in PROXYSQL_MYSQL_STATS_COMMAND_COUNTERS.iteritems():
                metric_name, metric_type = metric_details
                metric_tags = list(tags)
                self._submit_metric(metric_name, metric_type,
                                    int(command_counters.get(proxysql_metric_name)), metric_tags)

        report_conn_pool_stats = options.get('extra_connection_pool_metrics', True)
        if report_conn_pool_stats:
            conn_pool_stats = self._get_connection_pool_stats(conn)
            for proxysql_metric_name, metric_details in PROXYSQL_CONNECTION_POOL_STATS.iteritems():
                metric_name, metric_type = metric_details

                for metric in conn_pool_stats.get(proxysql_metric_name):
                    metric_tags = list(tags)
                    tag, value = metric
                    if tag:
                        metric_tags.append(tag)
                    self._submit_metric(metric_name, metric_type, int(value), metric_tags)

    def _get_global_stats(self, conn):
        """Fetch the global ProxySQL stats."""
        sql = 'SELECT * FROM stats.stats_mysql_global'

        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the stats schema 'stats_mysql_global' table.")
                    return None

                return {row['Variable_Name']: row['Variable_Value'] for row in cursor.fetchall()}
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("ProxySQL global stats unavailable at this time: %s" % str(e))
            return None

    def _get_command_counters(self, conn):
        """Fetch ProxySQL stats per command type."""
        sql = ('SELECT SUM(Total_Time_us) AS query_sum_time_us, '
               'SUM(Total_cnt) AS query_count '
               'FROM stats.stats_mysql_commands_counters')

        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the stats schema 'stats_mysql_commands_counters' table.")
                    return None

                row = cursor.fetchone()

                return {
                    'Query_sum_time': row['query_sum_time_us'],
                    'Query_count': row['query_count']
                }
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("ProxySQL commands_counters stats unavailable at this time: %s" % str(e))
            return None

    def _get_connection_pool_stats(self, conn):
        """Fetch ProxySQL connection pool stats"""
        sql = 'SELECT * FROM stats_mysql_connection_pool'

        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the stats schema 'stats_mysql_commands_counters' table.")
                    return None

                stats = defaultdict(list)
                for row in cursor.fetchall():
                    stats['Connections_used'].append(('proxysql_db_node:%s' % row['srv_host'], row['ConnUsed']))
                    stats['Connections_free'].append(('proxysql_db_node:%s' % row['srv_host'], row['ConnFree']))
                    stats['Connections_ok'].append(('proxysql_db_node:%s' % row['srv_host'], row['ConnOK']))
                    stats['Connections_error'].append(('proxysql_db_node:%s' % row['srv_host'], row['ConnERR']))
                    stats['Queries'].append(('proxysql_db_node:%s' % row['srv_host'], row['Queries']))
                    stats['Bytes_data_sent'].append(('proxysql_db_node:%s' % row['srv_host'], row['Bytes_data_sent']))
                    stats['Bytes_data_recv'].append(('proxysql_db_node:%s' % row['srv_host'], row['Bytes_data_recv']))

                    # https://github.com/sysown/proxysql/issues/882
                    # Latency_ms was actually returning values in microseconds
                    # ProxySQL v1.3.3 returns it with the correct key 'Latency_us'
                    latency_key = 'Latency_ms' if row.get('Latency_ms') else 'Latency_us'
                    stats['Latency_ms'].append(('proxysql_db_node:%s' % row['srv_host'],
                                                str(int(row[latency_key]) / 1000)))

                return stats
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("ProxySQL commands_counters stats unavailable at this time: %s" % str(e))
            return None

    @staticmethod
    def _get_config(instance):
        host = instance.get('server', '')
        port = int(instance.get('port', 0))
        socket = instance.get('sock', '')

        user = instance.get('user', '')
        password = str(instance.get('pass', ''))
        tags = instance.get('tags', [])
        options = instance.get('options', {})
        connect_timeout = instance.get('connect_timeout', None)

        return host, port, user, password, socket, tags, options, connect_timeout

    @contextmanager
    def _connect(self, host, port, socket, user, password, connect_timeout):
        self.service_check_tags = [
            'server:%s' % (socket if socket != '' else host),
            'port:%s' % ('unix_socket' if port == 0 else port)
        ]

        db = None
        try:
            if socket != '':
                self.service_check_tags = [
                    'server:{0}'.format(socket),
                    'port:unix_socket'
                ]
                db = pymysql.connect(
                    unix_socket=socket,
                    user=user,
                    passwd=password,
                    connect_timeout=connect_timeout,
                    cursorclass=pymysql.cursors.DictCursor
                )
            elif port:
                db = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    passwd=password,
                    connect_timeout=connect_timeout,
                    cursorclass=pymysql.cursors.DictCursor
                )
            else:
                db = pymysql.connect(
                    host=host,
                    user=user,
                    passwd=password,
                    connect_timeout=connect_timeout,
                    cursorclass=pymysql.cursors.DictCursor
                )
            self.log.debug("Connected to ProxySQL")
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

    def _submit_metric(self, metric_name, metric_type, metric_value, metric_tags):
        if metric_value is None:
            return

        if metric_type == RATE:
            self.rate(metric_name, metric_value, tags=metric_tags)
        elif metric_type == GAUGE:
            self.gauge(metric_name, metric_value, tags=metric_tags)
        elif metric_type == COUNT:
            self.count(metric_name, metric_value, tags=metric_tags)
        elif metric_type == MONOTONIC:
            self.monotonic_count(metric_name, metric_value, tags=metric_tags)

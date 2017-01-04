# (C) Ovais Tariq <ovaistariq@twindb.com> 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from contextlib import closing, contextmanager
from collections import defaultdict

# 3p
import pymysql
import pymysql.cursors
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# project
from checks import AgentCheck

GAUGE = "gauge"
RATE = "rate"
COUNT = "count"
MONOTONIC = "monotonic_count"

# ProxySQL Metrics
PROXYSQL_MYSQL_STATS_GLOBAL = {
    'Active_Transactions': GAUGE,
    'Backend_query_time_nsec': RATE,
    'Client_Connections_aborted': RATE,
    'Client_Connections_connected': GAUGE,
    'Client_Connections_created': RATE,
    'Client_Connections_non_idle': GAUGE,
    'ConnPool_get_conn_failure': RATE,
    'ConnPool_get_conn_immediate': RATE,
    'ConnPool_get_conn_success': RATE,
    'ConnPool_memory_bytes': GAUGE,
    'mysql_backend_buffers_bytes': GAUGE,
    'mysql_frontend_buffers_bytes': GAUGE,
    'mysql_session_internal_bytes': GAUGE,
    'Queries_backends_bytes_recv': RATE,
    'Queries_backends_bytes_sent': RATE,
    'Query_Processor_time_nsec': RATE,
    'Questions': RATE,
    'Server_Connections_aborted': RATE,
    'Server_Connections_connected': GAUGE,
    'Server_Connections_created': RATE,
    'Slow_queries': RATE,
    'SQLite3_memory_bytes': GAUGE,
}

# ProxySQL metrics that we fetch by querying stats_mysql_commands_counters
PROXYSQL_MYSQL_STATS_COMMAND_COUNTERS = {
    'Query_sum_time': RATE,
    'Query_count': RATE,
}

# ProxySQL metrics that we fetch by querying stats_mysql_connection_pool
PROXYSQL_CONNECTION_POOL_STATS = {
    'Connections_used': GAUGE,
    'Connections_free': GAUGE,
    'Connections_ok': RATE,
    'Connections_error': RATE,
    'Queries': RATE,
    'Bytes_data_sent': RATE,
    'Bytes_data_recv': RATE,
    'Latency_ms': GAUGE
}


class ProxySQL(AgentCheck):
    SERVICE_CHECK_NAME = 'proxysql.can_connect'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        self.host = None
        self.port = None
        self.socket = None

    def get_library_versions(self):
        return {"pymysql": pymysql.__version__}

    def check(self, instance):
        host, port, socket, user, password, tags, options, connect_timeout = self._get_config(instance)

        if not host or not port or not user or not password:
            raise Exception("ProxySQL host, port, user and password are needed")

        with self._connect(host, port, socket, user, password, connect_timeout) as conn:
            try:
                # Metric Collection
                self._collect_metrics(host, conn, tags, options)
            except Exception as e:
                self.log.exception("error!")
                raise e

    def _collect_metrics(self, host, conn, tags, options):
        """Collects all the different types of ProxySQL metrics and submits them to Datadog"""
        global_stats = self._get_global_stats(conn)
        for metric_name, metric_type in PROXYSQL_MYSQL_STATS_GLOBAL.iteritems():
            metric_tags = list(tags)
            self._submit_metric(metric_name, metric_type, int(global_stats.get(metric_name)), metric_tags)

        command_counters = self._get_command_counters(conn)
        for metric_name, metric_type in PROXYSQL_MYSQL_STATS_COMMAND_COUNTERS.iteritems():
            metric_tags = list(tags)
            self._submit_metric(metric_name, metric_type, int(command_counters.get(metric_name)), metric_tags)

        conn_pool_stats = self._get_connection_pool_stats(conn)
        for metric_name, metric_type in PROXYSQL_CONNECTION_POOL_STATS.iteritems():
            for metric in conn_pool_stats.get(metric_name):
                metric_tags = list(tags)
                for tag, value in metric.iteritems():
                    if tag:
                        metric_tags.append(tag)
                    self._submit_metric(metric_name, metric_type, value, metric_tags)

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
        sql = ('SELECT srv_host as Host, ConnUsed as Connections_used, '
               'ConnFree as Connections_free, ConnOK as Connections_ok, '
               'ConnERR as Connections_error, Queries, Bytes_data_sent, '
               'Bytes_data_recv, Latency_ms '
               'FROM stats_mysql_connection_pool')

        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(sql)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from the stats schema 'stats_mysql_commands_counters' table.")
                    return None

                stats = defaultdict(list)
                for row in cursor.fetchall():
                    stats['Connections_used'].append({'proxysql_db_node:%s' % row['Host']: row['Connections_used']})
                    stats['Connections_free'].append({'proxysql_db_node:%s' % row['Host']: row['Connections_free']})
                    stats['Connections_ok'].append({'proxysql_db_node:%s' % row['Host']: row['Connections_ok']})
                    stats['Connections_error'].append({'proxysql_db_node:%s' % row['Host']: row['Connections_error']})
                    stats['Queries'].append({'proxysql_db_node:%s' % row['Host']: row['Queries']})
                    stats['Bytes_data_sent'].append({'proxysql_db_node:%s' % row['Host']: row['Bytes_data_sent']})
                    stats['Bytes_data_recv'].append({'proxysql_db_node:%s' % row['Host']: row['Bytes_data_recv']})
                    stats['Latency_ms'].append({'proxysql_db_node:%s' % row['Host']: row['Latency_ms']})

                return stats
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("ProxySQL commands_counters stats unavailable at this time: %s" % str(e))
            return None

    def _get_config(self, instance):
        self.host = instance.get('server', '')
        self.port = int(instance.get('port', 0))
        self.socket = instance.get('sock', '')

        user = instance.get('user', '')
        password = str(instance.get('pass', ''))
        tags = instance.get('tags', [])
        options = instance.get('options', {})
        connect_timeout = instance.get('connect_timeout', None)

        return self.host, self.port, user, password, self.socket, tags, options, connect_timeout

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

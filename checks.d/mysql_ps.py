# stdlib
import subprocess
import os
import sys
import re
import traceback

# project
from checks import AgentCheck
from util import Platform

# 3rd party
import pymysql

GAUGE = "gauge"
RATE = "rate"

METRICS_MAP = {
    'Ps_digest_95th_percentile_by_avg_us': ('mysql.performance.query_run_time_95th_us', GAUGE)
}

class MySqlPS(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)

    def get_library_versions(self):
        return {"pymysql": pymysql.__version__}

    def check(self, instance):
        host, port, user, password, mysql_sock, defaults_file, tags, options = self._get_config(instance)

        if (not host or not user) and not defaults_file:
            raise Exception("Mysql host and user are needed.")

        db = self._connect(host, port, mysql_sock, user, password, defaults_file)

        # check that we are running the correct MySQL version
        if not self._version_greater_565(db, host):
            raise Exception("MySQL version >= 5.6.5 is required.")

        # Metric collection
        self._collect_metrics(host, db, tags, options)

    def _get_config(self, instance):
        host = instance.get('server', '')
        user = instance.get('user', '')
        port = int(instance.get('port', 0))
        password = instance.get('pass', '')
        mysql_sock = instance.get('sock', '')
        defaults_file = instance.get('defaults_file', '')
        tags = instance.get('tags', None)
        options = instance.get('options', {})

        return host, port, user, password, mysql_sock, defaults_file, tags, options

    def _connect(self, host, port, mysql_sock, user, password, defaults_file):
        if defaults_file != '':
            db = pymysql.connect(read_default_file=defaults_file)
        elif  mysql_sock != '':
            db = pymysql.connect(unix_socket=mysql_sock,
                                    user=user,
                                    passwd=password)
        elif port:
            db = pymysql.connect(host=host,
                                    port=port,
                                    user=user,
                                    passwd=password)
        else:
            db = pymysql.connect(host=host,
                                    user=user,
                                    passwd=password)
        self.log.debug("Connected to MySQL")

        return db

    def _collect_metrics(self, host, db, tags, options):
        mysql_metrics = dict()

        # Compute 95th percentile query execution time in microseconds across all queries
        mysql_metrics['Ps_digest_95th_percentile_by_avg_us'] = self._get_query_exec_time_95th_us(db)
        
        # Send the metrics to Datadog based on the type of the metric
        self._rate_or_gauge_statuses(METRICS_MAP, mysql_metrics, tags)

        # report avg query response time per schema to Datadog
        self._gauge_query_exec_time_per_schema(db, "mysql.performance.query_run_time_avg")

    def _rate_or_gauge_statuses(self, statuses, dbResults, tags):
        for status, metric in statuses.iteritems():
            metric_name, metric_type = metric
            value = self._collect_scalar(status, dbResults)
            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, tags=tags)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=tags)

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

        cursor = db.cursor()
        cursor.execute(sql_95th_percentile)

        if cursor.rowcount < 1:
            raise Exception("Failed to fetch record from the table performance_schema.events_statements_summary_by_digest")

        row = cursor.fetchone()
        query_exec_time_95th_per = row[0]

        cursor.close()
        del cursor

        return query_exec_time_95th_per

    def _gauge_query_exec_time_per_schema(self, db, metric_name):
        # Fetches the avg query execution time per schema and returns the
        # value in microseconds

        sql_avg_query_run_time = """SELECT schema_name, SUM(count_star) cnt, ROUND(AVG(avg_timer_wait)/1000000) AS avg_us 
            FROM performance_schema.events_statements_summary_by_digest 
            WHERE schema_name IS NOT NULL 
            GROUP BY schema_name"""

        cursor = db.cursor()
        cursor.execute(sql_avg_query_run_time)

        if cursor.rowcount < 1:
            raise Exception("Failed to fetch records from the table performance_schema.events_statements_summary_by_digest")

        schema_query_avg_run_time = {}
        for row in cursor.fetchall():
            schema_name = str(row[0])
            avg_us = long(row[2])

            self.gauge(metric_name, avg_us, tags=["schema:%s" % schema_name])

        cursor.close()
        del cursor

        return True

    def _get_query_first_seen_seconds(self, db):
        # Returns the number of seconds since any query was first executed

        query_first_seen_in_seconds = 0

        cursor = db.cursor()
        cursor.execute("select min(first_seen) from performance_schema.events_statements_summary_by_digest")

        if cursor.rowcount > 0:
            row = cursor.fetchone()
            query_first_seen_datetime = row[0]

            cursor.execute("select now()")
            row = cursor.fetchone()
            current_mysql_datetime = row[0]

            timedelta = current_mysql_datetime - query_first_seen_datetime
            query_first_seen_in_seconds = int(timedelta.total_seconds())

        cursor.close()
        del cursor

        return query_first_seen_in_seconds

    def _version_greater_565(self, db, host):
        # some of the performance_schema tables such as events_statements_%
        # tables were only introduced in MySQL 5.6.5. For reference see this
        # this link from the manual: 
        # http://dev.mysql.com/doc/refman/5.6/en/performance-schema-statement-digests.html
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number
        greater_565 = False
        try:
            mysql_version = self._get_version(db, host)
            self.log.debug("MySQL version %s" % mysql_version)

            major = int(mysql_version[0])
            minor = int(mysql_version[1])
            patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))

            if (major, minor, patchlevel) > (5, 6, 5):
                greater_565 = True

        except Exception, exception:
            self.warning("Cannot compute mysql version, assuming older than 5.6.5: %s" % str(exception))

        return greater_565

    def _get_version(self, db, host):
        # Get MySQL version
        cursor = db.cursor()
        cursor.execute('SELECT VERSION()')
        result = cursor.fetchone()
        cursor.close()
        del cursor
        # Version might include a description e.g. 4.1.26-log.
        # See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
        version = result[0].split('-')
        version = version[0].split('.')
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

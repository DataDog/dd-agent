import subprocess
import os
import sys
import re
from checks import AgentCheck

GAUGE = "gauge"
RATE = "rate"

QUERIES_COMMON = [
    ('mysql.net.connections', "SHOW STATUS LIKE 'Connections'", RATE),
    ('mysql.net.max_connections', "SHOW STATUS LIKE 'Max_used_connections'", GAUGE),
    ('mysql.performance.open_files', "SHOW STATUS LIKE 'Open_files'", GAUGE),
    ('mysql.performance.table_locks_waited', "SHOW STATUS LIKE 'Table_locks_waited'", GAUGE),
    ('mysql.performance.threads_connected', "SHOW STATUS LIKE 'Threads_connected'", GAUGE),
    ('mysql.innodb.data_reads', "SHOW STATUS LIKE 'Innodb_data_reads'", RATE),
    ('mysql.innodb.data_writes', "SHOW STATUS LIKE 'Innodb_data_writes'", RATE),
    ('mysql.innodb.os_log_fsyncs', "SHOW STATUS LIKE 'Innodb_os_log_fsyncs'", RATE),
    ('mysql.innodb.buffer_pool_size', "SHOW STATUS LIKE 'Innodb_data_reads'", RATE),
]

QUERIES_GREATER_502 = [
    ('mysql.performance.created_tmp_disk_tables', "SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables'", GAUGE),
    ('mysql.performance.slow_queries', "SHOW GLOBAL STATUS LIKE 'Slow_queries'", RATE),
    ('mysql.performance.questions', "SHOW GLOBAL STATUS LIKE 'Questions'", RATE),
    ('mysql.performance.queries', "SHOW GLOBAL STATUS LIKE 'Queries'", RATE),
]

QUERIES_OLDER_502 = [
    ('mysql.performance.created_tmp_disk_tables', "SHOW STATUS LIKE 'Created_tmp_disk_tables'", GAUGE),
    ('mysql.performance.slow_queries', "SHOW STATUS LIKE 'Slow_queries'", RATE),
    ('mysql.performance.questions', "SHOW STATUS LIKE 'Questions'", RATE),
    ('mysql.performance.queries', "SHOW STATUS LIKE 'Queries'", RATE),
]


class MySql(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.mysql_version = {}
        self.greater_502 = {}

    def check(self, instance):
        host, user, password, mysql_sock, tags, options = self._get_config(instance)

        if not host or not user:
            raise Exception("Mysql host and user are needed.")

        db = self._connect(host, mysql_sock, user, password)

        # Metric collection
        self._collect_metrics(host, db, tags, options)

    def _get_config(self, instance):
        host = instance['server']
        user = instance['user']
        password = instance.get('pass', '')
        mysql_sock = instance.get('sock', '')
        tags = instance.get('tags', None)
        options = instance.get('options', {})

        return host, user, password, mysql_sock, tags, options

    def _connect(self, host, mysql_sock, user, password):
        try:
            import MySQLdb
        except ImportError:
            raise Exception("Cannot import MySQLdb module. Check the instructions "
                "to install this module at https://app.datadoghq.com/account/settings#integrations/mysql")

        if  mysql_sock != '':
            db = MySQLdb.connect(unix_socket=mysql_sock,
                                    user=user,
                                    passwd=password)
        else:
            db = MySQLdb.connect(host=host,
                                    user=user,
                                    passwd=password)
        self.log.debug("Connected to MySQL")

        return db

    def _collect_metrics(self, host, db, tags, options):
        if self._version_greater_502(db, host):
            queries = QUERIES_GREATER_502 + QUERIES_COMMON
        else:
            queries = QUERIES_OLDER_502 + QUERIES_COMMON

        for metric_name, query, metric_type in queries:
            value = self._collect_scalar(query, db)
            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, tags=tags)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=tags)

        # Compute InnoDB buffer metrics
        page_size = self._collect_scalar("SHOW STATUS LIKE 'Innodb_page_size'", db)
        innodb_buffer_pool_pages_total = self._collect_scalar("SHOW STATUS LIKE 'Innodb_buffer_pool_pages_total'", db)
        innodb_buffer_pool_pages_free = self._collect_scalar("SHOW STATUS LIKE 'Innodb_buffer_pool_pages_free'", db)
        innodb_buffer_pool_pages_total = innodb_buffer_pool_pages_total * page_size
        innodb_buffer_pool_pages_free = innodb_buffer_pool_pages_free * page_size
        innodb_buffer_pool_pages_used = innodb_buffer_pool_pages_total - innodb_buffer_pool_pages_free

        self.gauge("mysql.innodb.buffer_pool_free", innodb_buffer_pool_pages_free, tags=tags)
        self.gauge("mysql.innodb.buffer_pool_used", innodb_buffer_pool_pages_used, tags=tags)
        self.gauge("mysql.innodb.buffer_pool_total", innodb_buffer_pool_pages_total, tags=tags)

        # Compute CPU metrics
        self._collect_procfs(tags, db)

        if 'galera_cluster' in options.keys() and options['galera_cluster']:
            value = self._collect_scalar("SHOW STATUS LIKE 'wsrep_cluster_size'", db)
            self.gauge('mysql.galera.wsrep_cluster_size', value, tags=tags)

        if 'replication' in options.keys() and options['replication']:
            self._collect_dict(GAUGE, {"Seconds_behind_master": "mysql.replication.seconds_behind_master"}, "SHOW SLAVE STATUS", db, tags=tags)

    def _version_greater_502(self, db, host):
        # show global status was introduced in 5.0.2
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number
        if host in self.greater_502:
            return self.greater_502[host]

        greater_502 = False
        try:
            mysql_version = self._get_version(db, host)
            self.log.debug("MySQL version %s" % mysql_version)

            major = int(mysql_version[0])
            minor = int(mysql_version[1])
            patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))

            if (major, minor, patchlevel) > (5, 0, 2):
                greater_502 = True

        except Exception, exception:
            self.warning("Cannot compute mysql version, assuming older than 5.0.2: %s" % str(exception))

        self.greater_502[host] = greater_502

        return greater_502

    def _get_version(self, db, host):
        if host in self.mysql_version:
            return self.mysql_version[host]

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
        self.mysql_version[host] = version
        return version

    def _collect_scalar(self, query, db):
        self.log.debug("Collecting data with %s" % (query))
        try:
            cursor = db.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            del cursor
            if result is None:
                self.log.debug("%s returned None" % query)
                return None
            self.log.debug("Collecting done, value %s" % result[1])
            return float(result[1])
        except Exception:
            self.log.exception("While running %s" % query)

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
                        col_idx = [d[0].lower() for d in cursor.description].index(field.lower())
                        if metric_type == GAUGE:
                            self.gauge(metric, float(result[col_idx]), tags=tags)
                        elif metric_type == RATE:
                            self.rate(metric, float(result[col_idx]), tags=tags)
                        else:
                            self.gauge(metric, float(result[col_idx]), tags=tags)
                    except ValueError:
                        self.log.exception("Cannot find %s in the columns %s" % (field, cursor.description))
            cursor.close()
            del cursor
        except Exception:
            self.log.debug("Error while running %s" % query)

    def _collect_procfs(self, tags, db):
        pid = self._get_server_pid(db)

        if pid is None:
            self.warning("Cannot compute advanced MySQL metrics; cannot find mysql pid")
        else:
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
                self.rate("mysql.performance.user_time", int((float(ucpu)/float(clk_tck)) * 100), tags=tags)
                self.rate("mysql.performance.kernel_time", int((float(kcpu)/float(clk_tck)) * 100), tags=tags)
            except Exception:
                self.warning("Error while reading mysql (pid: %s) procfs data" % pid)

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
                    ps = subprocess.Popen(['ps', '-C', 'mysqld', '-o', 'pid'], stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]
                    pslines = ps.split('\n')
                    # First line is header, second line is mysql pid
                    if len(pslines) > 1 and pslines[1] != '':
                        pid = int(pslines[1])

                elif sys.platform.startswith("darwin") or sys.platform.startswith("freebsd"):
                    # Get all processes, filter in python then
                    procs = subprocess.Popen(["ps", "-A", "-o", "pid,command"], stdout=subprocess.PIPE,
                                             close_fds=True).communicate()[0]
                    ps = [p for p in procs.split("\n") if "mysqld" in p]
                    if len(ps) > 0:
                        pid = int(ps[0].split()[0])
            except Exception:
                self.log.exception("Error while fetching mysql pid from ps")

        return pid

    @staticmethod
    def parse_agent_config(agent_config):
        if not agent_config.get('mysql_server'):
            return False

        return {
            'instances': [{
                'server': agent_config.get('mysql_server',''),
                'sock': agent_config.get('mysql_sock',''),
                'user': agent_config.get('mysql_user',''),
                'pass': agent_config.get('mysql_pass',''),
                'options': {'replication': True},
            }]
        }

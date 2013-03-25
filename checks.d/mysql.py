from checks import AgentCheck
import subprocess, os
import sys
import re

class MySql(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.mysqlVersion = None
        self.db = None

    def _collect_scalar(self, query):
        if self.db is not None:
            self.log.debug("Collecting data with %s" % (query))
            try:
                cursor = self.db.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                cursor.close()
                del cursor
                self.log.debug("Collecting done, value %s" % result[1])
                return float(result[1])
            except:
                if self.log is not None:
                    self.log.exception("While running %s" % query)

    def _collect_dict(self, mtype, field_metric_map, query, tags):
        """
        Query status and get a dictionary back.
        Extract each field out of the dictionary
        and stuff it in the corresponding metric.

        query: show status...
        field_metric_map: {"Seconds_behind_master": "mysqlSecondsBehindMaster"}
        """
        if self.db is not None:
            try:
                cursor = self.db.cursor()
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
                            if mtype == "gauge":
                                self.gage(metric, float(result[col_idx]), tags=tags)
                            elif mtype == "rate":
                                self.rate(metric, float(result[col_idx]), tags=tags)
  			    else:
                                self.gage(metric, float(result[col_idx]), tags=tags)
                        except ValueError:
                            self.log.exception("Cannot find %s in the columns %s" % (field, cursor.description))
                cursor.close()
                del cursor
            except:
                if self.log is not None:
                    self.log.exception("While running %s" % query)

    def getVersion(self):
        # Get MySQL version
        if self.mysqlVersion == None and self.db is not None:
            try:
                cursor = self.db.cursor()
                cursor.execute('SELECT VERSION()')
                result = cursor.fetchone()
                version = result[0].split('-') # Case 31237. Might include a description e.g. 4.1.26-log. See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
                version = version[0].split('.')
                self.mysqlVersion = version
            except MySQLdb.OperationalError, message:
                self.log.exception('MySQL query error when getting version')
        return self.mysqlVersion

    def _get_server_pid(self):
 
        pid = None

        try:
            if sys.platform.startswith("linux"):
                ps = subprocess.Popen(['ps','-C','mysqld','-o','pid'], stdout=subprocess.PIPE, 
                                      close_fds=True).communicate()[0]
                pslines = ps.split('\n')
                # First line is header, second line is mysql pid
                if len(pslines) > 1 and pslines[1] != '':
                    return int(pslines[1])

            elif sys.platform.startswith("darwin") or sys.platform.startswith("freebsd"):
                # Get all processes, filter in python then
                procs = subprocess.Popen(["ps", "-A", "-o", "pid,command"], stdout=subprocess.PIPE, 
                                         close_fds=True).communicate()[0]
                ps = [p for p in procs.split("\n") if p.index("mysqld") > 0]
                if len(ps) > 0:
                    return int(ps.split())[0]
            else:
                self.log.warning("Unsupported platform mysql pluging")
        except:
            if self.log is not None:
                self.log.exception("while fetching mysql pid from ps")
            
        return pid

    def _collect_procfs(self, tags):
        # Try to use the pid file, but there is a good chance
        # we don't have the permission to read it
        pid_file = None
        pid = None

        try:
            if self.db is not None:
                cursor = self.db.cursor()
                cursor.execute("SHOW VARIABLES LIKE 'pid_file'")
                pid_file = cursor.fetchone()[1]
                cursor.close()
                del cursor                      
        except:
            if self.log is not None:
                self.log.exception("While fetching pid of mysql")


        if pid_file is not None:
            self.log.debug("pid file: %s" % str(pid_file))
 
            try:
                f = open(pid_file)
                pid = int(f.readline())
                f.close()
            except:
                if self.log is not None:
                    self.log.warn("Cannot compute advanced MySQL metrics; cannot read mysql pid file %s" % pid_file)

        self.log.debug("pid: %s" % pid)
        # If pid has not been found (permission issue), read it from ps

        if pid is None:
            pid = self._get_server_pid()
            self.log.debug("pid: %s" % pid)

        if pid is not None:
            # At last, get mysql cpu data out of procfs
            try:
                # See http://www.kernel.org/doc/man-pages/online/pages/man5/proc.5.html
                # for meaning: we get 13 & 14: utime and stime, in clock ticks and convert
                # them with the right sysconf value (SC_CLK_TCK)
                f = open("/proc/" + str(pid) + "/stat")
                data = f.readline()
                f.close()
                fields = data.split(' ')
                ucpu = fields[13]
                kcpu = fields[14]
                clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                # Convert time to s (number of second of CPU used by mysql)
                # It's a counter, it will be divided by the period, multiply by 100
                # to get the percentage of CPU used by mysql over the period
                self.rate("mysql.user_time", int((float(ucpu)/float(clk_tck)) * 100), tags=tags)
                self.rate("mysql.kernel_time", int((float(kcpu)/float(clk_tck)) * 100), tags=tags)

            except:
                if self.log is not None:
                    self.log.exception("While reading mysql (pid: %s) procfs data" % pid)

    def check(self, instance):
        import pprint
        import logging
        logging.basicConfig(level=logging.DEBUG)
        pprint.pprint(instance)
        self.log.debug("Mysql check start")
        try:
            host = instance.get('server', '')
            user = instance.get('user', '')
            password = instance.get('pass', '')
            mysql_sock = instance.get('sock', '')
            tags = instance.get('tags', [])
            options = instance.get('options', {})
            self.log.debug("OPTIONS")
            self.log.debug(options)

            if  host != '' and user != '':
                # Connect
                try:
                    import MySQLdb
                    if  mysql_sock != '':
                        self.db = MySQLdb.connect(unix_socket=mysql_sock,
                                                  user=user,
                                                  passwd=password)
                    else:
                        self.db = MySQLdb.connect(host=host,
                                                  user=user,
                                                  passwd=password)
                    self.getVersion()
    
                except ImportError, e:
                    self.log.exception("Cannot import MySQLdb")
                    return False
    
                except MySQLdb.OperationalError:
                    self.log.exception('MySQL connection error')
                    return False
                
                self.log.debug("Connected to MySQL")
    
                # Metric collection
    
                self.log.debug("MySQL version %s" % self.mysqlVersion)
                # show global status was introduced in 5.0.2
                # some patch version numbers contain letters (e.g. 5.0.51a)
                # so let's be careful when we compute the version number
                greater_502 = False
                try:
                    major = int(self.mysqlVersion[0])
                    patchlevel = int(re.match(r"([0-9]+)", self.mysqlVersion[2]).group(1))
                    
                    if major > 5 or  major == 5 and patchlevel >= 2: 
                        greater_502 = True
                    
                except:
                    self.log.exception("Cannot compute mysql version from %s, assuming older than 5.0.2" % self.mysqlVersion)
    
		self.gauge("mysql.connections", self._collect_scalar("show status like 'Connections'"), tags=tags)
                if greater_502:
                    self.gauge("mysql.threads", self._collect_scalar("select 'threads_connected', count(*) from information_schema.processlist"), tags=tags)
                    self.gauge("mysql.created_tmp_disk_tables", self._collect_scalar("SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables'"), tags=tags)
                    self.rate("mysql.slow_queries", self._collect_scalar("SHOW GLOBAL STATUS LIKE 'Slow_queries'"), tags=tags)
                    self.rate("mysql.questions", self._collect_scalar("SHOW GLOBAL STATUS LIKE 'Questions'"), tags=tags)
                    self.rate("mysql.queries", self._collect_scalar("SHOW GLOBAL STATUS LIKE 'Queries'"), tags=tags)
                else:
                    self.gauge("mysql.threads", self._collect_scalar("show global status like 'threads_connected'"), tags=tags)
                    self.gauge("mysql.created_tmp_disk_tables", self._collect_scalar("SHOW STATUS LIKE 'Created_tmp_disk_tables'"), tags=tags)
                    self.rate("mysql.slow_queries", self._collect_scalar("SHOW STATUS LIKE 'Slow_queries'"), tags=tags)
                    self.rate("mysql.questions", self._collect_scalar("SHOW STATUS LIKE 'Questions'"), tags=tags)
                    self.rate("mysql.queries", self._collect_scalar("SHOW STATUS LIKE 'Queries'"), tags=tags)
                
                self.gauge("mysql.max_used_connections", self._collect_scalar("SHOW STATUS LIKE 'Max_used_connections'"), tags=tags)
                self.gauge("mysql.open_files", self._collect_scalar("SHOW STATUS LIKE 'Open_files'"), tags=tags)
                self.gauge("mysql.table_locks_waited", self._collect_scalar("SHOW STATUS LIKE 'Table_locks_waited'"), tags=tags)
                self.gauge("mysql.threads_connected", self._collect_scalar("SHOW STATUS LIKE 'Threads_connected'"), tags=tags)
    
                innodb_buffer_pool_pages_total = self._collect_scalar("SHOW STATUS LIKE 'Innodb_buffer_pool_pages_total'")
                innodb_buffer_pool_pages_free = self._collect_scalar("SHOW STATUS LIKE 'Innodb_buffer_pool_pages_free'")
                innodb_buffer_pool_pages_used = innodb_buffer_pool_pages_total - innodb_buffer_pool_pages_free 
                innodb_buffer_pool_pages_total = (innodb_buffer_pool_pages_total * 16384)/1024;
                innodb_buffer_pool_pages_free = (innodb_buffer_pool_pages_free * 16384)/1024;
                innodb_buffer_pool_pages_used = (innodb_buffer_pool_pages_used * 16384)/1024;
                self.log.debug("bufer_pool_stats: total %s free %s used %s" % (innodb_buffer_pool_pages_total,innodb_buffer_pool_pages_free, innodb_buffer_pool_pages_used))
                self.gauge("mysql.innodb.buffer_pool_free", innodb_buffer_pool_pages_free, tags=tags)
                self.gauge("mysql.innodb.buffer_pool_used", innodb_buffer_pool_pages_used, tags=tags)
                self.gauge("mysql.innodb.buffer_pool_total",innodb_buffer_pool_pages_total, tags=tags)
                

                self.rate("mysql.innodb.buffer_pool_size", self._collect_scalar("SHOW STATUS LIKE 'Innodb_data_reads'"), tags=tags)
                self.rate("mysql.innodb.data_reads", self._collect_scalar("SHOW STATUS LIKE 'Innodb_data_reads'"), tags=tags)
                self.rate("mysql.innodb.data_writes", self._collect_scalar("SHOW STATUS LIKE 'Innodb_data_writes'"), tags=tags)
                self.rate("mysql.innodb.os_log_fsyncs", self._collect_scalar("SHOW STATUS LIKE 'Innodb_os_log_fsyncs'"), tags=tags)
    
                self.log.debug("Collect cpu stats")
                self._collect_procfs(tags=tags)

                if ('galera_cluster' in options.keys() and options['galera_cluster']):
                    self.gauge('mysql.galera.wsrep_cluster_size', self._collect_scalar("SHOW STATUS LIKE 'wsrep_cluster_size'"), tags=tags)
    
                if ('replication' in options.keys() and options['replication']):
                    self._collect_dict("gauge", {"Seconds_behind_master": "mysql.seconds_behind_master"}, "SHOW SLAVE STATUS", tags=tags)
    
                self.log.debug("Done with MySQL")
                return True
            else:
                return False
        except:
            self.log.exception("Cannot check mysql")
            return False

if __name__ == "__main__":
    import pprint
    check, instances = MySql.from_yaml('/etc/dd-agent/conf.d/mysql.yaml')
    for instance in instances:
        print "\nRunning the check against url: %s" % (instance['server'])
        pprint.pprint(check.check(instance))
        if check.has_events():
            print 'Events: %s' % (check.get_events())
        print 'Metrics: %s' % (check.get_metrics())

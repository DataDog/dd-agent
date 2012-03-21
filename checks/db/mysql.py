from checks import Check
import subprocess, os
import sys
import re

class MySql(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)
        self.mysqlVersion = None
        self.db = None
        self.logger = logger

        # Register metrics
        self.counter("mysqlConnections")
        self.gauge("mysqlCreatedTmpDiskTables")
        self.gauge("mysqlMaxUsedConnections")
        self.gauge("mysqlOpenFiles")
        self.counter("mysqlSlowQueries")
        self.counter("mysqlQuestions")
        self.counter("mysqlQueries")
        self.gauge("mysqlTableLocksWaited")
        self.gauge("mysqlThreadsConnected")
        self.gauge("mysqlSecondsBehindMaster")

        self.counter("mysqlInnodbDataReads")
        self.counter("mysqlInnodbDataWrites")
        self.counter("mysqlInnodbOsLogFsyncs")

        self.counter("mysqlUserTime")
        self.counter("mysqlKernelTime")

    def _collect_scalar(self, metric, query):
        if self.db is not None:
            self.logger.debug("Collecting %s with %s" % (metric, query))
            try:
                cursor = self.db.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                self.save_sample(metric, float(result[1]))
                cursor.close()
                del cursor
                self.logger.debug("Collecting %s: done" % metric)
            except:
                if self.logger is not None:
                    self.logger.exception("While running %s" % query)

    def _collect_dict(self, field_metric_map, query):
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
                            self.save_sample(metric, float(result[col_idx]))
                        except ValueError:
                            self.logger.exception("Cannot find %s in the columns %s" % (field, cursor.description))
                cursor.close()
                del cursor
            except:
                if self.logger is not None:
                    self.logger.exception("While running %s" % query)

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
                self.logger.exception('MySQL query error when getting version')
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

            elif sys.platform.startswith("darwin"):
                # Get all processes, filter in python then
                procs = subprocess.Popen(["ps", "-A", "-o", "pid,command"], stdout=subprocess.PIPE, 
                                         close_fds=True).communicate()[0]
                ps = [p for p in procs.split("\n") if p.index("mysqld") > 0]
                if len(ps) > 0:
                    return int(ps.split())[0]
            else:
                self.logger.warning("Unsupported platform mysql pluging")
        except:
            if self.logger is not None:
                self.logger.exception("while fetching mysql pid from ps")
            
        return pid

    def _collect_procfs(self):
    

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
            if self.logger is not None:
                self.logger.exception("While fetching pid of mysql")


        if pid_file is not None:
            self.logger.debug("pid file: %s" % str(pid_file))
 
            try:
                f = open(pid_file)
                pid = int(f.readline())
                f.close()
            except:
                if self.logger is not None:
                    self.logger.warn("Cannot compute advanced MySQL metrics; cannot read mysql pid file %s" % pid_file)

        self.logger.debug("pid: %s" % pid)
        # If pid has not been found (permission issue), read it from ps

        if pid is None:
            pid = self._get_server_pid()
            self.logger.debug("pid: %s" % pid)

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
                self.save_sample("mysqlUserTime", int((float(ucpu)/float(clk_tck)) * 100))
                self.save_sample("mysqlKernelTime", int((float(kcpu)/float(clk_tck)) * 100))

            except:
                if self.logger is not None:
                    self.logger.exception("While reading mysql (pid: %s) procfs data" % pid)

    def check(self, agentConfig):
        try:
            self.logger.debug("Mysql check start")
            if  'MySQLServer' in agentConfig \
                and 'MySQLUser'   in agentConfig\
                and agentConfig['MySQLServer'] != ''\
                and agentConfig['MySQLUser'] != '':
    
                # Connect
                try:
                    import MySQLdb
                    self.db = MySQLdb.connect(agentConfig['MySQLServer'], agentConfig['MySQLUser'], agentConfig['MySQLPass'])
                    self.getVersion()
    
                except ImportError, e:
                    self.logger.exception("Cannot import MySQLdb")
                    return False
    
                except MySQLdb.OperationalError:
                    self.logger.exception('MySQL connection error')
                    return False
                
                self.logger.debug("Connected to MySQL")
    
                # Metric collection
                self._collect_scalar("mysqlConnections", "SHOW STATUS LIKE 'Connections'")
    
                self.logger.debug("MySQL version %s" % self.mysqlVersion)
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
                    self.logger.exception("Cannot compute mysql version from %s, assuming older than 5.0.2" % self.mysqlVersion)
    
                if greater_502:
                    self._collect_scalar("mysqlCreatedTmpDiskTables", "SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables'")
                    self._collect_scalar("mysqlSlowQueries",          "SHOW GLOBAL STATUS LIKE 'Slow_queries'")
                    self._collect_scalar("mysqlQuestions",            "SHOW GLOBAL STATUS LIKE 'Questions'")
                    self._collect_scalar("mysqlQueries",              "SHOW GLOBAL STATUS LIKE 'Queries'")
                else:
                    self._collect_scalar("mysqlCreatedTmpDiskTables", "SHOW STATUS LIKE 'Created_tmp_disk_tables'")
                    self._collect_scalar("mysqlSlowQueries",          "SHOW STATUS LIKE 'Slow_queries'")
                    self._collect_scalar("mysqlQuestions",            "SHOW STATUS LIKE 'Questions'")
                    self._collect_scalar("mysqlQueries",              "SHOW STATUS LIKE 'Queries'")
                
                self._collect_scalar("mysqlMaxUsedConnections", "SHOW STATUS LIKE 'Max_used_connections'")
                self._collect_scalar("mysqlOpenFiles",          "SHOW STATUS LIKE 'Open_files'")
                self._collect_scalar("mysqlTableLocksWaited",   "SHOW STATUS LIKE 'Table_locks_waited'")
                self._collect_scalar("mysqlThreadsConnected",   "SHOW STATUS LIKE 'Threads_connected'")
    
                self._collect_scalar("mysqlInnodbDataReads",   "SHOW STATUS LIKE 'Innodb_data_reads'")
                self._collect_scalar("mysqlInnodbDataWrites",  "SHOW STATUS LIKE 'Innodb_data_writes'")
                self._collect_scalar("mysqlInnodbOsLogFsyncs", "SHOW STATUS LIKE 'Innodb_os_log_fsyncs'")
    
                self.logger.debug("Collect cpu stats")
                self._collect_procfs()
    
                self._collect_dict({"Seconds_behind_master": "mysqlSecondsBehindMaster"}, "SHOW SLAVE STATUS")
    
                self.logger.debug("Done with MySQL")
                return self.get_samples()
            else:
                return False
        except:
            self.logger.exception("Cannot check mysql")
            return False

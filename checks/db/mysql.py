from checks import Check
import subprocess, os

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
            try:
                cursor = self.db.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                self.save_sample(metric, float(result[1]))
                cursor.close()
                del cursor
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
                        metric = field_metric_map[field]
                        self.save_sample(metric, float(result[field]))
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
            ps = subprocess.Popen(['ps','-C','mysqld','-o','pid'], stdout=subprocess.PIPE, 
                close_fds=True).communicate()[0]

            pslines = ps.split('\n')
            #First line is header, second line is mysql pid
            if len(pslines) > 1 and pslines[1] != '':
                return int(pslines[1])

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
                pid = int(read_line(f))
                f.close()
            except:
                if self.logger is not None:
                    self.logger.exception("While reading pid file %s" % pid_file)

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
        "Actual logic here"
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
            

            # Metric collection
            self._collect_scalar("mysqlConnections", "SHOW STATUS LIKE 'Connections'")

            if int(self.mysqlVersion[0]) >= 5 and int(self.mysqlVersion[2]) >= 2:
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

            self._collect_procfs()

            self._collect_dict({"Seconds_behind_master": "mysqlSecondsBehindMaster"}, "SHOW SLAVE STATUS")

            return self.get_samples()
        else:
            return False

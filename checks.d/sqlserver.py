# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

'''
Check the performance counters from SQL Server

See http://blogs.msdn.com/b/psssql/archive/2013/09/23/interpreting-the-counter-values-from-sys-dm-os-performance-counters.aspx
for information on how to report the metrics available in the sys.dm_os_performance_counters table
'''
# stdlib
import traceback

# 3rd party
import adodbapi

# project
from checks import AgentCheck

ALL_INSTANCES = 'ALL'
VALID_METRIC_TYPES = ('gauge', 'rate', 'histogram')

# Constant for SQLServer cntr_type
PERF_LARGE_RAW_BASE = 1073939712
PERF_RAW_LARGE_FRACTION = 537003264
PERF_AVERAGE_BULK = 1073874176
PERF_COUNTER_BULK_COUNT = 272696576
PERF_COUNTER_LARGE_RAWCOUNT = 65792

# Queries
COUNTER_TYPE_QUERY = '''select distinct cntr_type
                        from sys.dm_os_performance_counters
                        where counter_name = ?;'''

BASE_NAME_QUERY = '''select distinct counter_name
                     from sys.dm_os_performance_counters
                     where (counter_name=? or counter_name=?
                     or counter_name=?) and cntr_type=%s;''' % PERF_LARGE_RAW_BASE

INSTANCES_QUERY = '''select instance_name
                     from sys.dm_os_performance_counters
                     where counter_name=? and instance_name!='_Total';'''

VALUE_AND_BASE_QUERY = '''select cntr_value
                          from sys.dm_os_performance_counters
                          where (counter_name=? or counter_name=?)
                          and instance_name=?
                          order by cntr_type;'''

DATABASE_EXISTS_QUERY = 'select name from sys.databases;'

class SQLConnectionError(Exception):
    """
    Exception raised for SQL instance connection issues
    """
    pass


class SQLServer(AgentCheck):

    SOURCE_TYPE_NAME = 'sql server'
    SERVICE_CHECK_NAME = 'sqlserver.can_connect'
    # FIXME: 6.x, set default to 5s (like every check)
    DEFAULT_COMMAND_TIMEOUT = 30
    DEFAULT_DATABASE = 'master'
    DEFAULT_DB_KEY = 'database'
    PROC_GUARD_DB_KEY = 'proc_only_if_database'

    METRICS = [
        ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio', ''),  # RAW_LARGE_FRACTION
        ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.batch_requests', 'Batch Requests/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.connections', 'User Connections', ''),  # LARGE_RAWCOUNT
        ('sqlserver.stats.lock_waits', 'Lock Waits/sec', '_Total'),  # BULK_COUNT
        ('sqlserver.access.page_splits', 'Page Splits/sec', ''),  # BULK_COUNT
        ('sqlserver.stats.procs_blocked', 'Processes blocked', ''),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec', '')  # BULK_COUNT
    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Cache connections
        self.connections = {}
        self.failed_connections = {}
        self.instances_metrics = {}
        self.do_check = {}
        self.proc_type_mapping = {
            'gauge': self.gauge,
            'rate' : self.rate,
            'histogram': self.histogram
        }
        self.existing_databases = None

        # Pre-process the list of metrics to collect
        custom_metrics = init_config.get('custom_metrics', [])
        
        for instance in instances:
            try:
                # check to see if the database exists before we try any connections to it
                self.open_db_connections(instance, db_name=self.DEFAULT_DATABASE)
                db_exists, context = self._check_db_exists(instance)
                instance_key = self._conn_key(instance, db_key=self.DEFAULT_DB_KEY)
                
                if db_exists:
                    self.do_check[instance_key] = True
                    if instance.get('stored_procedure') is None:
                        self.open_db_connections(instance, db_key=self.DEFAULT_DB_KEY)
                        self._make_metric_list_to_collect(instance, custom_metrics)
                        self.close_db_connections(instance, db_key=self.DEFAULT_DB_KEY)
                else:
                    # How much do we care that the DB doesn't exist?
                    ignore = instance.get('ignore_missing_database')
                    if ignore is not None and ignore:
                        # not much : we expect it. Disable checks
                        self.do_check[instance_key] = False
                        self.log.info("Database %s does not exist. Disabling checks for this instance." % (context))
                    else:
                        # yes we do. Keep trying
                        self.do_check[instance_key] = True
                        self.log.exception("Database %s does not exist. Fix issue and restart agent" % (context))

                self.close_db_connections(instance, db_name=self.DEFAULT_DATABASE)

            except SQLConnectionError, e:
                self.log.exception("Skipping SQL Server instance")
                continue

    def _check_db_exists(self, instance):
        """
        Check if the database we're targeting actually exists
        If not then we won't do any checks
        This allows the same config to be installed on many servers but fail gracefully
        """
        
        host, username, password, database = self._get_access_info(instance, db_key=self.DEFAULT_DB_KEY)
        context = "%s - %s" % (host, database)
        if self.existing_databases is None:
            cursor = self.get_cursor(instance, db_name='master')
        
            try:
                self.existing_databases = {}
                cursor.execute(DATABASE_EXISTS_QUERY)
                for row in cursor:
                    self.existing_databases[row.name] = True

                self.close_cursor(cursor)
            except Exception, e:
                self.log.error("Failed to check if database %s exists: %s" % (database, e))
                return False, context
        
        return database in self.existing_databases, context

    def _make_metric_list_to_collect(self, instance, custom_metrics):
        """
        Store the list of metrics to collect by instance_key.
        Will also create and cache cursors to query the db.
        """
        metrics_to_collect = []
        for name, counter_name, instance_name in self.METRICS:
            try:
                sql_type, base_name = self.get_sql_type(instance, counter_name)
                metrics_to_collect.append(self.typed_metric(name,
                                                            counter_name,
                                                            base_name,
                                                            None,
                                                            sql_type,
                                                            instance_name,
                                                            None))
            except SQLConnectionError:
                raise
            except Exception:
                self.log.warning("Can't load the metric %s, ignoring", name, exc_info=True)
                continue

        # Load any custom metrics from conf.d/sqlserver.yaml
        for row in custom_metrics:
            user_type = row.get('type')
            if user_type is not None and user_type not in VALID_METRIC_TYPES:
                self.log.error('%s has an invalid metric type: %s', row['name'], user_type)
            sql_type = None
            try:
                if user_type is None:
                    sql_type, base_name = self.get_sql_type(instance, row['counter_name'])
            except Exception:
                self.log.warning("Can't load the metric %s, ignoring", row['name'], exc_info=True)
                continue

            metrics_to_collect.append(self.typed_metric(row['name'],
                                                        row['counter_name'],
                                                        base_name,
                                                        user_type,
                                                        sql_type,
                                                        row.get('instance_name', ''),
                                                        row.get('tag_by', None)))

        instance_key = self._conn_key(instance, db_key=self.DEFAULT_DB_KEY)
        self.instances_metrics[instance_key] = metrics_to_collect

    def typed_metric(self, dd_name, sql_name, base_name, user_type, sql_type, instance_name, tag_by):
        '''
        Create the appropriate SqlServerMetric object, each implementing its method to
        fetch the metrics properly.
        If a `type` was specified in the config, it is used to report the value
        directly fetched from SQLServer. Otherwise, it is decided based on the
        sql_type, according to microsoft's documentation.
        '''

        metric_type_mapping = {
            PERF_COUNTER_BULK_COUNT: (self.rate, SqlSimpleMetric),
            PERF_COUNTER_LARGE_RAWCOUNT: (self.gauge, SqlSimpleMetric),
            PERF_LARGE_RAW_BASE: (self.gauge, SqlSimpleMetric),
            PERF_RAW_LARGE_FRACTION: (self.gauge, SqlFractionMetric),
            PERF_AVERAGE_BULK: (self.gauge, SqlIncrFractionMetric)
        }
        if user_type is not None:
            # user type overrides any other value
            metric_type = getattr(self, user_type)
            cls = SqlSimpleMetric

        else:
            metric_type, cls = metric_type_mapping[sql_type]

        return cls(dd_name, sql_name, base_name,
                   metric_type, instance_name, tag_by, self.log)

    def _get_access_info(self, instance, db_key=None, db_name=None):
        ''' Convenience method to extract info from instance
        '''
        host = instance.get('host', '127.0.0.1,1433')
        username = instance.get('username')
        password = instance.get('password')
        database = instance.get(db_key) if db_name is None else db_name

        if database is None:
            database = (self.DEFAULT_DATABASE if (db_key == self.DEFAULT_DB_KEY) else
                        instance.get(self.DEFAULT_DB_KEY, self.DEFAULT_DATABASE))

        return host, username, password, database

    def _conn_key(self, instance, db_key=None, db_name=None):
        ''' Return a key to use for the connection cache
        '''
        host, username, password, database = self._get_access_info(instance, db_key)
        database = database if db_name is None else db_name
        return '%s:%s:%s:%s' % (host, username, password, database)

    def _conn_string(self, instance, db_key, db_name):
        ''' Return a connection string to use with adodbapi
        '''
        host, username, password, database = self._get_access_info(instance, db_key, db_name=db_name)
        conn_str = 'Provider=SQLOLEDB;Data Source=%s;Initial Catalog=%s;' \
            % (host, database)
        if username:
            conn_str += 'User ID=%s;' % (username)
        if password:
            conn_str += 'Password=%s;' % (password)
        if not username and not password:
            conn_str += 'Integrated Security=SSPI;'
        return conn_str

    def get_cursor(self, instance, db_key=None, db_name=None):
        '''
        Return a cursor to execute query against the db
        Cursor are cached in the self.connections dict
        '''
        conn_key = self._conn_key(instance, db_key=db_key, db_name=db_name)

        conn = self.connections[conn_key]['conn']
        cursor = conn.cursor()
        return cursor

    def get_sql_type(self, instance, counter_name):
        '''
        Return the type of the performance counter so that we can report it to
        Datadog correctly
        If the sql_type is one that needs a base (PERF_RAW_LARGE_FRACTION and
        PERF_AVERAGE_BULK), the name of the base counter will also be returned
        '''
        cursor = self.get_cursor(instance, self.DEFAULT_DATABASE)
        cursor.execute(COUNTER_TYPE_QUERY, (counter_name,))
        (sql_type,) = cursor.fetchone()
        if sql_type == PERF_LARGE_RAW_BASE:
            self.log.warning("Metric %s is of type Base and shouldn't be reported this way",
                             counter_name)
        base_name = None
        if sql_type in [PERF_AVERAGE_BULK, PERF_RAW_LARGE_FRACTION]:
            # This is an ugly hack. For certains type of metric (PERF_RAW_LARGE_FRACTION
            # and PERF_AVERAGE_BULK), we need two metrics: the metrics specified and
            # a base metrics to get the ratio. There is no unique schema so we generate
            # the possible candidates and we look at which ones exist in the db.
            candidates = (counter_name + " base",
                          counter_name.replace("(ms)", "base"),
                          counter_name.replace("Avg ", "") + " base"
                          )
            try:
                cursor.execute(BASE_NAME_QUERY, candidates)
                base_name = cursor.fetchone().counter_name.strip()
                self.log.debug("Got base metric: %s for metric: %s", base_name, counter_name)
            except Exception as e:
                self.log.warning("Could not get counter_name of base for metric: %s", e)

        self.close_cursor(cursor)

        return sql_type, base_name

    def check(self, instance):
        if self.do_check[self._conn_key(instance, db_key=self.DEFAULT_DB_KEY)]:
            proc = instance.get('stored_procedure')
            if proc is None:
                self.do_perf_counter_check(instance)
            else:
                self.do_stored_procedure_check(instance, proc)
        else:
            self.log.debug("Skipping check")
            
    def do_perf_counter_check(self, instance):
        """
        Fetch the metrics from the sys.dm_os_performance_counters table
        """
        self.open_db_connections(instance, db_key=self.DEFAULT_DB_KEY)
        cursor = self.get_cursor(instance, db_key=self.DEFAULT_DB_KEY)

        custom_tags = instance.get('tags', [])
        instance_key = self._conn_key(instance, db_key=self.DEFAULT_DB_KEY)
        metrics_to_collect = self.instances_metrics[instance_key]

        for metric in metrics_to_collect:
            try:
                metric.fetch_metric(cursor, custom_tags)
            except Exception as e:
                self.log.warning("Could not fetch metric %s: %s" % (metric.datadog_name, e))

        self.close_cursor(cursor)
        self.close_db_connections(instance, db_key=self.DEFAULT_DB_KEY)

    def do_stored_procedure_check(self, instance, proc):
        """
        Fetch the metrics from the stored proc
        """

        guardSql = instance.get('proc_only_if')

        if (guardSql and self.proc_check_guard(instance, guardSql)) or not guardSql:
            self.open_db_connections(instance, db_key=self.DEFAULT_DB_KEY)
            cursor = self.get_cursor(instance, db_key=self.DEFAULT_DB_KEY)

            try:
                cursor.callproc(proc)
                rows = cursor.fetchall()
                for row in rows:
                    tags = [] if row.tags is None or row.tags == '' else row.tags.split(',')

                    if row.type in self.proc_type_mapping:
                        self.proc_type_mapping[row.type](row.metric, row.value, tags)
                    else:
                        self.log.warning('%s is not a recognised type from procedure %s, metric %s'
                                         % (row.type, proc, row.metric))
                        
            except Exception, e:
                self.log.warning("Could not call procedure %s: %s" % (proc, e))
                
            self.close_cursor(cursor)
            self.close_db_connections(instance, db_key=self.DEFAULT_DB_KEY)
        else:
            self.log.info("Skipping call to %s due to only_if" % (proc))

    def proc_check_guard(self, instance, sql):
        """
        check to see if the guard SQL returns a single column contains 0 or 1
        We return true if 1, False if 0
        """
        self.open_db_connections(instance, self.PROC_GUARD_DB_KEY)
        cursor = self.get_cursor(instance, db_key=self.PROC_GUARD_DB_KEY)

        try:
            cursor.execute(sql, ())
            result = cursor.fetchone()
            return result[0] == 1
        except Exception, e:
            self.log.error("Failed to run proc_only_if sql %s : %s" % (sql, e))
            return False
        
        self.close_cursor(cursor)
        self.close_db_connections(instance, db_key=self.PROC_GUARD_DB_KEY)
    
    def close_cursor(self, cursor):
        """
        We close the cursor explicitly b/c we had proven memory leaks
        We handle any exception from closing, although according to the doc:
        "in adodbapi, it is NOT an error to re-close a closed cursor"
        """
        try:
            cursor.close()
        except Exception as e:
            self.log.warning("Could not close adodbapi cursor\n{0}".format(e))

    def close_db_connections(self, instance, db_key=None, db_name=None):
        """
        We close the db connections explicitly b/c when we don't they keep
        locks on the db. This presents as issues such as the SQL Server Agent
        being unable to stop.
        """
        conn_key = self._conn_key(instance, db_key, db_name)
        if conn_key not in self.connections:
            return

        try:
            self.connections[conn_key]['conn'].close()
            del self.connections[conn_key]
        except Exception as e:
            self.log.warning("Could not close adodbapi db connection\n{0}".format(e))

    def open_db_connections(self, instance, db_key=None, db_name=None):
        """
        We open the db connections explicitly, so we can ensure they are open
        before we use them, and are closable, once we are finished. Open db
        connections keep locks on the db, presenting issues such as the SQL
        Server Agent being unable to stop.
        """

        conn_key = self._conn_key(instance, db_key, db_name)
        timeout = int(instance.get('command_timeout',
                                   self.DEFAULT_COMMAND_TIMEOUT))

        host, username, password, database = self._get_access_info(instance, db_key, db_name)
        service_check_tags = [
            'host:%s' % host,
            'db:%s' % database
        ]

        try:
            rawconn = adodbapi.connect(self._conn_string(instance, db_key, db_name),
                                       {'timeout':timeout, 'autocommit':True})
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                               tags=service_check_tags)
            if conn_key not in self.connections:
                self.connections[conn_key] = {'conn': rawconn,
                                              'timeout': timeout,
                                              'autocommit': True}
            else:
                try:
                    # explicitly trying to avoid leaks...
                    self.connections[conn_key]['conn'].close()
                except Exception as e:
                    self.log.info("Could not close adodbapi db connection\n{0}".format(e))

                self.connections[conn_key]['conn'] = rawconn
        except Exception as e:
            cx = "%s - %s" % (host, database)
            message = "Unable to connect to SQL Server for instance %s." % cx
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                               tags=service_check_tags, message=message)

            password = instance.get('password')
            tracebk = traceback.format_exc()
            if password is not None:
                tracebk = tracebk.replace(password, "*" * 6)

            cxn_failure_exp = SQLConnectionError("%s \n %s" % (message, tracebk))
            raise cxn_failure_exp

class SqlServerMetric(object):
    '''General class for common methods, should never be instantiated directly
    '''

    def __init__(self, datadog_name, sql_name, base_name,
                 report_function, instance, tag_by, logger):
        self.datadog_name = datadog_name
        self.sql_name = sql_name
        self.base_name = base_name
        self.report_function = report_function
        self.instance = instance
        self.tag_by = tag_by
        self.instances = None
        self.past_values = {}
        self.log = logger

    def fetch_metrics(self, cursor, tags):
        raise NotImplementedError


class SqlSimpleMetric(SqlServerMetric):

    def fetch_metric(self, cursor, tags):
        query_base = '''
                    select instance_name, cntr_value
                    from sys.dm_os_performance_counters
                    where counter_name = ?
                    '''
        if self.instance == ALL_INSTANCES:
            query = query_base + "and instance_name!= '_Total'"
            query_content = (self.sql_name,)
        else:
            query = query_base + "and instance_name=?"
            query_content = (self.sql_name, self.instance)

        cursor.execute(query, query_content)
        rows = cursor.fetchall()
        for instance_name, cntr_value in rows:
            metric_tags = tags
            if self.instance == ALL_INSTANCES:
                metric_tags = metric_tags + ['%s:%s' % (self.tag_by, instance_name.strip())]
            self.report_function(self.datadog_name, cntr_value,
                                 tags=metric_tags)


class SqlFractionMetric(SqlServerMetric):

    def set_instances(self, cursor):
        if self.instance == ALL_INSTANCES:
            cursor.execute(INSTANCES_QUERY, (self.sql_name,))
            self.instances = [row.instance_name for row in cursor.fetchall()]
        else:
            self.instances = [self.instance]

    def fetch_metric(self, cursor, tags):
        '''
        Because we need to query the metrics by matching pairs, we can't query
        all of them together without having to perform some matching based on
        the name afterwards so instead we query instance by instance.
        We cache the list of instance so that we don't have to look it up every time
        '''
        if self.instances is None:
            self.set_instances(cursor)
        for instance in self.instances:
            cursor.execute(VALUE_AND_BASE_QUERY, (self.sql_name, self.base_name, instance))
            rows = cursor.fetchall()
            if len(rows) != 2:
                self.log.warning("Missing counter to compute fraction for "
                                 "metric %s instance %s, skipping", self.sql_name, instance)
                continue
            value = rows[0, "cntr_value"]
            base = rows[1, "cntr_value"]

            metric_tags = tags
            if self.instance == ALL_INSTANCES:
                metric_tags = metric_tags + ['%s:%s' % (self.tag_by, instance.strip())]
            self.report_fraction(value, base, metric_tags)

    def report_fraction(self, value, base, metric_tags):
        try:
            result = value / float(base)
            self.report_function(self.datadog_name, result, tags=metric_tags)
        except ZeroDivisionError:
            self.log.debug("Base value is 0, won't report metric %s for tags %s",
                           self.datadog_name, metric_tags)


class SqlIncrFractionMetric(SqlFractionMetric):

    def report_fraction(self, value, base, metric_tags):
        key = "key:" + "".join(metric_tags)
        if key in self.past_values:
            old_value, old_base = self.past_values[key]
            diff_value = value - old_value
            diff_base = base - old_base
            try:
                result = diff_value / float(diff_base)
                self.report_function(self.datadog_name, result, tags=metric_tags)
            except ZeroDivisionError:
                self.log.debug("Base value is 0, won't report metric %s for tags %s",
                               self.datadog_name, metric_tags)
        self.past_values[key] = (value, base)

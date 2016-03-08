'''
Call a SQL stored procedure that returns metric values

The proc must return a dataset with columns:
 - metric : the name of the metric
 - type   : gauge / rate / histogram
 - value  : the value to be logged
 - tags   : comma seprated list of tags

It is based on the SQL Server check

This could be made cross platform if we had access to a different DB library
'''
# stdlib
import traceback

# project
from checks import AgentCheck

# 3rd party
import adodbapi

class SQLConnectionError(Exception):
    """
    Exception raised for SQL instance connection issues
    """
    pass


class SqlProc(AgentCheck):

    SERVICE_CHECK_NAME = 'sqlproc.can_connect'
    DEFAULT_COMMAND_TIMEOUT = 30


    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Cache connections
        self.connections = {}
        self.failed_connections = {}
        self.type_mapping = {
            'gauge': self.gauge,
            'rate' : self.rate,
            'histogram': self.histogram
        }
        
    def _get_access_info(self, instance, db_key):
        ''' Convenience method to extract info from instance
        '''
        host = instance.get('host', '127.0.0.1,1433')
        username = instance.get('username')
        password = instance.get('password')
        database = instance.get(db_key)
        provider = instance.get('provider')

        if database == None and db_key != 'database':
            database = instance.get('database')
            
        return provider, host, username, password, database

    def _conn_key(self, instance, db_key):
        ''' Return a key to use for the connection cache
        '''
        provider, host, username, password, database = self._get_access_info(instance, db_key)
        return '%s:%s:%s:%s:%s' % (provider, host, username, password, database)

    def _conn_string(self, instance, db_key):
        ''' Return a connection string to use with adodbapi
        '''
        provider, host, username, password, database = self._get_access_info(instance, db_key)
        conn_str = 'Provider=%s;Data Source=%s;Initial Catalog=%s;' \
            % (provider, host, database)
        if username:
            conn_str += 'User ID=%s;' % (username)
        if password:
            conn_str += 'Password=%s;' % (password)
        if not username and not password:
            conn_str += 'Integrated Security=SSPI;'
        return conn_str

    def get_cursor(self, instance, cache_failure=False, db_key='database'):
        '''
        Return a cursor to execute query against the db
        Cursor are cached in the self.connections dict
        '''
        conn_key = self._conn_key(instance, db_key)

        provider, host, username, password, database = self._get_access_info(instance, db_key)
        service_check_tags = [
            'host:%s' % host,
            'db:%s' % database
        ]

        if conn_key in self.failed_connections:
            raise self.failed_connections[conn_key]

        if conn_key not in self.connections:
            try:
                conn = adodbapi.connect(
                    self._conn_string(instance, db_key),
                    timeout=int(instance.get('command_timeout',
                                             self.DEFAULT_COMMAND_TIMEOUT))
                )
                self.connections[conn_key] = conn
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
            except Exception:
                cx = "%s - %s" % (host, database)
                message = "Unable to connect to SQL Server for instance %s." % cx
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   tags=service_check_tags, message=message)

                password = instance.get('password')
                tracebk = traceback.format_exc()
                if password is not None:
                    tracebk = tracebk.replace(password, "*" * 6)

                # Avoid multiple connection timeouts (too slow):
                # save the exception, re-raise it when needed
                cxn_failure_exp = SQLConnectionError("%s \n %s" % (message, tracebk))
                if cache_failure:
                    self.failed_connections[conn_key] = cxn_failure_exp
                raise cxn_failure_exp

        conn = self.connections[conn_key]
        cursor = conn.cursor()
        return cursor

    def check(self, instance):
        """
        Fetch the metrics from the stored proc
        """

        proc = instance.get('procedure')
        guardSql = instance.get('only_if', '')
        
        if guardSql and self.check_guard(instance, guardSql):
            cursor = self.get_cursor(instance)
        
            try:
                cursor.callproc(proc)
                rows = cursor.fetchall()
                for row in rows:
                    tags = [] if row.tags is None or row.tags == '' else row.tags.split(',')

                    if row.type in self.type_mapping:
                        self.type_mapping[row.type](row.metric, row.value, tags)
                    else:
                        self.log.warning('%s is not a recognised type from procedure %s, metric %s' % (row.type, proc, row.metric))
                        
            except Exception, e:
                self.log.warning("Could not call procedure %s: %s" % (proc, e))
                
            self.close_cursor(cursor)
        else:
            self.log.info("Skipping call to %s due to only_if" % (proc))
            

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

    def check_guard(self, instance, sql):
        """
        check to see if the guard SQL returns a single column contains 0 or 1
        We return true if 1, False if 0
        """
        cursor = self.get_cursor(instance, db_key='only_if_database')

        try:
            cursor.execute(sql, ())
            result = cursor.fetchone()
            return result[0] == 1
        except Exception, e:
            self.log.error("Failed to run only_if sql %s : %s" % (sql, e))
            return False
        
        self.close_cursor(cursor)

from checks import Check

class PostgreSql(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self.pgVersion = None
        self.db = None

    def _get_version(self):
        if self.pgVersion is None and self.db is not None:
            try:
                cursor = self.db.cursor()
                cursor.execute('select version();')
                result = cursor.fetchone()
                self.pgVersion = result[0]
                #FIXME parse or find the way to get the ints
            except Exception, e:
                self.logger.exception('Error when fetching postgresql version')

        return self.pgVersion

    def _init_metric(self,kind,dbname,metric):
        mname = dbname + '.' + metric
        if kind == 'gauge':
            if not self.is_gauge(mname):
                self.logger.debug("Adding gauge metric: %s" % mname)
                self.gauge(mname)
        else:
            if not self.is_counter(mname):
                self.logger.debug("Adding counter metric: %s" % mname)
                self.counter(mname)

    def _init_metrics(self,dbname):
        self._init_metric('gauge',dbname,'connections')
        self._init_metric('counter',dbname,'commits')
        self._init_metric('counter',dbname,'rollbacks')
        self._init_metric('counter',dbname,'disk_read')
        self._init_metric('counter',dbname,'buffer_hit')
        self._init_metric('counter',dbname,'rows_returned')
        self._init_metric('counter',dbname,'rows_fetched')
        self._init_metric('counter',dbname,'rows_inserted')
        self._init_metric('counter',dbname,'rows_updated')
        self._init_metric('counter',dbname,'rows_deleted')


    def _store_metric(self, dbname, metric, val):
        mname = dbname + '.' + metric
        self.save_sample(mname,float(val))

    def _collect_stats(self):
        if self.db is not None:

            query = """
  select datname, numbackends, xact_commit, 
       xact_rollback, blks_read, blks_hit, 
       tup_returned, tup_fetched, tup_inserted, 
       tup_updated, tup_deleted
  from pg_stat_database
  where datname not ilike 'template%' and
        datname not ilike 'postgres';
            """
            try:
                cursor = self.db.cursor()
                cursor.execute(query)
                result = cursor.fetchone()
                while result is not None:
                    (datname, backends, commits, rollbacks, read, hit, 
                     ret, fetch, ins, upd, deleted) = result
                    self._init_metrics(datname)
                    self._store_metric(datname, 'connections', backends)
                    self._store_metric(datname, 'commits', commits)
                    self._store_metric(datname, 'rollbacks', rollbacks)
                    self._store_metric(datname, 'disk_read', read )
                    self._store_metric(datname, 'buffer_hit', hit )
                    self._store_metric(datname, 'rows_returned', ret)
                    self._store_metric(datname, 'rows_fetched', fetch)
                    self._store_metric(datname, 'rows_inserted', ins)
                    self._store_metric(datname, 'rows_updated', upd)
                    self._store_metric(datname, 'rows_deleted', deleted)
                    result = cursor.fetchone()
                del cursor
            except Exception, e:
                self.logger.exception("Error while gathering pg stats: %s" % e)


    def check(self, agentConfig):

        server = agentConfig.get('PostgreSqlServer','')
        user = agentConfig.get('PostgreSqlUser','')
        passwd = agentConfig.get('PostgreSqlPass','')
 
        if server != '' and user != '':

            try:
                import psycopg2 as pg
                self.db = pg.connect(host=server, user=user, password=passwd, 
                    database='postgres')
                self._get_version()
            except ImportError, e:
                self.logger.exception("Cannot import psypg2")
                return False
            except Exception, e: #Fixme: catch only pg errors
                self.logger.exception('PostgreSql connection error')
                return False

            # Check version
            self._get_version()

            # Collect metrics
            self._collect_stats()

            return self.get_samples()

if __name__ == "__main__":

    import logging
    pg = PostgreSql(logging)
    pg.check({'PostgreSqlServer': 'localhost', 'PostgreSqlUser': 'dog', 'PostgreSqlPass': 'dog'})


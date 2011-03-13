from checks import Check

class PostgreSql(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
        self.pgVersion = None
        self.db = None
        self.logger = logger

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

    def _init_metric(self,dbname,metric):
        mname = dbname + '.' + metric
        if not self.is_gauge(mname):
            self.logger.debug("Adding metric: %s" % mname)
            self.gauge(mname)

    def _init_metrics(self,dbname):
        self._init_metric(dbname,'backends')
        self._init_metric(dbname,'commits')
        self._init_metric(dbname,'rollbacks')
        self._init_metric(dbname,'read')
        self._init_metric(dbname,'hit')
        self._init_metric(dbname,'ret')
        self._init_metric(dbname,'fetch')
        self._init_metric(dbname,'ins')
        self._init_metric(dbname,'upd')
        self._init_metric(dbname,'del')


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
                    self._store_metric(datname, 'backends', backends)
                    self._store_metric(datname, 'commits', backends)
                    self._store_metric(datname, 'rollbacks', backends)
                    self._store_metric(datname, 'read', read )
                    self._store_metric(datname, 'hit', hit )
                    self._store_metric(datname, 'ret', ret)
                    self._store_metric(datname, 'fetch', fetch)
                    self._store_metric(datname, 'ins', ins)
                    self._store_metric(datname, 'upd', upd)
                    self._store_metric(datname, 'del', deleted)
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


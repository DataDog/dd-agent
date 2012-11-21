from checks import AgentCheck

class PostgreSql(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}
        self.versions = {}

    def _get_version(self, key, db):
        if key not in self.versions:
            try:
                cursor = db.cursor()
                cursor.execute('select version();')
                result = cursor.fetchone()
                self.versions[key] = result[0]
                # FIXME parse or find the way to get the ints
            except Exception, e:
                self.log.exception('Error when fetching postgresql version')

        return self.versions[key]

    def _collect_stats(self, db, tags):
        query = """
            select datname, numbackends, xact_commit,
               xact_rollback, blks_read, blks_hit,
               tup_returned, tup_fetched, tup_inserted,
               tup_updated, tup_deleted
            from pg_stat_database
            where datname not ilike 'template%' and
                datname not ilike 'postgres';
        """
        cursor = db.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        while result is not None:
            (dbname, backends, commits, rollbacks, read, hit,
             ret, fetch, ins, upd, deleted) = result
            tags = ['db:%s' % dbname] + tags
            self.gauge('postgresql.connections', backends, tags=tags)
            self.rate('postgresql.commits', commits, tags=tags)
            self.rate('postgresql.rollbacks', backends, tags=tags)
            self.rate('postgresql.disk_read', read, tags=tags)
            self.rate('postgresql.buffer_hit', hit, tags=tags)
            self.rate('postgresql.rows_returned', ret, tags=tags)
            self.rate('postgresql.rows_fetched', fetch, tags=tags)
            self.rate('postgresql.rows_inserted', ins, tags=tags)
            self.rate('postgresql.rows_updated', upd, tags=tags)
            self.rate('postgresql.rows_deleted', deleted, tags=tags)
            result = cursor.fetchone()
        del cursor

    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        passwd = instance.get('password', '')
        tags = instance.get('tags', [])
        key = '%s:%s' % (host, port)

        if key in self.dbs:
            db = self.dbs[key]
        elif host != '' and user != '':
            import psycopg2 as pg
            if host == 'localhost' and passwd == '':
                # Use ident method
                db = pg.connect("user=%s dbname=postgres" % user)
            elif port != '':
                db = pg.connect(host=host, port=port, user=user,
                    password=passwd, database='postgres')
            else:
                db = pg.connect(host=host, user=user, password=passwd,
                    database='postgres')

        # Check version
        version = self._get_version(key, db)
        self.log.debug("Running check against version %s" % version)

        # Collect metrics
        self._collect_stats(db, tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        server = agentConfig.get('postgresql_server','')
        port = agentConfig.get('postgresql_port','')
        user = agentConfig.get('postgresql_user','')
        passwd = agentConfig.get('postgresql_pass','')

        if server != '' and user != '':
            return {
                'instances': [{
                    'host': server,
                    'port': port,
                    'username': user,
                    'password': passwd
                }]
            }

        return False

if __name__ == "__main__":
    pg = PostgreSql(logging)
    pg.check({'host': 'localhost', 'username': 'dog', 'password': 'dog'})


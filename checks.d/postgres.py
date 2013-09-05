from checks import AgentCheck

class PostgreSql(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}
        self.versions = {}

    def _get_version(self, key, db):
        if key not in self.versions:
            cursor = db.cursor()
            cursor.execute('select version();')
            result = cursor.fetchone()
            self.versions[key] = result[0]
            # FIXME parse or find the way to get the ints

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
            try:
                tags = ['db:%s' % dbname] + tags
            except Exception:
                # if tags is none or is not of the right type
                tags = ['db:%s' % dbname]
            self.gauge('postgresql.connections', backends, tags=tags)
            self.rate('postgresql.commits', commits, tags=tags)
            self.rate('postgresql.rollbacks', rollbacks, tags=tags)
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
        dbname = instance.get('database', '')
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        key = '%s:%s' % (host, port)

        if dbname == '':
            dbname = 'postgres'

        if key in self.dbs:
            db = self.dbs[key]
        elif host != '' and user != '':
            import psycopg2 as pg
            if host == 'localhost' and passwd == '':
                # Use ident method
                db = pg.connect("user=%s dbname=%s" % (user, dbname))
            elif port != '':
                db = pg.connect(host=host, port=port, user=user,
                    password=passwd, database=dbname)
            else:
                db = pg.connect(host=host, user=user, password=passwd,
                    database=dbname)

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

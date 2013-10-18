from checks import AgentCheck

GAUGE = 'gauge'
RATE = 'rate'

METRICS = {
    'numbackends'       : ('connections', GAUGE),
    'xact_commit'       : ('commits', RATE),
    'xact_rollback'     : ('rollbacks', RATE),
    'blks_read'         : ('disk_read', RATE),
    'blks_hit'          : ('buffer_hit', RATE),
    'tup_returned'      : ('rows_returned', RATE),
    'tup_fetched'       : ('rows_fetched', RATE),
    'tup_inserted'      : ('rows_inserted', RATE),
    'tup_updated'       : ('rows_updated', RATE),
    'tup_deleted'       : ('rows_deleted', RATE),

}

NEWER_92_METRICS = {
    'blk_read_time'     : ('disk_read_time', GAUGE),
    'blk_write_time'    : ('disk_write_time', GAUGE),
    'deadlocks'         : ('deadlocks', GAUGE),
    'temp_bytes'        : ('temp_bytes', RATE),
    'temp_files'        : ('temp_files', RATE),
}

class PostgreSql(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}
        self.versions = {}

    def get_check_library_info(self):
        try:
            import psycopg2
        except ImportError:
            return "psycopg2 not found"

        try:
            version = psycopg2.__version__
        except AttributeError:
            version = "unknown"

        return "psycopg2: %s" % version

    def _get_version(self, key, db):
        if key not in self.versions:
            cursor = db.cursor()
            cursor.execute('SHOW SERVER_VERSION;')
            result = cursor.fetchone()
            try:
                version = map(int, result[0].split('.'))
            except Exception:
                version = result[0]
            self.versions[key] = version

        return self.versions[key]

    def _is_9_2_or_above(self, key, db):
        version = self._get_version(key, db)
        if type(version) == list:
            return version >= [9,2,0]

        return False


    def _collect_stats(self, key, db, instance_tags):

        metrics_to_collect = METRICS
        if self._is_9_2_or_above(key, db):
            metrics_to_collect.update(NEWER_92_METRICS)


        metrics_keys = metrics_to_collect.keys()
        fields = ",".join(metrics_keys)
        query = """SELECT datname,
                    %s 
                    FROM pg_stat_database
                    WHERE datname not ilike 'template%%'
                    AND datname not ilike 'postgres'
                ;""" % fields
        
        cursor = db.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        while result is not None:
            dbname = result[0]
            try:
                tags = ['db:%s' % dbname] + instance_tags
            except Exception:
                # if tags is none or is not of the right type
                tags = ['db:%s' % dbname]

            for i, value in enumerate(result):
                if i == 0:
                    # This is the dbname
                    continue

                metric_name = "postgresql.%s" % metrics_to_collect[metrics_keys[i-1]][0]
                metric_type = metrics_to_collect[metrics_keys[i-1]][1]
                if metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=tags)
                elif metric_type == RATE:
                    self.rate(metric_name, value, tags=tags)

            result = cursor.fetchone()
        del cursor

    def get_connection(self, key, host, port, user, password, dbname):

        if key in self.dbs:
            return self.dbs[key]

        elif host != '' and user != '':
            try:
                import psycopg2 as pg
            except ImportError:
                raise ImportError("psycopg2 library can not be imported. Please check the installation instruction on the Datadog Website")
            
            if host == 'localhost' and password == '':
                # Use ident method
                return pg.connect("user=%s dbname=%s" % (user, dbname))
            elif port != '':
                return pg.connect(host=host, port=port, user=user,
                    password=password, database=dbname)
            else:
                return pg.connect(host=host, user=user, password=password,
                    database=dbname)


    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        password = instance.get('password', '')
        tags = instance.get('tags', [])
        dbname = instance.get('database', 'postgres')
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        key = '%s:%s' % (host, port)

        db = self.get_connection(key, host, port, user, password, dbname)

        # Check version
        version = self._get_version(key, db)
        self.log.debug("Running check against version %s" % version)

        # Collect metrics
        self._collect_stats(key, db, tags)

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

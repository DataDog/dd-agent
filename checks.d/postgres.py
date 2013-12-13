from checks import AgentCheck

GAUGE = 'gauge'
RATE = 'rate'

# Comment here

# turning columns into tags
DB_METRICS = {
    'descriptors': [
        ('datname', 'db')
    ],
    'metrics': {
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
    },
    'query': """
SELECT datname,
       %s
  FROM pg_stat_database
 WHERE datname not ilike 'template%%'
   AND datname not ilike 'postgres'
""",
    'relation': False,
}

NEWER_92_DB_METRICS = {
    'blk_read_time'     : ('disk_read_time', GAUGE),
    'blk_write_time'    : ('disk_write_time', GAUGE),
    'deadlocks'         : ('deadlocks', GAUGE),
    'temp_bytes'        : ('temp_bytes', RATE),
    'temp_files'        : ('temp_files', RATE),
}

REL_METRICS = {
    'descriptors': [
        ('relname', 'table')
    ],
    'metrics': {
        'seq_scan'          : ('seq_scans', RATE),
        'seq_tup_read'      : ('seq_rows_read', RATE),
        'idx_scan'          : ('index_scans', RATE),
        'idx_tup_fetch'     : ('index_rows_fetched', RATE),
        'n_tup_ins'         : ('rows_inserted', RATE),
        'n_tup_upd'         : ('rows_updated', RATE),
        'n_tup_del'         : ('rows_deleted', RATE),
        'n_tup_hot_upd'     : ('rows_hot_updated', RATE),
        'n_live_tup'        : ('live_rows', GAUGE),
        'n_dead_tup'        : ('dead_rows', GAUGE),
    },
    'query': """
SELECT relname,
       %s
  FROM pg_stat_user_tables
 WHERE relname = %s""",
    'relation': True,
}

IDX_METRICS = {
    'descriptors': [
        ('relname', 'table'),
        ('indexrelname', 'index')
    ],
    'metrics': {
        'idx_scan'          : ('index_scans', RATE),
        'idx_tup_read'      : ('index_rows_read', RATE),
        'idx_tup_fetch'     : ('index_rows_fetched', RATE),
    },
    'query': """
SELECT relname,
       indexrelname,
       %s
  FROM pg_stat_user_indexes
 WHERE relname = %s""",
    'relation': True,
}


class PostgreSql(AgentCheck):
    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}
        self.versions = {}

    def get_library_versions(self):
        try:
            import psycopg2
            version = psycopg2.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"psycopg2": version}

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

    def _collect_stats(self, key, db, instance_tags, relations):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        """
        def get_dd_metric_name(pg_name, mapping):
            "Turn a pg metric name into a dd metric name"
            return "postgresql.%s" % mapping.get('metrics', {}).get(pg_name, pg_name)
 
        # Extended 9.2+ metrics
        if self._is_9_2_or_above(key, db):
            DB_METRICS['metrics'].update(NEWER_92_METRICS)
        
        cursor = db.cursor()
        try:
            for scope in (DB_METRICS, REL_METRICS, IDX_METRICS):
                # build query
                fields = ",".join(scope['metrics'].keys())
                query = scope['query'] % fields

                # execute query
                cursor.execute(query)
                results = cursor.fetchall()

                # parse results
                # A row should look like this
                # (descriptor, descriptor, ..., value, value, value, value, ...)
                # with descriptor a table, relation or index name
            
                
                for row in results:
                    # [(metric-map, value), (metric-map, value), ...]
                    # shift the results since the first columns will be the "descriptors"
                    desc = scope['descriptors']
                    x = zip(scope['metrics'], row[len(desc):])
                
                    # compute tags
                    if instance_tags is None:
                        instance_tags = []
                    # turn descriptors into tags
                    tags = instance_tags.extend(["%s:%s" % (d[0][1], d for d in zip(desc, row[:len(desc)])])

                # [(metric, value), (metric, value), ...]
                metric_name = lambda name: "postgresql.%s" % metrics_to_collect[metrics_keys[i-1]][0]
                metric_type = metrics_to_collect[metrics_keys[i-1]][1]
                if metric_type == GAUGE:
                    self.gauge(metric_name, value, tags=tags)
                elif metric_type == RATE:
                    self.rate(metric_name, value, tags=tags)
                            
                result = cursor.fetchone()
        finally:
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
        relations = instance.get('relations', [])
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
        self._collect_stats(key, db, tags, relations)

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

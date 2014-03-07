from checks import AgentCheck, CheckException

class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics
    """

    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    
    # turning columns into tags
    DB_METRICS = {
        'descriptors': [
            ('datname', 'db')
        ],
        'metrics': {
            'numbackends'       : ('postgresql.connections', GAUGE),
            'xact_commit'       : ('postgresql.commits', RATE),
            'xact_rollback'     : ('postgresql.rollbacks', RATE),
            'blks_read'         : ('postgresql.disk_read', RATE),
            'blks_hit'          : ('postgresql.buffer_hit', RATE),
            'tup_returned'      : ('postgresql.rows_returned', RATE),
            'tup_fetched'       : ('postgresql.rows_fetched', RATE),
            'tup_inserted'      : ('postgresql.rows_inserted', RATE),
            'tup_updated'       : ('postgresql.rows_updated', RATE),
            'tup_deleted'       : ('postgresql.rows_deleted', RATE),
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

    NEWER_92_METRICS = {
        'deadlocks'         : ('postgresql.deadlocks', GAUGE),
        'temp_bytes'        : ('postgresql.temp_bytes', RATE),
        'temp_files'        : ('postgresql.temp_files', RATE),
    }

    REL_METRICS = {
        'descriptors': [
            ('relname', 'table')
        ],
        'metrics': {
            'seq_scan'          : ('postgresql.seq_scans', RATE),
            'seq_tup_read'      : ('postgresql.seq_rows_read', RATE),
            'idx_scan'          : ('postgresql.index_scans', RATE),
            'idx_tup_fetch'     : ('postgresql.index_rows_fetched', RATE),
            'n_tup_ins'         : ('postgresql.rows_inserted', RATE),
            'n_tup_upd'         : ('postgresql.rows_updated', RATE),
            'n_tup_del'         : ('postgresql.rows_deleted', RATE),
            'n_tup_hot_upd'     : ('postgresql.rows_hot_updated', RATE),
            'n_live_tup'        : ('postgresql.live_rows', GAUGE),
            'n_dead_tup'        : ('postgresql.dead_rows', GAUGE),
        },
        'query': """
SELECT relname,
       %s
  FROM pg_stat_user_tables
 WHERE relname = ANY(%s)""",
        'relation': True,
    }

    IDX_METRICS = {
        'descriptors': [
            ('relname', 'table'),
            ('indexrelname', 'index')
        ],
        'metrics': {
            'idx_scan'          : ('postgresql.index_scans', RATE),
            'idx_tup_read'      : ('postgresql.index_rows_read', RATE),
            'idx_tup_fetch'     : ('postgresql.index_rows_fetched', RATE),
        },
        'query': """
SELECT relname,
       indexrelname,
       %s
  FROM pg_stat_user_indexes
 WHERE relname = ANY(%s)""",
        'relation': True,
    }


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
            return version >= [9, 2, 0]

        return False

    def _collect_stats(self, key, db, instance_tags, relations):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        """

        # Extended 9.2+ metrics
        if self._is_9_2_or_above(key, db):
            self.DB_METRICS['metrics'].update(self.NEWER_92_METRICS)

        # Do we need relation-specific metrics?
        if not relations:
            metric_scope = (self.DB_METRICS,)
        else:
            metric_scope = (self.DB_METRICS, self.REL_METRICS, self.IDX_METRICS)
  
        for scope in metric_scope:
            # build query
            cols = scope['metrics'].keys()  # list of metrics to query, in some order
            # we must remember that order to parse results
            cursor = db.cursor()
            
            # if this is a relation-specific query, we need to list all relations last
            if scope['relation'] and len(relations) > 0:
                query = scope['query'] % (", ".join(cols), "%s")  # Keep the last %s intact
                self.log.debug("Running query: %s with relations: %s" % (query, relations))
                cursor.execute(query, (relations, ))
            else:
                query = scope['query'] % (", ".join(cols))
                self.log.debug("Running query: %s" % query)
                cursor.execute(query)

            results = cursor.fetchall()
            cursor.close()
                
            # parse & submit results
            # A row should look like this
            # (descriptor, descriptor, ..., value, value, value, value, ...)
            # with descriptor a PG relation or index name, which we use to create the tags
            for row in results:
                # turn descriptors into tags
                desc = scope['descriptors']
                # Check that all columns will be processed
                assert len(row) == len(cols) + len(desc)
                
                # Build tags
                # descriptors are: (pg_name, dd_tag_name): value
                # Special-case the "db" tag, which overrides the one that is passed as instance_tag
                # The reason is that pg_stat_database returns all databases regardless of the
                # connection.
                if not scope['relation']:
                    tags = [t for t in instance_tags if not t.startswith("db:")]
                else:
                    tags = [t for t in instance_tags]

                tags += ["%s:%s" % (d[0][1], d[1]) for d in zip(desc, row[:len(desc)])]

                # [(metric-map, value), (metric-map, value), ...]
                # metric-map is: (dd_name, "rate"|"gauge")
                # shift the results since the first columns will be the "descriptors"
                values = zip([scope['metrics'][c] for c in cols], row[len(desc):])
                
                # To submit simply call the function for each value v
                # v[0] == (metric_name, submit_function)
                # v[1] == the actual value
                # tags are
                [v[0][1](self, v[0][0], v[1], tags=tags) for v in values]
            

    def get_connection(self, key, host, port, user, password, dbname):
        "Get and memoize connections to instances"
        if key in self.dbs:
            return self.dbs[key]

        elif host != "" and user != "":
            try:
                import psycopg2 as pg
            except ImportError:
                raise ImportError("psycopg2 library cannot be imported. Please check the installation instruction on the Datadog Website.")
            
            if host == 'localhost' and password == '':
                # Use ident method
                connection = pg.connect("user=%s dbname=%s" % (user, dbname))
            elif port != '':
                connection = pg.connect(host=host, port=port, user=user,
                    password=password, database=dbname)
            else:
                connection = pg.connect(host=host, user=user, password=password,
                    database=dbname)
        else:
            if not host:
                raise CheckException("Please specify a Postgres host to connect to.")
            elif not user:
                raise CheckException("Please specify a user to connect to Postgres as.")

        try:
            connection.autocommit = True
        except AttributeError:
            # connection.autocommit was added in version 2.4.2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        self.dbs[key] = connection
        return connection


    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        password = instance.get('password', '')
        tags = instance.get('tags', [])
        dbname = instance.get('dbname', 'postgres')
        relations = instance.get('relations', [])

        key = '%s:%s:%s' % (host, port,dbname)
        db = self.get_connection(key, host, port, user, password, dbname)

        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        
        # preset tags to the database name
        tags.extend(["db:%s" % dbname])

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

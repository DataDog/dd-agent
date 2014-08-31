"""PostgreSQL check

Collects database-wide metrics and optionally per-relation metrics.
"""
# project
from checks import AgentCheck, CheckException

# 3rd party
import pg8000 as pg
from pg8000 import InterfaceError

class ShouldRestartException(Exception): pass

class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics
    """
    SOURCE_TYPE_NAME = 'postgresql'
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge

    # turning columns into tags
    DB_METRICS = {
        'descriptors': [
            ('datname', 'db')
        ],
        'metrics': {},
        'query': """
SELECT datname,
       %s
  FROM pg_stat_database
 WHERE datname not ilike 'template%%'
   AND datname not ilike 'postgres'
""",
        'relation': False,
    }

    BGW_METRICS = {
        'descriptors': [],
        'metrics': {
            'checkpoints_timed'    : ('postgresql.bgwriter.checkpoints_timed', RATE),
            'checkpoints_req'      : ('postgresql.bgwriter.checkpoints_requested', RATE),
            'checkpoint_write_time': ('postgresql.bgwriter.write_time', RATE),
            'checkpoint_sync_time' : ('postgresql.bgwriter.sync_time', RATE),
            'buffers_checkpoint'   : ('postgresql.bgwriter.buffers_checkpoint', RATE),
            'buffers_clean'        : ('postgresql.bgwriter.buffers_clean', RATE),
            'maxwritten_clean'     : ('postgresql.bgwriter.maxwritten_clean', RATE),
            'buffers_backend'      : ('postgresql.bgwriter.buffers_backend', RATE),
            'buffers_backend_fsync': ('postgresql.bgwriter.buffers_backend_fsync', RATE),
            'buffers_alloc'        : ('postgresql.bgwriter.buffers_alloc', RATE),
        },
        'query': "select %s FROM pg_stat_bgwriter",
        'relation': False,
    }

    LOCK_METRICS = {
        'descriptors': [
            ('mode', 'lock_mode'),
            ('relname', 'table'),
        ],
        'metrics': {
            'lock_count'       : ('postgresql.locks', GAUGE),
        },
        'query': """
SELECT mode,
       pc.relname,
       count(*) AS %s
  FROM pg_locks l
  JOIN pg_class pc ON (l.relation = pc.oid)
 WHERE l.mode IS NOT NULL
   AND pc.relname NOT LIKE 'pg_%%'
 GROUP BY pc.relname, mode""",
        'relation': False,
    }

    COMMON_METRICS = {
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

    SIZE_METRICS = {
        'descriptors': [
            ('relname', 'table'),
        ],
        'metrics': {
            'pg_table_size(C.oid)'  : ('postgresql.table_size', GAUGE),
            'pg_indexes_size(C.oid)'  : ('postgresql.index_size', GAUGE),
            'pg_total_relation_size(C.oid)': ('postgresql.total_size', GAUGE),
        },
        'relation': True,
        'query': """
SELECT
  relname,
  %s
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
WHERE nspname NOT IN ('pg_catalog', 'information_schema') AND
  nspname !~ '^pg_toast' AND
  relkind IN ('r') AND
  relname = ANY(%s)"""
    }

    # Individual metrics with tuple of (query, metric_name, metric_type)
    MAX_CONNECTIONS_METRIC = ('SHOW max_connections;', 'postgresql.max_connections', GAUGE)

    HOT_STANDBY_METRIC = ('select now() - pg_last_xact_replay_timestamp() AS replication_delay;', 'postgresql.replication_delay', GAUGE)


    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}
        self.versions = {}
        self.instance_metrics = {}

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

    def _get_instance_metrics(self, key, db):
        """Use either COMMON_METRICS or COMMON_METRICS + NEWER_92_METRICS
        depending on the postgres version.
        Uses a dictionnary to save the result for each instance
        """
        # Extended 9.2+ metrics if needed
        metrics = self.instance_metrics.get(key)
        if metrics is None:
            if self._is_9_2_or_above(key, db):
                self.instance_metrics[key] = dict(self.COMMON_METRICS, **self.NEWER_92_METRICS)
            else:
                self.instance_metrics[key] = dict(self.COMMON_METRICS)
            metrics = self.instance_metrics.get(key)
        return metrics

    def _collect_stats(self, key, db, instance_tags, relations):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        """

        self.DB_METRICS['metrics'] = self._get_instance_metrics(key, db)

        # Do we need relation-specific metrics?
        if not relations:
            metric_scope = (self.DB_METRICS, self.BGW_METRICS, self.LOCK_METRICS)
        else:
            metric_scope = (self.DB_METRICS, self.BGW_METRICS, self.LOCK_METRICS,
                            self.REL_METRICS, self.IDX_METRICS, self.SIZE_METRICS)

        try:
            cursor = db.cursor()

            for scope in metric_scope:
                # build query
                cols = scope['metrics'].keys()  # list of metrics to query, in some order
                # we must remember that order to parse results

                # if this is a relation-specific query, we need to list all relations last
                if scope['relation'] and len(relations) > 0:
                    query = scope['query'] % (", ".join(cols), "%s")  # Keep the last %s intact
                    self.log.debug("Running query: %s with relations: %s" % (query, relations))
                    cursor.execute(query, (relations, ))
                else:
                    query = scope['query'] % (", ".join(cols))
                    self.log.debug("Running query: %s" % query)
                    cursor.execute(query.replace(r'%', r'%%'))

                results = cursor.fetchall()

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

            if not results:
                self.warning('No results were found for query: "%s"' % query)

            # Query for miscellaneous metrics
            query = self.MAX_CONNECTIONS_METRIC[0]
            cursor.execute(query)
            result = cursor.fetchone()
            self.MAX_CONNECTIONS_METRIC[2](self, self.MAX_CONNECTIONS_METRIC[1], result[0], tags=instance_tags)

            # Query for percent usage of max_connections
            cursor.execute('show max_connections')
            max_conn = cursor.fetchone()[0]
            cursor.execute('SELECT sum(numbackends) FROM pg_stat_database')
            current_conn = cursor.fetchone()[0]
            percent_usage = float(current_conn) / float(max_conn)
            self.gauge('postgresql.percent_usage_connections', percent_usage, tags=instance_tags)

            # check if hot_standby is on before running hot standby metrics (replication delay)
            cursor.execute('show hot_standby')
            if cursor.fetchone()[0] == 'on':
                query = self.HOT_STANDBY_METRIC[0]
                cursor.execute(query)
                # Python interprets the return value of the replication delay output from postgres as a timedelta
                # Therefore, you must use the seconds attribute on the timedelta object in order to get the correct metric value.
                result = cursor.fetchone()[0]
                if result is not None:
                    if result.days < 0:
                        self.HOT_STANDBY_METRIC[2](self, self.HOT_STANDBY_METRIC[1], 0, tags=instance_tags)
                    else:
                        self.HOT_STANDBY_METRIC[2](self, self.HOT_STANDBY_METRIC[1], result.microseconds / 1000000.0, tags=instance_tags)
            cursor.close()
        except InterfaceError, e:
            self.log.error("Connection error: %s" % str(e))
            raise ShouldRestartException

    def get_connection(self, key, host, port, user, password, dbname, use_cached=True):
        "Get and memoize connections to instances"
        if key in self.dbs and use_cached:
            return self.dbs[key]

        elif host != "" and user != "":
            try:
                service_check_tags = [
                    "host:%s" % host,
                    "port:%s" % port
                ]
                if dbname:
                    service_check_tags.append("db:%s" % dbname)

                if host == 'localhost' and password == '':
                    # Use ident method
                    connection = pg.connect("user=%s dbname=%s" % (user, dbname))
                elif port != '':
                    connection = pg.connect(host=host, port=port, user=user,
                        password=password, database=dbname)
                else:
                    connection = pg.connect(host=host, user=user, password=password,
                        database=dbname)
                status = AgentCheck.OK
                self.service_check('postgres.can_connect', status, tags=service_check_tags)
                self.log.info('pg status: %s' % status)

            except Exception:
                status = AgentCheck.CRITICAL
                self.service_check('postgres.can_connect', status, tags=service_check_tags)
                self.log.info('pg status: %s' % status)
                raise
        else:
            if not host:
                raise CheckException("Please specify a Postgres host to connect to.")
            elif not user:
                raise CheckException("Please specify a user to connect to Postgres as.")

        connection.autocommit = True

        self.dbs[key] = connection
        return connection


    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        password = instance.get('password', '')
        tags = instance.get('tags', [])
        dbname = instance.get('dbname', None)
        relations = instance.get('relations', [])

        if relations and not dbname:
            self.warning('"dbname" parameter must be set when using the "relations" parameter.')

        if dbname is None:
            dbname = 'postgres'

        key = '%s:%s:%s' % (host, port, dbname)

        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        # preset tags to the database name
        tags.extend(["db:%s" % dbname])

        # Collect metrics
        try:
            # Check version
            db = self.get_connection(key, host, port, user, password, dbname)
            version = self._get_version(key, db)
            self.log.debug("Running check against version %s" % version)
            self._collect_stats(key, db, tags, relations)
        except ShouldRestartException:
            self.log.info("Resetting the connection")
            db = self.get_connection(key, host, port, user, password, dbname, use_cached=False)
            self._collect_stats(key, db, tags, relations)

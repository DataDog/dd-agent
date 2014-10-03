"""Pgbouncer check

Collects metrics from the pgbouncer database.
"""
from checks import AgentCheck, CheckException
from collections import OrderedDict

import psycopg2 as pg
import socket

class ShouldRestartException(Exception): pass

class PgBouncer(AgentCheck):
    """Collects metrics from pgbouncer
    """
    SOURCE_TYPE_NAME = 'pgbouncer'
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count

    STATS_METRICS = {
        'descriptors': [
            ('database', 'db'),
        ],
        'metrics': OrderedDict([
            ('total_requests', ('pgbouncer.stats.total_requests', GAUGE)),
            ('total_received', ('pgbouncer.stats.total_received', GAUGE)),
            ('total_sent', ('pgbouncer.stats.total_sent', GAUGE)),
            ('total_query_time', ('pgbouncer.stats.total_query_time', GAUGE)),
            ('avg_req', ('pgbouncer.stats.avg_req', RATE)),
            ('avg_recv', ('pgbouncer.stats.avg_recv', RATE)),
            ('avg_sent', ('pgbouncer.stats.avg_sent', RATE)),
            ('avg_query', ('pgbouncer.stats.avg_query', RATE)),
        ]),
        'query': """
SHOW STATS
""",
    }

    POOLS_METRICS = {
        'descriptors': [
            ('database', 'db'),
            ('user', 'user'),
        ],
        'metrics': OrderedDict([
            ('cl_active', ('pgbouncer.pools.cl_active', GAUGE)),
            ('cl_waiting', ('pgbouncer.pools.cl_waiting', GAUGE)),
            ('sv_active', ('pgbouncer.pools.sv_active', GAUGE)),
            ('sv_idle', ('pgbouncer.pools.sv_idle', GAUGE)),
            ('sv_used', ('pgbouncer.pools.sv_used', GAUGE)),
            ('sv_tested', ('pgbouncer.pools.sv_tested', GAUGE)),
            ('sv_login', ('pgbouncer.pools.sv_login', GAUGE)),
            ('maxwait', ('pgbouncer.pools.maxwait', GAUGE)),
        ]),
        'query': """
SHOW POOLS
""",
    }

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self.dbs = {}

    def _collect_stats(self, key, db, instance_tags):
        """Query pgbouncer for various metrics
        """

        metric_scope = (self.STATS_METRICS, self.POOLS_METRICS)

        try:
            cursor = db.cursor()
            for scope in metric_scope:

                cols = scope['metrics'].keys()

                try:
                    query = scope['query']
                    self.log.debug("Running query: %s" % query)
                    cursor.execute(query)

                    results = cursor.fetchall()
                except pg.Error, e:
                    self.log.warning("Not all metrics may be available: %s" % str(e))
                    continue

                for row in results:
                    if row[0] == 'pgbouncer':
                        continue

                    desc = scope['descriptors']
                    assert len(row) == len(cols) + len(desc)

                    tags = [t for t in instance_tags]
                    tags += ["%s:%s" % (d[0][1], d[1]) for d in zip(desc, row[:len(desc)])]

                    values = zip([scope['metrics'][c] for c in cols], row[len(desc):])

                    [v[0][1](self, v[0][0], v[1], tags=tags) for v in values]

            if not results:
                self.warning('No results were found for query: "%s"' % query)

            cursor.close()
        except pg.Error, e:
            self.log.error("Connection error: %s" % str(e))
            raise ShouldRestartException

    def _get_connection(self, key, host, port, user, password, dbname, use_cached=True):
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
                self.service_check('pgbouncer.can_connect', status, tags=service_check_tags)
                self.log.info('pgbouncer status: %s' % status)

            except Exception:
                status = AgentCheck.CRITICAL
                self.service_check('pgbouncer.can_connect', status, tags=service_check_tags)
                self.log.info('pgbouncer status: %s' % status)
                raise
        else:
            if not host:
                raise CheckException("Please specify a PgBouncer host to connect to.")
            elif not user:
                raise CheckException("Please specify a user to connect to PgBouncer as.")

        connection.autocommit = True

        self.dbs[key] = connection
        return connection

    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        user = instance.get('username', '')
        password = instance.get('password', '')
        tags = instance.get('tags', [])
        dbname = 'pgbouncer'

        key = '%s:%s:%s' % (host, port, dbname)

        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        tags.extend(["db:%s" % dbname])

        try:
            db = self._get_connection(key, host, port, user, password, dbname)
            self._collect_stats(key, db, tags)
        except ShouldRestartException:
            self.log.info("Resetting the connection")
            db = self._get_connection(key, host, port, user, password, dbname, use_cached=False)
            self._collect_stats(key, db, tags)

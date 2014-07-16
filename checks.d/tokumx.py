# stdlib
import re
import types
import time

# project
from checks import AgentCheck
from util import get_hostname

# When running with pymongo < 2.0
# Not the full spec for mongo URIs -- just extract username and password
# http://www.mongodb.org/display/DOCS/connections6
mongo_uri_re=re.compile(r'mongodb://(?P<username>[^:@]+):(?P<password>[^:@]+)@.*')

DEFAULT_TIMEOUT = 10

class TokuMX(AgentCheck):

    GAUGES = [
        "indexCounters.btree.missRatio",
        "globalLock.ratio",
        "connections.current",
        "connections.available",
        "mem.resident",
        "mem.virtual",
        "mem.mapped",
        "cursors.totalOpen",
        "cursors.timedOut",
        "uptime",

        "stats.indexes",
        "stats.indexSize",
        "stats.objects",
        "stats.dataSize",
        "stats.storageSize",

        "replSet.health",
        "replSet.state",
        "replSet.replicationLag",
        "metrics.repl.buffer.count",
        "metrics.repl.buffer.maxSizeBytes",
        "metrics.repl.buffer.sizeBytes",

        "ft.cachetable.size.current",
        "ft.cachetable.size.writing",
        "ft.cachetable.size.limit",
        "ft.locktree.size.current",
        "ft.locktree.size.limit",
        "ft.compressionRatio.leaf",
        "ft.compressionRatio.nonleaf",
        "ft.compressionRatio.overall",
        "ft.checkpoint.lastComplete.time",

        "ft.alerts.locktreeRequestsPending",
        "ft.alerts.checkpointFailures",
    ]

    RATES = [
        "indexCounters.btree.accesses",
        "indexCounters.btree.hits",
        "indexCounters.btree.misses",
        "opcounters.insert",
        "opcounters.query",
        "opcounters.update",
        "opcounters.delete",
        "opcounters.getmore",
        "opcounters.command",
        "opcountersRepl.insert",
        "opcountersRepl.query",
        "opcountersRepl.update",
        "opcountersRepl.delete",
        "opcountersRepl.getmore",
        "opcountersRepl.command",
        "asserts.regular",
        "asserts.warning",
        "asserts.msg",
        "asserts.user",
        "asserts.rollovers",
        "metrics.document.deleted",
        "metrics.document.inserted",
        "metrics.document.returned",
        "metrics.document.updated",
        "metrics.getLastError.wtime.num",
        "metrics.getLastError.wtime.totalMillis",
        "metrics.getLastError.wtimeouts",
        "metrics.operation.fastmod",
        "metrics.operation.idhack",
        "metrics.operation.scanAndOrder",
        "metrics.queryExecutor.scanned",
        "metrics.record.moves",
        "metrics.repl.apply.batches.num",
        "metrics.repl.apply.batches.totalMillis",
        "metrics.repl.apply.ops",
        "metrics.repl.network.bytes",
        "metrics.repl.network.getmores.num",
        "metrics.repl.network.getmores.totalMillis",
        "metrics.repl.network.ops",
        "metrics.repl.network.readersCreated",
        "metrics.repl.oplog.insert.num",
        "metrics.repl.oplog.insert.totalMillis",
        "metrics.repl.oplog.insertBytes",
        "metrics.ttl.deletedDocuments",
        "metrics.ttl.passes",

        "ft.fsync.count",
        "ft.fsync.time",
        "ft.log.count",
        "ft.log.time",
        "ft.log.bytes",
        "ft.cachetable.miss.count",
        "ft.cachetable.miss.time",
        "ft.cachetable.miss.full.count",
        "ft.cachetable.miss.full.time",
        "ft.cachetable.miss.partial.count",
        "ft.cachetable.miss.partial.time",
        "ft.cachetable.evictions.partial.nonleaf.clean.count",
        "ft.cachetable.evictions.partial.nonleaf.clean.bytes",
        "ft.cachetable.evictions.partial.leaf.clean.count",
        "ft.cachetable.evictions.partial.leaf.clean.bytes",
        "ft.cachetable.evictions.full.nonleaf.clean.count",
        "ft.cachetable.evictions.full.nonleaf.clean.bytes",
        "ft.cachetable.evictions.full.nonleaf.dirty.count",
        "ft.cachetable.evictions.full.nonleaf.dirty.bytes",
        "ft.cachetable.evictions.full.nonleaf.dirty.time",
        "ft.cachetable.evictions.full.leaf.clean.count",
        "ft.cachetable.evictions.full.leaf.clean.bytes",
        "ft.cachetable.evictions.full.leaf.dirty.count",
        "ft.cachetable.evictions.full.leaf.dirty.bytes",
        "ft.cachetable.evictions.full.leaf.dirty.time",
        "ft.checkpoint.count",
        "ft.checkpoint.time",
        "ft.checkpoint.begin.time",
        "ft.checkpoint.write.nonleaf.count",
        "ft.checkpoint.write.nonleaf.time",
        "ft.checkpoint.write.nonleaf.bytes.uncompressed",
        "ft.checkpoint.write.nonleaf.bytes.compressed",
        "ft.checkpoint.write.leaf.count",
        "ft.checkpoint.write.leaf.time",
        "ft.checkpoint.write.leaf.bytes.uncompressed",
        "ft.checkpoint.write.leaf.bytes.compressed",
        "ft.serializeTime.nonleaf.serialize",
        "ft.serializeTime.nonleaf.compress",
        "ft.serializeTime.nonleaf.decompress",
        "ft.serializeTime.nonleaf.deserialize",
        "ft.serializeTime.leaf.serialize",
        "ft.serializeTime.leaf.compress",
        "ft.serializeTime.leaf.decompress",
        "ft.serializeTime.leaf.deserialize",

        "ft.alerts.longWaitEvents.logBufferWait",
        "ft.alerts.longWaitEvents.fsync.count",
        "ft.alerts.longWaitEvents.fsync.time",
        "ft.alerts.longWaitEvents.cachePressure.count",
        "ft.alerts.longWaitEvents.cachePressure.time",
        "ft.alerts.longWaitEvents.checkpointBegin.count",
        "ft.alerts.longWaitEvents.checkpointBegin.time",
        "ft.alerts.longWaitEvents.locktreeWait.count",
        "ft.alerts.longWaitEvents.locktreeWait.time",
        "ft.alerts.longWaitEvents.locktreeWaitEscalation.count",
        "ft.alerts.longWaitEvents.locktreeWaitEscalation.time",
    ]

    METRICS = GAUGES + RATES

    def __init__(self, name, init_config, agentConfig):
        AgentCheck.__init__(self, name, init_config, agentConfig)
        self._last_state_by_server = {}

    def get_library_versions(self):
        try:
            import pymongo
            version = pymongo.version
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"pymongo": version}

    def check_last_state(self, state, server, agentConfig):
        if self._last_state_by_server.get(server, -1) != state:
            self._last_state_by_server[server] = state
            return self.create_event(state, server, agentConfig)

    def create_event(self, state, server, agentConfig):
        """Create an event with a message describing the replication
            state of a mongo node"""

        def get_state_description(state):
            if state == 0: return 'Starting Up'
            elif state == 1: return 'Primary'
            elif state == 2: return 'Secondary'
            elif state == 3: return 'Recovering'
            elif state == 4: return 'Fatal'
            elif state == 5: return 'Starting up (initial sync)'
            elif state == 6: return 'Unknown'
            elif state == 7: return 'Arbiter'
            elif state == 8: return 'Down'
            elif state == 9: return 'Rollback'

        status = get_state_description(state)
        hostname = get_hostname(agentConfig)
        msg_title = "%s is %s" % (server, status)
        msg = "TokuMX %s just reported as %s" % (server, status)

        self.event({
            'timestamp': int(time.time()),
            'event_type': 'tokumx',
            'api_key': agentConfig['api_key'],
            'msg_title': msg_title,
            'msg_text': msg,
            'host': hostname
        })

    def check(self, instance):
        """
        Returns a dictionary that looks a lot like what's sent back by db.serverStatus()
        """
        if 'server' not in instance:
            self.log.warn("Missing 'server' in tokumx config")
            return

        server = instance['server']

        ssl_params = {
            'ssl': instance.get('ssl', None),
            'ssl_keyfile': instance.get('ssl_keyfile', None),
            'ssl_certfile': instance.get('ssl_certfile', None),
            'ssl_cert_reqs':  instance.get('ssl_cert_reqs', None),
            'ssl_ca_certs': instance.get('ssl_ca_certs', None)
        }

        for key, param in ssl_params.items():
            if param is None:
                del ssl_params[key]

        tags = instance.get('tags', [])
        tags.append('server:%s' % server)
        # de-dupe tags to avoid a memory leak
        tags = list(set(tags))

        try:
            from pymongo import MongoClient, ReadPreference
        except ImportError:
            self.log.error('tokumx.yaml exists but pymongo module can not be imported. Skipping check.')
            raise Exception('Python PyMongo Module can not be imported. Please check the installation instruction on the Datadog Website')

        try:
            from pymongo import uri_parser
            # Configuration a URL, mongodb://user:pass@server/db
            parsed = uri_parser.parse_uri(server)
        except ImportError:
            # uri_parser is pymongo 2.0+
            matches = mongo_uri_re.match(server)
            if matches:
                parsed = matches.groupdict()
            else:
                parsed = {}
        username = parsed.get('username')
        password = parsed.get('password')
        db_name = parsed.get('database')

        if not db_name:
            self.log.info('No TokuMX database found in URI. Defaulting to admin.')
            db_name = 'admin'

        do_auth = True
        if username is None or password is None:
            self.log.debug("TokuMX: cannot extract username and password from config %s" % server)
            do_auth = False

        conn = MongoClient(server, socketTimeoutMS=DEFAULT_TIMEOUT*1000, **ssl_params)
        db = conn[db_name]
        if do_auth:
            if not db.authenticate(username, password):
                self.log.error("TokuMX: cannot connect with config %s" % server)

        if conn.is_mongos:
            tags.append('role:mongos')
            config = conn['config']
            agg_result = config['chunks'].aggregate([{'$group': {'_id': {'ns': '$ns', 'shard': '$shard'}, 'count': {'$sum': 1}}}])
            if agg_result['ok']:
                for doc in agg_result['result']:
                    chunk_tags = list(tags)
                    parts = doc['_id']['ns'].split('.', 1)
                    chunk_tags.append('db:%s' % parts[0])
                    chunk_tags.append('coll:%s' % parts[1])
                    chunk_tags.append('shard:%s' % doc['_id']['shard'])
                    shard_doc = config['shards'].find_one(doc['_id']['shard'])
                    host_parts = shard_doc['host'].split('/', 1)
                    if len(host_parts) == 2:
                        chunk_tags.append('replset:%s' % host_parts[0])
                    self.gauge('tokumx.sharding.chunks', doc['count'], tags=chunk_tags)
        else:
            status = db["$cmd"].find_one({"serverStatus": 1})
            status['stats'] = db.command('dbstats')

            # Handle replica data, if any
            # See http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus
            try:
                data = {}

                replSet = conn['admin'].command('replSetGetStatus')
                if replSet:
                    primary = None
                    current = None

                    # find nodes: master and current node (ourself)
                    for member in replSet.get('members'):
                        if member.get('self'):
                            current = member
                        if int(member.get('state')) == 1:
                            primary = member

                    # If we have both we can compute a lag time
                    if current is not None and primary is not None:
                        lag = primary['optimeDate'] - current['optimeDate']
                        # Python 2.7 has this built in, python < 2.7 don't...
                        if hasattr(lag,'total_seconds'):
                            data['replicationLag'] = lag.total_seconds()
                        else:
                            data['replicationLag'] = (lag.microseconds + \
                                                      (lag.seconds + lag.days * 24 * 3600) * 10**6) / 10.0**6

                    if current is not None:
                        data['health'] = current['health']

                    tags.append('replset:%s' % replSet['set'])
                    tags.append('replstate:%s' % current['stateStr'])
                    if current['stateStr'] == 'PRIMARY':
                        tags.append('role:primary')
                    else:
                        tags.append('role:secondary')
                        conn.read_preference = ReadPreference.SECONDARY

                    data['state'] = replSet['myState']
                    self.check_last_state(data['state'], server, self.agentConfig)
                    status['replSet'] = data
            except Exception, e:
                if "OperationFailure" in repr(e) and "replSetGetStatus" in str(e):
                    pass
                else:
                    raise e

            for dbname in conn.database_names():
                db_tags = list(tags)
                db_tags.append('db:%s' % dbname)
                db = conn[dbname]
                stats = db.command('dbstats')
                for m, v in stats.items():
                    if m in ['db', 'ok']:
                        continue
                    m = 'stats.db.%s' % m
                    m = self.normalize(m, 'tokumx')
                    self.gauge(m, v, db_tags)
                for collname in db.collection_names(False):
                    coll_tags = list(db_tags)
                    coll_tags.append('coll:%s' % collname)
                    stats = db.command('collStats', collname)
                    for m, v in stats.items():
                        if m in ['db', 'ok']:
                            continue
                        if m == 'indexDetails':
                            for idx_stats in v:
                                idx_tags = list(coll_tags)
                                idx_tags.append('idx:%s' % idx_stats['name'])
                                for k in ['count', 'size', 'avgObjSize', 'storageSize']:
                                    mname = 'stats.idx.%s' % k
                                    mname = self.normalize(mname, 'tokumx')
                                    self.gauge(mname, idx_stats[k], tags=idx_tags)
                                for k in ['queries', 'nscanned', 'nscannedObjects', 'inserts', 'deletes']:
                                    mname = 'stats.idx.%s' % k
                                    mname = self.normalize(mname, 'tokumx')
                                    self.rate(mname, idx_stats[k], tags=idx_tags)
                        else:
                            m = 'stats.coll.%s' % m
                            m = self.normalize(m, 'tokumx')
                            self.gauge(m, v, coll_tags)

            # If these keys exist, remove them for now as they cannot be serialized
            try:
                status['backgroundFlushing'].pop('last_finished')
            except KeyError:
                pass
            try:
                status.pop('localTime')
            except KeyError:
                pass

            # Go through the metrics and save the values
            for m in self.METRICS:
                # each metric is of the form: x.y.z with z optional
                # and can be found at status[x][y][z]
                value = status
                try:
                    for c in m.split("."):
                        value = value[c]
                except KeyError:
                    continue

                # value is now status[x][y][z]
                assert type(value) in (types.IntType, types.LongType, types.FloatType)

                # Check if metric is a gauge or rate
                if m in self.GAUGES:
                    m = self.normalize(m, 'tokumx')
                    self.gauge(m, value, tags=tags)

                if m in self.RATES:
                    m = self.normalize(m, 'tokumx') + "ps"
                    self.rate(m, value, tags=tags)

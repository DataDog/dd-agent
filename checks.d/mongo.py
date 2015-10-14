# stdlib
import time

# 3p
import pymongo

# project
from checks import AgentCheck
from util import get_hostname

DEFAULT_TIMEOUT = 30


class MongoDb(AgentCheck):
    SERVICE_CHECK_NAME = 'mongodb.can_connect'
    SOURCE_TYPE_NAME = 'mongodb'

    GAUGES = [
        # L21-24 removed as of V 3.0.0
        "indexCounters.btree.missRatio",
        "indexCounters.missRatio",
        "globalLock.ratio",
        "globalLock.lockTime",
        "globalLock.totalTime",
        "globalLock.currentQueue.total",
        "globalLock.currentQueue.readers",
        "globalLock.currentQueue.writers",
        "globalLock.activeClients.total",
        "globalLock.activeClients.readers",
        "globalLock.activeClients.writers",
        "connections.current",
        "connections.available",
        "connections.totalCreated",
        "mem.bits",
        "mem.resident",
        "mem.virtual",
        "mem.mapped",
        "mem.mappedWithJournal",
        "cursors.totalOpen",
        "cursors.timedOut",
        "uptime",

        "stats.collections",
        "stats.objects",
        "stats.avgObjSize",
        "stats.dataSize",
        "stats.storageSize",
        "stats.numExtents",
        "stats.indexes",
        "stats.indexSize",
        "stats.fileSize",
        "stats.nsSizeMB",

        "replSet.health",
        "replSet.state",
        "replSet.replicationLag",

        "metrics.repl.buffer.count",
        "metrics.repl.buffer.maxSizeBytes",
        "metrics.repl.buffer.sizeBytes",

        "tcmalloc.generic.current_allocated_bytes",
        "tcmalloc.generic.heap_size",
        "tcmalloc.tcmalloc.pageheap_free_bytes",
        "tcmalloc.tcmalloc.pageheap_unmapped_bytes",
        "tcmalloc.tcmalloc.max_total_thread_cache_bytes",
        "tcmalloc.tcmalloc.current_total_thread_cache_bytes",
        "tcmalloc.tcmalloc.central_cache_free_bytes",
        "tcmalloc.tcmalloc.transfer_cache_free_bytes",
        "tcmalloc.tcmalloc.thread_cache_free_bytes",
        "tcmalloc.tcmalloc.aggressive_memory_decommit",
    ]

    RATES = [
        # indexCounters removed as of V 3.0.0
        "indexCounters.btree.accesses",
        "indexCounters.btree.hits",
        "indexCounters.btree.misses",
        "indexCounters.accesses",
        "indexCounters.hits",
        "indexCounters.misses",
        "indexCounters.resets",
        "extra_info.page_faults",
        "extra_info.heap_usage_bytes",
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
        "metrics.repl.preload.indexes.num"
        "metrics.repl.preload.indexes.totalMillis"
        "metrics.repl.oplog.insert.num",
        "metrics.repl.oplog.insert.totalMillis",
        "metrics.repl.oplog.insertBytes",
        "metrics.ttl.deletedDocuments",
        "metrics.ttl.passes",
    ]

    METRICS = GAUGES + RATES

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self._last_state_by_server = {}

    def get_library_versions(self):
        return {"pymongo": pymongo.version}

    def check_last_state(self, state, clean_server_name, agentConfig):
        if self._last_state_by_server.get(clean_server_name, -1) != state:
            self._last_state_by_server[clean_server_name] = state
            return self.create_event(state, clean_server_name, agentConfig)

    def create_event(self, state, clean_server_name, agentConfig):
        """Create an event with a message describing the replication
            state of a mongo node"""

        def get_state_description(state):
            if state == 0:
                return 'Starting Up'
            elif state == 1:
                return 'Primary'
            elif state == 2:
                return 'Secondary'
            elif state == 3:
                return 'Recovering'
            elif state == 4:
                return 'Fatal'
            elif state == 5:
                return 'Starting up (forking threads)'
            elif state == 6:
                return 'Unknown'
            elif state == 7:
                return 'Arbiter'
            elif state == 8:
                return 'Down'
            elif state == 9:
                return 'Rollback'

        status = get_state_description(state)
        hostname = get_hostname(agentConfig)
        msg_title = "%s is %s" % (clean_server_name, status)
        msg = "MongoDB %s just reported as %s" % (clean_server_name, status)

        self.event({
            'timestamp': int(time.time()),
            'event_type': 'Mongo',
            'api_key': agentConfig.get('api_key', ''),
            'msg_title': msg_title,
            'msg_text': msg,
            'host': hostname
        })

    def check(self, instance):
        """
        Returns a dictionary that looks a lot like what's sent back by
        db.serverStatus()
        """
        if 'server' not in instance:
            raise Exception("Missing 'server' in mongo config")

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

        # Configuration a URL, mongodb://user:pass@server/db
        parsed = pymongo.uri_parser.parse_uri(server)
        username = parsed.get('username')
        password = parsed.get('password')
        db_name = parsed.get('database')
        clean_server_name = server.replace(password, "*"*5) if password is not None else server

        tags = instance.get('tags', [])
        tags.append('server:%s' % clean_server_name)

        # de-dupe tags to avoid a memory leak
        tags = list(set(tags))

        if not db_name:
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            db_name = 'admin'

        service_check_tags = [
            "db:%s" % db_name
        ]

        nodelist = parsed.get('nodelist')
        if nodelist:
            host = nodelist[0][0]
            port = nodelist[0][1]
            service_check_tags = service_check_tags + [
                "host:%s" % host,
                "port:%s" % port
            ]

        do_auth = True
        if username is None or password is None:
            self.log.debug("Mongo: cannot extract username and password from config %s" % server)
            do_auth = False

        timeout = float(instance.get('timeout', DEFAULT_TIMEOUT)) * 1000
        try:
            cli = pymongo.mongo_client.MongoClient(
                server,
                socketTimeoutMS=timeout,
                read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED,
                **ssl_params)
            # some commands can only go against the admin DB
            admindb = cli['admin']
            db = cli[db_name]
        except Exception:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags)
            raise

        if do_auth and not db.authenticate(username, password):
            message = "Mongo: cannot connect with config %s" % server
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message=message)
            raise Exception(message)

        self.service_check(
            self.SERVICE_CHECK_NAME,
            AgentCheck.OK,
            tags=service_check_tags)

        status = db["$cmd"].find_one({"serverStatus": 1})
        if status['ok'] == 0:
            raise Exception(status['errmsg'].__str__())

        status['stats'] = db.command('dbstats')
        dbstats = {}
        dbstats[db_name] = {'stats': status['stats']}

        # Handle replica data, if any
        # See
        # http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus
        try:
            data = {}
            dbnames = []

            replSet = admindb.command('replSetGetStatus')
            if replSet:
                primary = None
                current = None

                # need a new connection to deal with replica sets
                setname = replSet.get('set')
                cli = pymongo.mongo_client.MongoClient(
                    server,
                    socketTimeoutMS=timeout,
                    replicaset=setname,
                    read_preference=pymongo.ReadPreference.NEAREST,
                    **ssl_params)
                db = cli[db_name]

                if do_auth and not db.authenticate(username, password):
                    message = ("Mongo: cannot connect with config %s" % server)
                    self.service_check(
                        self.SERVICE_CHECK_NAME,
                        AgentCheck.CRITICAL,
                        tags=service_check_tags,
                        message=message)
                    raise Exception(message)

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
                    if hasattr(lag, 'total_seconds'):
                        data['replicationLag'] = lag.total_seconds()
                    else:
                        data['replicationLag'] = (
                            lag.microseconds +
                            (lag.seconds + lag.days * 24 * 3600) * 10**6
                        ) / 10.0**6

                if current is not None:
                    data['health'] = current['health']

                data['state'] = replSet['myState']
                self.check_last_state(
                    data['state'],
                    clean_server_name,
                    self.agentConfig)
                status['replSet'] = data

        except Exception as e:
            if "OperationFailure" in repr(e) and "replSetGetStatus" in str(e):
                pass
            else:
                raise e

        # If these keys exist, remove them for now as they cannot be serialized
        try:
            status['backgroundFlushing'].pop('last_finished')
        except KeyError:
            pass
        try:
            status.pop('localTime')
        except KeyError:
            pass

        dbnames = cli.database_names()
        for db_n in dbnames:
            db_aux = cli[db_n]
            dbstats[db_n] = {'stats': db_aux.command('dbstats')}

        # Go through the metrics and save the values
        for m in self.METRICS:
            # each metric is of the form: x.y.z with z optional
            # and can be found at status[x][y][z]
            value = status

            if m.startswith('stats'):
                continue
            else:
                try:
                    for c in m.split("."):
                        value = value[c]
                except KeyError:
                    continue

            # value is now status[x][y][z]
            if not isinstance(value, (int, long, float)):
                raise TypeError('{0} value is a {1}, it should be an int, a float or a long instead.'
                                .format(m, type(value)))

            # Check if metric is a gauge or rate
            if m in self.GAUGES:
                m = self.normalize(m.lower(), 'mongodb')
                self.gauge(m, value, tags=tags)

            if m in self.RATES:
                m = self.normalize(m.lower(), 'mongodb') + "ps"
                self.rate(m, value, tags=tags)

        stat_metrics = filter(lambda x: x.startswith('stats.'), self.METRICS)
        for st, value in dbstats.iteritems():
            for m in stat_metrics:
                try:
                    val = value['stats'][m.split('.')[1]]
                except KeyError:
                    continue

                # value is now status[x][y][z]
                if not isinstance(val, (int, long, float)):
                    raise TypeError('{0} value is a {1}, it should be an int, a float or a long instead.'
                                    .format(m, type(val)))

                # Check if metric is a gauge or rate
                if m in self.GAUGES:
                    m = self.normalize(m.lower(), 'mongodb')
                    self.gauge(m, val, tags=tags + ['cluster:db:%s' % st])

                if m in self.RATES:
                    m = self.normalize(m.lower(), 'mongodb') + "ps"
                    self.rate(m, val, tags=tags + ['cluster:db:%s' % st])

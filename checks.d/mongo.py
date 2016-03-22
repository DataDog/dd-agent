# stdlib
import re
import time

# 3p
import pymongo

# project
from checks import AgentCheck
from util import get_hostname

DEFAULT_TIMEOUT = 30
GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate


class MongoDb(AgentCheck):
    SERVICE_CHECK_NAME = 'mongodb.can_connect'
    SOURCE_TYPE_NAME = 'mongodb'

    """
    MongoDB replica set states, as documented at
    https://docs.mongodb.org/manual/reference/replica-states/
    """
    REPLSET_STATES = {
        0: 'startup',
        1: 'primary',
        2: 'secondary',
        3: 'recovering',
        5: 'startup2',
        6: 'unknown',
        7: 'arbiter',
        8: 'down',
        9: 'rollback',
        10: 'removed'
    }

    # METRIC LIST DEFINITION
    #
    # Format
    # ------
    #   metric_name -> (metric_type, alias)
    # or
    #   metric_name -> metric_type *
    # * by default MongoDB metrics are reported under their original metric names
    """
    Core metrics collected by default.
    """
    BASE_METRICS = {
        "asserts.msg": RATE,
        "asserts.regular": RATE,
        "asserts.rollovers": RATE,
        "asserts.user": RATE,
        "asserts.warning": RATE,
        "backgroundFlushing.average_ms": GAUGE,
        "backgroundFlushing.flushes": RATE,
        "backgroundFlushing.last_ms": GAUGE,
        "backgroundFlushing.total_ms": GAUGE,
        "connections.available": GAUGE,
        "connections.current": GAUGE,
        "connections.totalCreated": GAUGE,
        "cursors.timedOut": GAUGE,
        "cursors.totalOpen": GAUGE,
        "extra_info.heap_usage_bytes": RATE,
        "extra_info.page_faults": RATE,
        "globalLock.activeClients.readers": GAUGE,
        "globalLock.activeClients.total": GAUGE,
        "globalLock.activeClients.writers": GAUGE,
        "globalLock.currentQueue.readers": GAUGE,
        "globalLock.currentQueue.total": GAUGE,
        "globalLock.currentQueue.writers": GAUGE,
        "globalLock.lockTime": GAUGE,
        "globalLock.ratio": GAUGE,                  # < 2.2
        "globalLock.totalTime": GAUGE,
        "indexCounters.accesses": RATE,
        "indexCounters.btree.accesses": RATE,       # < 2.4
        "indexCounters.btree.hits": RATE,           # < 2.4
        "indexCounters.btree.misses": RATE,         # < 2.4
        "indexCounters.btree.missRatio": GAUGE,     # < 2.4
        "indexCounters.hits": RATE,
        "indexCounters.misses": RATE,
        "indexCounters.missRatio": GAUGE,
        "indexCounters.resets": RATE,
        "mem.bits": GAUGE,
        "mem.mapped": GAUGE,
        "mem.mappedWithJournal": GAUGE,
        "mem.resident": GAUGE,
        "mem.virtual": GAUGE,
        "metrics.cursor.open.noTimeout": GAUGE,
        "metrics.cursor.open.pinned": GAUGE,
        "metrics.cursor.open.total": GAUGE,
        "metrics.cursor.timedOut": RATE,
        "metrics.document.deleted": RATE,
        "metrics.document.inserted": RATE,
        "metrics.document.returned": RATE,
        "metrics.document.updated": RATE,
        "metrics.getLastError.wtime.num": RATE,
        "metrics.getLastError.wtime.totalMillis": RATE,
        "metrics.getLastError.wtimeouts": RATE,
        "metrics.operation.fastmod": RATE,
        "metrics.operation.idhack": RATE,
        "metrics.operation.scanAndOrder": RATE,
        "metrics.operation.writeConflicts": RATE,
        "metrics.queryExecutor.scanned": RATE,
        "metrics.record.moves": RATE,
        "metrics.repl.apply.batches.num": RATE,
        "metrics.repl.apply.batches.totalMillis": RATE,
        "metrics.repl.apply.ops": RATE,
        "metrics.repl.buffer.count": GAUGE,
        "metrics.repl.buffer.maxSizeBytes": GAUGE,
        "metrics.repl.buffer.sizeBytes": GAUGE,
        "metrics.repl.network.bytes": RATE,
        "metrics.repl.network.getmores.num": RATE,
        "metrics.repl.network.getmores.totalMillis": RATE,
        "metrics.repl.network.ops": RATE,
        "metrics.repl.network.readersCreated": RATE,
        "metrics.repl.oplog.insert.num": RATE,
        "metrics.repl.oplog.insert.totalMillis": RATE,
        "metrics.repl.oplog.insertBytes": RATE,
        "metrics.repl.preload.docs.num": RATE,
        "metrics.repl.preload.docs.totalMillis": RATE,
        "metrics.repl.preload.indexes.num": RATE,
        "metrics.repl.preload.indexes.totalMillis": RATE,
        "metrics.repl.storage.freelist.search.bucketExhausted": RATE,
        "metrics.repl.storage.freelist.search.requests": RATE,
        "metrics.repl.storage.freelist.search.scanned": RATE,
        "metrics.ttl.deletedDocuments": RATE,
        "metrics.ttl.passes": RATE,
        "network.bytesIn": RATE,
        "network.bytesOut": RATE,
        "network.numRequests": RATE,
        "opcounters.command": RATE,
        "opcounters.delete": RATE,
        "opcounters.getmore": RATE,
        "opcounters.insert": RATE,
        "opcounters.query": RATE,
        "opcounters.update": RATE,
        "opcountersRepl.command": RATE,
        "opcountersRepl.delete": RATE,
        "opcountersRepl.getmore": RATE,
        "opcountersRepl.insert": RATE,
        "opcountersRepl.query": RATE,
        "opcountersRepl.update": RATE,
        "replSet.health": GAUGE,
        "replSet.replicationLag": GAUGE,
        "replSet.state": GAUGE,
        "stats.avgObjSize": GAUGE,
        "stats.collections": GAUGE,
        "stats.dataSize": GAUGE,
        "stats.fileSize": GAUGE,
        "stats.indexes": GAUGE,
        "stats.indexSize": GAUGE,
        "stats.nsSizeMB": GAUGE,
        "stats.numExtents": GAUGE,
        "stats.objects": GAUGE,
        "stats.storageSize": GAUGE,
        "uptime": GAUGE,
    }

    """
    Journaling-related operations and performance report.

    https://docs.mongodb.org/manual/reference/command/serverStatus/#serverStatus.dur
    """
    DURABILITY_METRICS = {
        "dur.commits": GAUGE,
        "dur.commitsInWriteLock": GAUGE,
        "dur.compression": GAUGE,
        "dur.earlyCommits": GAUGE,
        "dur.journaledMB": GAUGE,
        "dur.timeMs.dt": GAUGE,
        "dur.timeMs.prepLogBuffer": GAUGE,
        "dur.timeMs.remapPrivateView": GAUGE,
        "dur.timeMs.writeToDataFiles": GAUGE,
        "dur.timeMs.writeToJournal": GAUGE,
        "dur.writeToDataFilesMB": GAUGE,

        # Required version > 3.0.0
        "dur.timeMs.commits": GAUGE,
        "dur.timeMs.commitsInWriteLock": GAUGE,
    }

    """
    ServerStatus use of database commands report.
    Required version > 3.0.0.

    https://docs.mongodb.org/manual/reference/command/serverStatus/#serverStatus.metrics.commands
    """
    COMMANDS_METRICS = {
        # Required version >
        "metrics.commands.count.failed": RATE,
        "metrics.commands.count.total": GAUGE,
        "metrics.commands.createIndexes.failed": RATE,
        "metrics.commands.createIndexes.total": GAUGE,
        "metrics.commands.delete.failed": RATE,
        "metrics.commands.delete.total": GAUGE,
        "metrics.commands.eval.failed": RATE,
        "metrics.commands.eval.total": GAUGE,
        "metrics.commands.findAndModify.failed": RATE,
        "metrics.commands.findAndModify.total": GAUGE,
        "metrics.commands.insert.failed": RATE,
        "metrics.commands.insert.total": GAUGE,
        "metrics.commands.update.failed": RATE,
        "metrics.commands.update.total": GAUGE,
    }

    """
    ServerStatus locks report.
    Required version > 3.0.0.

    https://docs.mongodb.org/manual/reference/command/serverStatus/#server-status-locks
    """
    LOCKS_METRICS = {
        "locks.Collection.acquireCount.R": RATE,
        "locks.Collection.acquireCount.r": RATE,
        "locks.Collection.acquireCount.W": RATE,
        "locks.Collection.acquireCount.w": RATE,
        "locks.Collection.acquireWaitCount.R": RATE,
        "locks.Collection.acquireWaitCount.W": RATE,
        "locks.Collection.timeAcquiringMicros.R": RATE,
        "locks.Collection.timeAcquiringMicros.W": RATE,
        "locks.Database.acquireCount.r": RATE,
        "locks.Database.acquireCount.R": RATE,
        "locks.Database.acquireCount.w": RATE,
        "locks.Database.acquireCount.W": RATE,
        "locks.Database.acquireWaitCount.r": RATE,
        "locks.Database.acquireWaitCount.R": RATE,
        "locks.Database.acquireWaitCount.w": RATE,
        "locks.Database.acquireWaitCount.W": RATE,
        "locks.Database.timeAcquiringMicros.r": RATE,
        "locks.Database.timeAcquiringMicros.R": RATE,
        "locks.Database.timeAcquiringMicros.w": RATE,
        "locks.Database.timeAcquiringMicros.W": RATE,
        "locks.Global.acquireCount.r": RATE,
        "locks.Global.acquireCount.R": RATE,
        "locks.Global.acquireCount.w": RATE,
        "locks.Global.acquireCount.W": RATE,
        "locks.Global.acquireWaitCount.r": RATE,
        "locks.Global.acquireWaitCount.R": RATE,
        "locks.Global.acquireWaitCount.w": RATE,
        "locks.Global.acquireWaitCount.W": RATE,
        "locks.Global.timeAcquiringMicros.r": RATE,
        "locks.Global.timeAcquiringMicros.R": RATE,
        "locks.Global.timeAcquiringMicros.w": RATE,
        "locks.Global.timeAcquiringMicros.W": RATE,
        "locks.Metadata.acquireCount.R": RATE,
        "locks.Metadata.acquireCount.W": RATE,
        "locks.MMAPV1Journal.acquireCount.r": RATE,
        "locks.MMAPV1Journal.acquireCount.w": RATE,
        "locks.MMAPV1Journal.acquireWaitCount.r": RATE,
        "locks.MMAPV1Journal.acquireWaitCount.w": RATE,
        "locks.MMAPV1Journal.timeAcquiringMicros.r": RATE,
        "locks.MMAPV1Journal.timeAcquiringMicros.w": RATE,
        "locks.oplog.acquireCount.R": RATE,
        "locks.oplog.acquireCount.w": RATE,
        "locks.oplog.acquireWaitCount.R": RATE,
        "locks.oplog.acquireWaitCount.w": RATE,
        "locks.oplog.timeAcquiringMicros.R": RATE,
        "locks.oplog.timeAcquiringMicros.w": RATE,
    }

    """
    TCMalloc memory allocator report.
    """
    TCMALLOC_METRICS = {
        "tcmalloc.generic.current_allocated_bytes": GAUGE,
        "tcmalloc.generic.heap_size": GAUGE,
        "tcmalloc.tcmalloc.aggressive_memory_decommit": GAUGE,
        "tcmalloc.tcmalloc.central_cache_free_bytes": GAUGE,
        "tcmalloc.tcmalloc.current_total_thread_cache_bytes": GAUGE,
        "tcmalloc.tcmalloc.max_total_thread_cache_bytes": GAUGE,
        "tcmalloc.tcmalloc.pageheap_free_bytes": GAUGE,
        "tcmalloc.tcmalloc.pageheap_unmapped_bytes": GAUGE,
        "tcmalloc.tcmalloc.thread_cache_free_bytes": GAUGE,
        "tcmalloc.tcmalloc.transfer_cache_free_bytes": GAUGE,
    }

    """
    WiredTiger storage engine.

    """
    WIREDTIGER_METRICS = {
        "wiredTiger.cache.bytes currently in the cache": (GAUGE, "wiredTiger.cache.bytes_currently_in_cache"),  # noqa
        "wiredTiger.cache.failed eviction of pages that exceeded the in-memory maximum": (RATE, "wiredTiger.cache.failed_eviction_of_pages_exceeding_the_in-memory_maximum"),  # noqa
        "wiredTiger.cache.in-memory page splits": GAUGE,
        "wiredTiger.cache.maximum bytes configured": GAUGE,
        "wiredTiger.cache.maximum page size at eviction": GAUGE,
        "wiredTiger.cache.pages currently held in the cache": (GAUGE, "wiredTiger.cache.pages_currently_held_in_cache"),  # noqa
        "wiredTiger.cache.pages evicted because they exceeded the in-memory maximum": (RATE, "wiredTiger.cache.pages_evicted_exceeding_the_in-memory_maximum"),  # noqa
        "wiredTiger.cache.pages evicted by application threads": RATE,
        "wiredTiger.concurrentTransactions.read.available": GAUGE,
        "wiredTiger.concurrentTransactions.read.out": GAUGE,
        "wiredTiger.concurrentTransactions.read.totalTickets": GAUGE,
        "wiredTiger.concurrentTransactions.write.available": GAUGE,
        "wiredTiger.concurrentTransactions.write.out": GAUGE,
        "wiredTiger.concurrentTransactions.write.totalTickets": GAUGE,
    }

    """
    Usage statistics for each collection.

    https://docs.mongodb.org/v3.0/reference/command/top/
    """
    TOP_METRICS = {
        "commands.count": GAUGE,
        "commands.time": GAUGE,
        "getmore.count": GAUGE,
        "getmore.time": GAUGE,
        "insert.count": GAUGE,
        "insert.time": GAUGE,
        "queries.count": GAUGE,
        "queries.time": GAUGE,
        "readLock.count": GAUGE,
        "readLock.time": GAUGE,
        "remove.count": GAUGE,
        "remove.time": GAUGE,
        "total.count": GAUGE,
        "total.time": GAUGE,
        "update.count": GAUGE,
        "update.time": GAUGE,
        "writeLock.count": GAUGE,
        "writeLock.time": GAUGE,
    }

    """
    Mapping for case-sensitive metric name suffixes.

    https://docs.mongodb.org/manual/reference/command/serverStatus/#server-status-locks
    """
    CASE_SENSITIVE_METRIC_NAME_SUFFIXES = {
        '\.R\\b': ".shared",
        '\.r\\b': ".intent_shared",
        '\.W\\b': ".exclusive",
        '\.w\\b': ".intent_exclusive",
    }

    """
    Associates with the metric list to collect.
    """
    AVAILABLE_METRICS = {
        'durability': DURABILITY_METRICS,
        'locks': LOCKS_METRICS,
        'metrics.commands': COMMANDS_METRICS,
        'tcmalloc': TCMALLOC_METRICS,
        'wiredtiger': WIREDTIGER_METRICS,
        'top': TOP_METRICS,
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self._last_state_by_server = {}
        self.metrics_to_collect_by_instance = {}

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

    def _build_metric_list_to_collect(self, additional_metrics):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Defaut metrics
        metrics_to_collect.update(self.BASE_METRICS)

        # Additional metrics metrics
        for option in additional_metrics:
            additional_metrics = self.AVAILABLE_METRICS.get(option)

            if not additional_metrics:
                self.log.warning(
                    u"Failed to extend the list of metrics to collect:"
                    " unrecognized {option} option".format(
                        option=option
                    )
                )
                continue

            self.log.debug(
                u"Adding `{option}` corresponding metrics to the list"
                " of metrics to collect.".format(
                    option=option
                )
            )
            metrics_to_collect.update(additional_metrics)

        return metrics_to_collect

    def _get_metrics_to_collect(self, instance_key, additional_metrics):
        """
        Return and cache the list of metrics to collect.
        """
        if instance_key not in self.metrics_to_collect_by_instance:
            self.metrics_to_collect_by_instance[instance_key] = \
                self._build_metric_list_to_collect(additional_metrics)
        return self.metrics_to_collect_by_instance[instance_key]

    def _resolve_metric(self, original_metric_name, metrics_to_collect, prefix=""):
        """
        Return the submit method and the metric name to use.

        The metric name is defined as follow:
        * If available, the normalized metric name alias
        * (Or) the normalized original metric name
        """

        submit_method = metrics_to_collect[original_metric_name][0] \
            if isinstance(metrics_to_collect[original_metric_name], tuple) \
            else metrics_to_collect[original_metric_name]

        metric_name = metrics_to_collect[original_metric_name][1] \
            if isinstance(metrics_to_collect[original_metric_name], tuple) \
            else original_metric_name

        return submit_method, self._normalize(metric_name, submit_method, prefix)

    def _normalize(self, metric_name, submit_method, prefix):
        """
        Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "mongodb." if not prefix else "mongodb.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == RATE else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in self.CASE_SENSITIVE_METRIC_NAME_SUFFIXES.iteritems():
            metric_name = re.compile(pattern).sub(repl, metric_name)

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.normalize(metric_name.lower()),
            metric_prefix=metric_prefix, metric_suffix=metric_suffix
        )

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
            'ssl_cert_reqs': instance.get('ssl_cert_reqs', None),
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
        clean_server_name = server.replace(password, "*" * 5) if password is not None else server

        additional_metrics = instance.get('additional_metrics', [])

        tags = instance.get('tags', [])
        tags.append('server:%s' % clean_server_name)

        # Get the list of metrics to collect
        collect_tcmalloc_metrics = 'tcmalloc' in additional_metrics
        metrics_to_collect = self._get_metrics_to_collect(
            server,
            additional_metrics
        )

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

        status = db.command('serverStatus', tcmalloc=collect_tcmalloc_metrics)
        if status['ok'] == 0:
            raise Exception(status['errmsg'].__str__())

        status['stats'] = db.command('dbstats')
        dbstats = {}
        dbstats[db_name] = {'stats': status['stats']}

        # Handle replica data, if any
        # See
        # http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus  # noqa
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
                tags.append('replset_state:%s' % self.REPLSET_STATES[data['state']])
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
        for metric_name in metrics_to_collect:
            # each metric is of the form: x.y.z with z optional
            # and can be found at status[x][y][z]
            value = status

            if metric_name.startswith('stats'):
                continue
            else:
                try:
                    for c in metric_name.split("."):
                        value = value[c]
                except KeyError:
                    continue

            # value is now status[x][y][z]
            if not isinstance(value, (int, long, float)):
                raise TypeError(
                    u"{0} value is a {1}, it should be an int, a float or a long instead."
                    .format(metric_name, type(value)))

            # Submit the metric
            submit_method, metric_name_alias = self._resolve_metric(metric_name, metrics_to_collect)
            submit_method(self, metric_name_alias, value, tags=tags)

        for st, value in dbstats.iteritems():
            for metric_name in metrics_to_collect:
                if not metric_name.startswith('stats.'):
                    continue

                try:
                    val = value['stats'][metric_name.split('.')[1]]
                except KeyError:
                    continue

                # value is now status[x][y][z]
                if not isinstance(val, (int, long, float)):
                    raise TypeError(
                        u"{0} value is a {1}, it should be an int, a float or a long instead."
                        .format(metric_name, type(val))
                    )

                # Submit the metric
                submit_method, metric_name_alias = \
                    self._resolve_metric(metric_name, metrics_to_collect)
                metrics_tags = tags + ['cluster:db:%s' % st]
                submit_method(self, metric_name_alias, val, tags=metrics_tags)

        # Report the usage metrics for dbs/collections
        if 'top' in additional_metrics:
            try:
                dbtop = db.command('top')
                for ns, ns_metrics in dbtop['totals'].iteritems():
                    if "." not in ns:
                        continue

                    # configure tags for db name and collection name
                    dbname, collname = ns.split(".", 1)
                    ns_tags = tags + ["db:%s" % dbname, "collection:%s" % collname]

                    # iterate over DBTOP metrics
                    for m in self.TOP_METRICS:
                        # each metric is of the form: x.y.z with z optional
                        # and can be found at ns_metrics[x][y][z]
                        value = ns_metrics
                        try:
                            for c in m.split("."):
                                value = value[c]
                        except Exception:
                            continue

                        # value is now status[x][y][z]
                        if not isinstance(value, (int, long, float)):
                            raise TypeError(
                                u"{0} value is a {1}, it should be an int, a float or a long instead."
                                .format(m, type(value))
                            )

                        # Submit the metric
                        submit_method, metric_name_alias = \
                            self._resolve_metric(m, metrics_to_collect, prefix="usage")
                        submit_method(self, metric_name_alias, value, tags=ns_tags)
            except Exception, e:
                self.log.warning('Failed to record `top` metrics %s' % str(e))

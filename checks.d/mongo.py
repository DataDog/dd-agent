# stdlib
import re
import time
import urllib

# 3p
import pymongo

# project
from checks import AgentCheck
from urlparse import urlsplit

DEFAULT_TIMEOUT = 30
GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate


class MongoDb(AgentCheck):
    """
    MongoDB agent check.

    # Metrics
    Metric available for collection are listed by topic as `MongoDb` class variables.

    Various metric topics are collected by default. Others require the
    corresponding option enabled in the check configuration file.

    ## Format
    Metrics are listed with the following format:
        ```
        metric_name -> metric_type
        ```
        or
        ```
        metric_name -> (metric_type, alias)*
        ```

    * `alias` parameter is optional, if unspecified, MongoDB metrics are reported
       with their original metric names.

    # Service checks
    Available service checks:
    * `mongodb.can_connect`
      Connectivity health to the instance.
    * `mongodb.replica_set_member_state`
      Disposition of the member replica set state.
    """
    # Source
    SOURCE_TYPE_NAME = 'mongodb'

    # Service check
    SERVICE_CHECK_NAME = 'mongodb.can_connect'

    # Metrics
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
        "fsyncLocked": GAUGE,
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
        "oplog.logSizeMB": GAUGE,
        "oplog.usedSizeMB": GAUGE,
        "oplog.timeDiff": GAUGE,
        "replSet.health": GAUGE,
        "replSet.replicationLag": GAUGE,
        "replSet.state": GAUGE,
        "replSet.votes": GAUGE,
        "replSet.voteFraction": GAUGE,
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
        "wiredTiger.cache.modified pages evicted": GAUGE,
        "wiredTiger.cache.pages currently held in the cache": (GAUGE, "wiredTiger.cache.pages_currently_held_in_cache"),  # noqa
        "wiredTiger.cache.pages evicted because they exceeded the in-memory maximum": (RATE, "wiredTiger.cache.pages_evicted_exceeding_the_in-memory_maximum"),  # noqa
        "wiredTiger.cache.pages evicted by application threads": RATE,
        "wiredTiger.cache.tracked dirty bytes in the cache": (GAUGE, "wiredTiger.cache.tracked_dirty_bytes_in_cache"),  # noqa
        "wiredTiger.cache.unmodified pages evicted": GAUGE,
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

    COLLECTION_METRICS = {
        'collection.size': GAUGE,
        'collection.avgObjSize': GAUGE,
        'collection.count': GAUGE,
        'collection.capped': GAUGE,
        'collection.max': GAUGE,
        'collection.maxSize': GAUGE,
        'collection.storageSize': GAUGE,
        'collection.nindexes': GAUGE,
        'collection.indexSizes': GAUGE,
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
    Metrics collected by default.
    """
    DEFAULT_METRICS = {
        'base': BASE_METRICS,
        'durability': DURABILITY_METRICS,
        'locks': LOCKS_METRICS,
        'wiredtiger': WIREDTIGER_METRICS,
    }

    """
    Additional metrics by category.
    """
    AVAILABLE_METRICS = {
        'metrics.commands': COMMANDS_METRICS,
        'tcmalloc': TCMALLOC_METRICS,
        'top': TOP_METRICS,
        'collection': COLLECTION_METRICS,
    }

    # Replication states
    """
    MongoDB replica set states, as documented at
    https://docs.mongodb.org/manual/reference/replica-states/
    """
    REPLSET_MEMBER_STATES = {
        0: ('STARTUP', 'Starting Up'),
        1: ('PRIMARY', 'Primary'),
        2: ('SECONDARY', 'Secondary'),
        3: ('RECOVERING', 'Recovering'),
        4: ('Fatal', 'Fatal'),   # MongoDB docs don't list this state
        5: ('STARTUP2', 'Starting up (forking threads)'),
        6: ('UNKNOWN', 'Unknown to this replset member'),
        7: ('ARBITER', 'Arbiter'),
        8: ('DOWN', 'Down'),
        9: ('ROLLBACK', 'Rollback'),
        10: ('REMOVED', 'Removed'),
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

        # Members' last replica set states
        self._last_state_by_server = {}

        # List of metrics to collect per instance
        self.metrics_to_collect_by_instance = {}

        self.collection_metrics_names = []
        for (key, value) in self.COLLECTION_METRICS.iteritems():
            self.collection_metrics_names.append(key.split('.')[1])

    def get_library_versions(self):
        return {"pymongo": pymongo.version}

    def get_state_description(self, state):
        if state in self.REPLSET_MEMBER_STATES:
            return self.REPLSET_MEMBER_STATES[state][1]
        else:
            return 'Replset state %d is unknown to the Datadog agent' % state

    def get_state_name(self, state):
        if state in self.REPLSET_MEMBER_STATES:
            return self.REPLSET_MEMBER_STATES[state][0]
        else:
            return 'UNKNOWN'

    def _report_replica_set_state(self, state, clean_server_name, replset_name, agentConfig):
        """
        Report the member's replica set state
        * Submit a service check.
        * Create an event on state change.
        """
        last_state = self._last_state_by_server.get(clean_server_name, -1)
        self._last_state_by_server[clean_server_name] = state
        if last_state != state and last_state != -1:
            return self.create_event(last_state, state, clean_server_name, replset_name, agentConfig)

    def hostname_for_event(self, clean_server_name, agentConfig):
        """Return a reasonable hostname for a replset membership event to mention."""
        uri = urlsplit(clean_server_name)
        if '@' in uri.netloc:
            hostname = uri.netloc.split('@')[1].split(':')[0]
        else:
            hostname = uri.netloc.split(':')[0]
        if hostname == 'localhost':
            hostname = self.hostname
        return hostname

    def create_event(self, last_state, state, clean_server_name, replset_name, agentConfig):
        """Create an event with a message describing the replication
            state of a mongo node"""

        status = self.get_state_description(state)
        short_status = self.get_state_name(state)
        last_short_status = self.get_state_name(last_state)
        hostname = self.hostname_for_event(clean_server_name, agentConfig)
        msg_title = "%s is %s for %s" % (hostname, short_status, replset_name)
        msg = "MongoDB %s (%s) just reported as %s (%s) for %s; it was %s before." % (hostname, clean_server_name, status, short_status, replset_name, last_short_status)

        self.event({
            'timestamp': int(time.time()),
            'source_type_name': self.SOURCE_TYPE_NAME,
            'msg_title': msg_title,
            'msg_text': msg,
            'host': hostname,
            'tags': [
                'action:mongo_replset_member_status_change',
                'member_status:' + short_status,
                'previous_member_status:' + last_short_status,
                'replset:' + replset_name,
            ]
        })

    def _build_metric_list_to_collect(self, additional_metrics):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Defaut metrics
        for default_metrics in self.DEFAULT_METRICS.itervalues():
            metrics_to_collect.update(default_metrics)

        # Additional metrics metrics
        for option in additional_metrics:
            additional_metrics = self.AVAILABLE_METRICS.get(option)
            if not additional_metrics:
                if option in self.DEFAULT_METRICS:
                    self.log.warning(
                        u"`%s` option is deprecated."
                        u" The corresponding metrics are collected by default.", option
                    )
                else:
                    self.log.warning(
                        u"Failed to extend the list of metrics to collect:"
                        u" unrecognized `%s` option", option
                    )
                continue

            self.log.debug(
                u"Adding `%s` corresponding metrics to the list"
                u" of metrics to collect.", option
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

    def _authenticate(self, database, username, password, use_x509):
        """
        Authenticate to the database.

        Available mechanisms:
        * Username & password
        * X.509

        More information:
        https://api.mongodb.com/python/current/examples/authentication.html
        """
        authenticated = False
        try:
            # X.509
            if use_x509:
                self.log.debug(
                    u"Authenticate `%s`  to `%s` using `MONGODB-X509` mechanism",
                    username, database
                )
                authenticated = database.authenticate(username, mechanism='MONGODB-X509')

            # Username & password
            else:
                authenticated = database.authenticate(username, password)

        except pymongo.errors.PyMongoError as e:
            self.log.error(
                u"Authentication failed due to invalid credentials or configuration issues. %s", e
            )

        return authenticated

    def check(self, instance):
        """
        Returns a dictionary that looks a lot like what's sent back by
        db.serverStatus()
        """

        def total_seconds(td):
            """
            Returns total seconds of a timedelta in a way that's safe for
            Python < 2.7
            """
            if hasattr(td, 'total_seconds'):
                return td.total_seconds()
            else:
                return (
                    lag.microseconds +
                    (lag.seconds + lag.days * 24 * 3600) * 10**6
                ) / 10.0**6

        if 'server' not in instance:
            raise Exception("Missing 'server' in mongo config")

        # x.509 authentication
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
        server = instance['server']
        parsed = pymongo.uri_parser.parse_uri(server)
        username = parsed.get('username')
        password = parsed.get('password')
        db_name = parsed.get('database')
        additional_metrics = instance.get('additional_metrics', [])

        # IF the password contains a URL encoded character (for example '/'), then the
        # raw server string will have %2F, but the password string will have the '/'.
        # Therefore, the string replace (below) won't work, because it won't have an
        # exact match.  Convert the password *back* to URL encoded, so the string
        # replace works properly.
        encoded_password = urllib.quote_plus(password) if password else None

        clean_server_name = server.replace(encoded_password, "*" * 5) if encoded_password else server

        if ssl_params:
            username_uri = u"{}@".format(urllib.quote(username))
            clean_server_name = clean_server_name.replace(username_uri, "")

        # Get the list of metrics to collect
        collect_tcmalloc_metrics = 'tcmalloc' in additional_metrics
        metrics_to_collect = self._get_metrics_to_collect(
            server,
            additional_metrics
        )

        # Tagging
        tags = instance.get('tags', [])
        # ...de-dupe tags to avoid a memory leak
        tags = list(set(tags))

        if not db_name:
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            db_name = 'admin'

        service_check_tags = [
            "db:%s" % db_name
        ]
        service_check_tags.extend(tags)

        # ...add the `server` tag to the metrics' tags only
        # (it's added in the backend for service checks)
        tags.append('server:%s' % clean_server_name)

        nodelist = parsed.get('nodelist')
        if nodelist:
            host = nodelist[0][0]
            port = nodelist[0][1]
            service_check_tags = service_check_tags + [
                "host:%s" % host,
                "port:%s" % port
            ]

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

        # Authenticate
        do_auth = True
        use_x509 = ssl_params and not password

        if not username:
            self.log.debug(
                u"A username is required to authenticate to `%s`", server
            )
            do_auth = False

        if do_auth and not self._authenticate(db, username, password, use_x509):
            message = u"Mongo: cannot connect with config `%s`" % clean_server_name
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags,
                message=message)
            raise Exception(message)

        try:
            status = db.command('serverStatus', tcmalloc=collect_tcmalloc_metrics)
        except Exception:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                tags=service_check_tags)
            raise
        else:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                tags=service_check_tags)

        if status['ok'] == 0:
            raise Exception(status['errmsg'].__str__())

        ops = db.current_op()
        status['fsyncLocked'] = 1 if ops.get('fsyncLock') else 0

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

                if do_auth and not self._authenticate(db, username, password, use_x509):
                    message = ("Mongo: cannot connect with config %s" % server)
                    self.service_check(
                        self.SERVICE_CHECK_NAME,
                        AgentCheck.CRITICAL,
                        tags=service_check_tags,
                        message=message)
                    raise Exception(message)

                # Replication set information
                replset_name = replSet['set']
                replset_state = self.get_state_name(replSet['myState']).lower()

                tags.extend([
                    u"replset_name:{0}".format(replset_name),
                    u"replset_state:{0}".format(replset_state),
                ])

                # Find nodes: master and current node (ourself)
                for member in replSet.get('members'):
                    if member.get('self'):
                        current = member
                    if int(member.get('state')) == 1:
                        primary = member

                # Compute a lag time
                if current is not None and primary is not None:
                    if 'optimeDate' in primary and 'optimeDate' in current:
                        lag = primary['optimeDate'] - current['optimeDate']
                        data['replicationLag'] = total_seconds(lag)

                if current is not None:
                    data['health'] = current['health']

                data['state'] = replSet['myState']

                if current is not None:
                    total = 0.0
                    cfg = cli['local']['system.replset'].find_one()
                    for member in cfg.get('members'):
                        total += member.get('votes', 1)
                        if member['_id'] == current['_id']:
                            data['votes'] = member.get('votes', 1)
                    data['voteFraction'] = data['votes'] / total

                status['replSet'] = data

                # Submit events
                self._report_replica_set_state(
                    data['state'], clean_server_name, replset_name, self.agentConfig
                )

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
                metrics_tags = (
                    tags +
                    [
                        u"cluster:db:{0}".format(st),  # FIXME 6.0 - keep for backward compatibility
                        u"db:{0}".format(st),
                    ]
                )

                submit_method, metric_name_alias = \
                    self._resolve_metric(metric_name, metrics_to_collect)
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
            except Exception as e:
                self.log.warning('Failed to record `top` metrics %s' % str(e))


        if 'local' in dbnames: # it might not be if we are connectiing through mongos
            # Fetch information analogous to Mongo's db.getReplicationInfo()
            localdb = cli['local']

            oplog_data = {}

            for ol_collection_name in ("oplog.rs", "oplog.$main"):
                ol_metadata = localdb.system.namespaces.find_one({"name": "local.%s" % ol_collection_name})
                if ol_metadata:
                    break

            if ol_metadata:
                try:
                    oplog_data['logSizeMB'] = round(
                        ol_metadata['options']['size'] / 2.0 ** 20, 2
                    )

                    oplog = localdb[ol_collection_name]

                    oplog_data['usedSizeMB'] = round(
                        localdb.command("collstats", ol_collection_name)['size'] / 2.0 ** 20, 2
                    )

                    op_asc_cursor = oplog.find().sort("$natural", pymongo.ASCENDING).limit(1)
                    op_dsc_cursor = oplog.find().sort("$natural", pymongo.DESCENDING).limit(1)

                    try:
                        first_timestamp = op_asc_cursor[0]['ts'].as_datetime()
                        last_timestamp = op_dsc_cursor[0]['ts'].as_datetime()
                        oplog_data['timeDiff'] = total_seconds(last_timestamp - first_timestamp)
                    except (IndexError, KeyError):
                        # if the oplog collection doesn't have any entries
                        # if an object in the collection doesn't have a ts value, we ignore it
                        pass
                except KeyError:
                    # encountered an error trying to access options.size for the oplog collection
                    self.log.warning(u"Failed to record `ReplicationInfo` metrics.")

            for (m, value) in oplog_data.iteritems():
                submit_method, metric_name_alias = \
                    self._resolve_metric('oplog.%s' % m, metrics_to_collect)
                submit_method(self, metric_name_alias, value, tags=tags)

        else:
            self.log.debug('"local" database not in dbnames. Not collecting ReplicationInfo metrics')

        # get collection level stats
        try:
            # Ensure that you're on the right db
            db = cli[db_name]
            # grab the collections from the configutation
            coll_names = instance.get('collections', [])
            # loop through the collections
            for coll_name in coll_names:
                # grab the stats from the collection
                stats = db.command("collstats", coll_name)
                # loop through the metrics
                for m in self.collection_metrics_names:
                    coll_tags = tags + ["db:%s" % db_name, "collection:%s" % coll_name]
                    value = stats.get(m, None)
                    if not value:
                        continue

                    # if it's the index sizes, then it's a dict.
                    if m == 'indexSizes':
                        submit_method, metric_name_alias = \
                            self._resolve_metric('collection.%s' % m, self.COLLECTION_METRICS)
                        # loop through the indexes
                        for (idx, val) in value.iteritems():
                            # we tag the index
                            idx_tags = coll_tags + ["index:%s" % idx]
                            submit_method(self, metric_name_alias, val, tags=idx_tags)
                    else:
                        submit_method, metric_name_alias = \
                            self._resolve_metric('collection.%s' % m, self.COLLECTION_METRICS)
                        submit_method(self, metric_name_alias, value, tags=coll_tags)
        except Exception as e:
            self.log.warning(u"Failed to record `collection` metrics.")
            self.log.exception(e)

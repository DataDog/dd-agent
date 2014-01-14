import re
import types
import time

from checks import AgentCheck
from util import get_hostname

# When running with pymongo < 2.0
# Not the full spec for mongo URIs -- just extract username and password
# http://www.mongodb.org/display/DOCS/connections6
mongo_uri_re=re.compile(r'mongodb://(?P<username>[^:@]+):(?P<password>[^:@]+)@.*')

DEFAULT_TIMEOUT = 10

class MongoDb(AgentCheck):

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
        "replSet.replicationLag"
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
        "asserts.regular",
        "asserts.warning",
        "asserts.msg",
        "asserts.user",
        "asserts.rollovers"
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
            elif state == 5: return 'Starting up (forking threads)'
            elif state == 6: return 'Unknown'
            elif state == 7: return 'Arbiter'
            elif state == 8: return 'Down'
            elif state == 9: return 'Rollback'

        status = get_state_description(state)
        hostname = get_hostname(agentConfig)
        msg_title = "%s is %s" % (server, status)
        msg = "MongoDB %s just reported as %s" % (server, status)

        self.event({
            'timestamp': int(time.time()),
            'event_type': 'Mongo',
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
            self.log.warn("Missing 'server' in mongo config")
            return

        server = instance['server']
        tags = instance.get('tags', [])
        tags.append('server:%s' % server)
        # de-dupe tags to avoid a memory leak
        tags = list(set(tags))

        try:
            from pymongo import Connection
        except ImportError:
            self.log.error('mongo.yaml exists but pymongo module can not be imported. Skipping check.')
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
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            db_name = 'admin'

        do_auth = True
        if username is None or password is None:
            self.log.debug("Mongo: cannot extract username and password from config %s" % server)
            do_auth = False

        conn = Connection(server, network_timeout=DEFAULT_TIMEOUT)
        db = conn[db_name]
        if do_auth:
            if not db.authenticate(username, password):
                self.log.error("Mongo: cannot connect with config %s" % server)

        status = db["$cmd"].find_one({"serverStatus": 1})
        status['stats'] = db.command('dbstats')

        # Handle replica data, if any
        # See http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus
        try:
            data = {}

            replSet = db.command('replSetGetStatus')
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
                    lag = current['optimeDate'] - primary['optimeDate']
                    # Python 2.7 has this built in, python < 2.7 don't...
                    if hasattr(lag,'total_seconds'):
                        data['replicationLag'] = lag.total_seconds()
                    else:
                        data['replicationLag'] = (lag.microseconds + \
            (lag.seconds + lag.days * 24 * 3600) * 10**6) / 10.0**6

                if current is not None:
                    data['health'] = current['health']

                data['state'] = replSet['myState']
                self.check_last_state(data['state'], server, self.agentConfig)
                status['replSet'] = data
        except Exception, e:
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
                m = self.normalize(m.lower(), 'mongodb')
                self.gauge(m, value, tags=tags)

            if m in self.RATES:
                m = self.normalize(m.lower(), 'mongodb') + "ps"
                self.rate(m, value, tags=tags)

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('mongodb_server'):
            return False

        return {
            'instances': [{
                'server': agentConfig.get('mongodb_server')
            }]
        }

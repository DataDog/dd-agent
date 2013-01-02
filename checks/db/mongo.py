import re
import types
from datetime import datetime

from checks import *

# When running with pymongo < 2.0
# Not the full spec for mongo URIs -- just extract username and password
# http://www.mongodb.org/display/DOCS/connections6
mongo_uri_re=re.compile(r'mongodb://(?P<username>[^:@]+):(?P<password>[^:@]+)@.*')

class MongoDb(Check):

    def __init__(self, logger):

        Check.__init__(self, logger)

        self._last_state = -1

        self.counter("indexCounters.btree.accesses")
        self.counter("indexCounters.btree.hits")
        self.counter("indexCounters.btree.misses")
        self.gauge("indexCounters.btree.missRatio")
        self.counter("opcounters.insert")
        self.counter("opcounters.query")
        self.counter("opcounters.update")
        self.counter("opcounters.delete")
        self.counter("opcounters.getmore")
        self.counter("opcounters.command")
        self.counter("asserts.regular")
        self.counter("asserts.warning")
        self.counter("asserts.msg")
        self.counter("asserts.user")
        self.counter("asserts.rollovers")
        self.gauge("globalLock.ratio")
        self.gauge("connections.current")
        self.gauge("connections.available")
        self.gauge("mem.resident")
        self.gauge("mem.virtual")
        self.gauge("mem.mapped")
        self.gauge("cursors.totalOpen")
        self.gauge("cursors.timedOut")
        self.gauge("uptime")

        self.gauge("stats.indexes")
        self.gauge("stats.indexSize")
        self.gauge("stats.objects")
        self.gauge("stats.dataSize")
        self.gauge("stats.storageSize")

        self.gauge("replSet.health")
        self.gauge("replSet.state")
        self.gauge("replSet.replicationLag")

    def checkLastState(self, state, agentConfig, serverVersion):
        if self._last_state != state:
            self._last_state = state
            return self.create_event(state, agentConfig, serverVersion)

    def create_event(self, state, agentConfig, serverVersion):
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

        return { 'timestamp': int(time.mktime(datetime.now().timetuple())),
                 'event_type': 'Mongo',
                 'host': gethostname(agentConfig),
                 'api_key': agentConfig['api_key'],
                 'version': serverVersion,
                 'state': get_state_description(state) }

    def check(self, agentConfig):
        """
        Returns a dictionary that looks a lot like what's sent back by db.serverStatus()
        """

        if 'mongodb_server' not in agentConfig or agentConfig['mongodb_server'] == '':
            return False

        try:
            from pymongo import Connection
            try:
                from pymongo import uri_parser
                # Configuration a URL, mongodb://user:pass@server/db
                parsed = uri_parser.parse_uri(agentConfig['mongodb_server'])
            except ImportError:
                # uri_parser is pymongo 2.0+
                matches = mongo_uri_re.match(agentConfig['mongodb_server'])
                if matches:
                    parsed = matches.groupdict()
                else:
                    parsed = {}
            username = parsed.get('username')
            password = parsed.get('password')

            do_auth = True
            if username is None or password is None:
                self.logger.debug("Mongo: cannot extract username and password from config %s" % agentConfig['mongodb_server'])
                do_auth = False

            conn = Connection(agentConfig['mongodb_server'])
            db = conn['admin']
            if do_auth:
                if not db.authenticate(username, password):
                    lef.logger.error("Mongo: cannot connect with config %s" % agentConfig['mongodb_server'])

            status = db.command('serverStatus') # Shorthand for {'serverStatus': 1}
            status['stats'] = db.command('dbstats')

            results = {}

            # Handle replica data, if any
            # See http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus
            try:
                data = {}

                replSet = db.command('replSetGetStatus')
                serverVersion = conn.server_info()['version']
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
                    event = self.checkLastState(data['state'], agentConfig, serverVersion)
                    if event is not None:
                        results['events'] = {'Mongo': [event]}
                    status['replSet'] = data
            except:
                self.logger.debug("Cannot determine replication set status", exc_info=True)

            # If these keys exist, remove them for now as they cannot be serialized
            try:
                status['backgroundFlushing'].pop('last_finished')
            except KeyError:
                pass
            try:
                status.pop('localTime')
            except KeyError:
                pass

            # Flatten the metrics first
            # Collect samples
            # Send a dictionary back

            for m in self.get_metric_names():
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

                self.save_sample(m, value)

                # opposite op: x.y.z -> results[x][y][zPS], yes, ...PS for counters
                try:
                    val = self.get_sample(m)
                    r = results
                    for c in m.split(".")[:-1]:
                        if c not in r:
                            r[c] = {}
                        r = r[c]
                    if self.is_counter(m):
                        suffix = m.split(".")[-1] + "PS"
                    else:
                        suffix = m.split(".")[-1]
                    r[suffix] = val

                except UnknownValue:
                    pass

            return results

        except ImportError:
            self.logger.exception('Unable to import pymongo library')
            return False

        except:
            self.logger.exception('Unable to get MongoDB status')
            return False

if __name__ == "__main__":
    import logging
    agentConfig = { 'mongodb_server': 'localhost:27017', 'api_key': 'toto' }
    db = MongoDb(logging)
    print db.check(agentConfig)


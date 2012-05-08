import re
import types

# Not the full spec for mongo URIs
# http://www.mongodb.org/display/DOCS/Connections
mongo_uri_re=re.compile(r"^mongodb://[^/]+/(\w+)$")

from checks import *

class MongoDb(Check):

    def __init__(self, logger):
        Check.__init__(self, logger)
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

    def check(self, agentConfig):
        """
        Returns a dictionary that looks a lot like what's sent back by db.serverStatus()
        """
        if 'MongoDBServer' not in agentConfig or agentConfig['MongoDBServer'] == '':
            return False

        try:
            from pymongo import Connection

            # Configuration a URL, mongodb://user:pass@server/db
            dbName = mongo_uri_re.match(agentConfig['MongoDBServer']).group(1)

            conn = Connection(agentConfig['MongoDBServer'])
            db = conn[dbName]

            status = db.command('serverStatus') # Shorthand for {'serverStatus': 1}
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
                    status['replSet'] = data
            except:
                self.logger.exception("Cannot determine replication set status")

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
            results = {}

            for m in self.get_metrics():
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
    agentConfig = { 'MongoDBServer': 'localhost:27017' }
    db = MongoDb(logging)
    print db.check(agentConfig)
   

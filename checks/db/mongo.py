import types

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

    def check(self, agentConfig):
        """
        Returns a dictionary that looks a lot like what's sent back by db.serverStatus()
        """
        if 'MongoDBServer' not in agentConfig or agentConfig['MongoDBServer'] == '':
            return False

        try:
            from pymongo import Connection

            dbName = 'local'
            conn = Connection(agentConfig['MongoDBServer'])
            db = conn[dbName]

            status = db.command('serverStatus') # Shorthand for {'serverStatus': 1}
            status['stats'] = db.command('dbstats')

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
   

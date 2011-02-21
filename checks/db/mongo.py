class MongoDb(Check):
    def check(self, logger, agentConfig):

        if 'MongoDBServer' not in agentConfig or agentConfig['MongoDBServer'] == '':
            return False

        try:
            import pymongo
            from pymongo import Connection
        except ImportError:
            logger.exception('Unable to import pymongo library')
            return False

        # The dictionary to be returned.
        mongodb = {}

        try:
            conn = Connection(agentConfig['MongoDBServer'])
        except:
            logger.exception('Unable to connect to MongoDB server')
            return False

        try:
            dbName = 'local'
            db = conn[dbName]
            status = db.command('serverStatus') # Shorthand for {'serverStatus': 1}
            # If these keys exist, remove them for now as they cannot be serialized
            try:
                status['backgroundFlushing'].pop('last_finished')
            except KeyError:
                pass
            try:
                status.pop('localTime')
            except KeyError:
                pass

            if self.mongoDBStore == None:
                logger.debug('getMongoDBStatus: no cached data, so storing for first time')
                self._clearMongoDBStatus(status)
            else:
                logger.debug('getMongoDBStatus: cached data exists, so calculating per sec metrics')
                accessesPS = float(status['indexCounters']['btree']['accesses'] - self.mongoDBStore['indexCounters']['btree']['accesses']) / 60
                
                if accessesPS >= 0:
                    status['indexCounters']['btree']['accessesPS'] = accessesPS
                    status['indexCounters']['btree']['hitsPS'] = float(status['indexCounters']['btree']['hits'] - self.mongoDBStore['indexCounters']['btree']['hits']) / 60
                    status['indexCounters']['btree']['missesPS'] = float(status['indexCounters']['btree']['misses'] - self.mongoDBStore['indexCounters']['btree']['misses']) / 60
                    status['indexCounters']['btree']['missRatioPS'] = float(status['indexCounters']['btree']['missRatio'] - self.mongoDBStore['indexCounters']['btree']['missRatio']) / 60
                    status['opcounters']['insertPS'] = float(status['opcounters']['insert'] - self.mongoDBStore['opcounters']['insert']) / 60
                    status['opcounters']['queryPS'] = float(status['opcounters']['query'] - self.mongoDBStore['opcounters']['query']) / 60
                    status['opcounters']['updatePS'] = float(status['opcounters']['update'] - self.mongoDBStore['opcounters']['update']) / 60
                    status['opcounters']['deletePS'] = float(status['opcounters']['delete'] - self.mongoDBStore['opcounters']['delete']) / 60
                    status['opcounters']['getmorePS'] = float(status['opcounters']['getmore'] - self.mongoDBStore['opcounters']['getmore']) / 60
                    status['opcounters']['commandPS'] = float(status['opcounters']['command'] - self.mongoDBStore['opcounters']['command']) / 60
                    status['asserts']['regularPS'] = float(status['asserts']['regular'] - self.mongoDBStore['asserts']['regular']) / 60
                    status['asserts']['warningPS'] = float(status['asserts']['warning'] - self.mongoDBStore['asserts']['warning']) / 60
                    status['asserts']['msgPS'] = float(status['asserts']['msg'] - self.mongoDBStore['asserts']['msg']) / 60
                    status['asserts']['userPS'] = float(status['asserts']['user'] - self.mongoDBStore['asserts']['user']) / 60
                    status['asserts']['rolloversPS'] = float(status['asserts']['rollovers'] - self.mongoDBStore['asserts']['rollovers']) / 60
                else:
                    logger.debug('getMongoDBStatus: negative value calculated, mongod likely restarted, so clearing cache')
                    self._clearMongoDBStatus(status)

            self.mongoDBStore = status
            mongodb = status
        except:
            logger.exception('Unable to get MongoDB status')
            return False

        return mongodb


    def _clearMongoDBStatus(self, status):
        status['indexCounters']['btree']['accessesPS'] = 0
        status['indexCounters']['btree']['hitsPS'] = 0
        status['indexCounters']['btree']['missesPS'] = 0
        status['indexCounters']['btree']['missRatioPS'] = 0
        status['opcounters']['insertPS'] = 0
        status['opcounters']['queryPS'] = 0
        status['opcounters']['updatePS'] = 0
        status['opcounters']['deletePS'] = 0
        status['opcounters']['getmorePS'] = 0
        status['opcounters']['commandPS'] = 0
        status['asserts']['regularPS'] = 0
        status['asserts']['warningPS'] = 0
        status['asserts']['msgPS'] = 0
        status['asserts']['userPS'] = 0
        status['asserts']['rolloversPS'] = 0

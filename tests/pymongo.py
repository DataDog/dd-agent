try:
    import json
except ImportError:
    import simplejson as json

class MockMongo(object):
    delta = 10191 - 2893 # seconds elapsed between both samples
    stats1 = """{
        "version" : "1.6.5",
        "uptime" : 2893,
        "uptimeEstimate" : 2864,
        "localTime" : "Mon Feb 21 2011 14:14:25 GMT-0500 (EST)",
        "globalLock" : {
                "totalTime" : 2892839699,
                "lockTime" : 74,
                "ratio" : 2.5580401162767645e-8,
                "currentQueue" : {
                        "total" : 0,
                        "readers" : 0,
                        "writers" : 0
                }
        },
        "mem" : {
                "bits" : 64,
                "resident" : 5,
                "virtual" : 173,
                "supported" : true,
                "mapped" : 0
        },
        "connections" : {
                "current" : 1,
                "available" : 818
        },
        "extra_info" : {
                "note" : "fields vary by platform",
                "heap_usage_bytes" : 219136,
                "page_faults" : 3
        },
        "indexCounters" : {
                "btree" : {
                        "accesses" : 0,
                        "hits" : 0,
                        "misses" : 0,
                        "resets" : 0,
                        "missRatio" : 0
                }
        },
        "backgroundFlushing" : {
                "flushes" : 48,
                "total_ms" : 0,
                "average_ms" : 0,
                "last_ms" : 0,
                "last_finished" : "Mon Feb 21 2011 14:14:12 GMT-0500 (EST)"
        },
        "cursors" : {
                "totalOpen" : 0,
                "clientCursors_size" : 0,
                "timedOut" : 0
        },
        "opcounters" : {
                "insert" : 0,
                "query" : 1,
                "update" : 0,
                "delete" : 0,
                "getmore" : 0,
                "command" : 18
        },
        "asserts" : {
                "regular" : 0,
                "warning" : 0,
                "msg" : 0,
                "user" : 0,
                "rollovers" : 0
        },
       "ok" : 1
    }"""

    stats2= """{
        "version" : "1.6.5",
        "uptime" : 10191,
        "uptimeEstimate" : 10093,
        "localTime" : "Mon Feb 21 2011 16:16:03 GMT-0500 (EST)",
        "globalLock" : {
                "totalTime" : 10190978504,
                "lockTime" : 74,
                "ratio" : 7.2613243145351255e-9,
                "currentQueue" : {
                        "total" : 0,
                        "readers" : 0,
                        "writers" : 0
                }
        },
        "mem" : {
                "bits" : 64,
                "resident" : 5,
                "virtual" : 183,
                "supported" : true,
                "mapped" : 0
        },
        "connections" : {
                "current" : 1,
                "available" : 818
        },
        "extra_info" : {
                "note" : "fields vary by platform",
                "heap_usage_bytes" : 219200,
                "page_faults" : 3
        },
        "indexCounters" : {
                "btree" : {
                        "accesses" : 0,
                        "hits" : 0,
                        "misses" : 0,
                        "resets" : 0,
                        "missRatio" : 0
                }
        },
        "backgroundFlushing" : {
                "flushes" : 169,
                "total_ms" : 2,
                "average_ms" : 0.011834319526627219,
                "last_ms" : 0,
                "last_finished" : "Mon Feb 21 2011 16:15:12 GMT-0500 (EST)"
        },
        "cursors" : {
                "totalOpen" : 0,
                "clientCursors_size" : 0,
                "timedOut" : 0
        },
        "opcounters" : {
                "insert" : 0,
                "query" : 1,
                "update" : 0,
                "delete" : 0,
                "getmore" : 0,
                "command" : 244
        },
        "asserts" : {
                "regular" : 0,
                "warning" : 0,
                "msg" : 0,
                "user" : 0,
                "rollovers" : 0
        },
        "ok" : 1
    }"""
    
    def __init__(self):
        self.firstRun = False

    def __getitem__(self, ignore):
        """Connection(config)['dbname']"""
        return self

    def command(self, ignore):
        if self.firstRun:
            self.firstRun = False
            return json.loads(self.stats1)
        else:
            return json.loads(self.stats2)

def Connection(ignore):
    return MockMongo()

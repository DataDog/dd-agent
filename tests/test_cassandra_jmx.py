import logging
import unittest
import os
import os.path
import time

from nose.plugins.attrib import attr

from checks.cassandra import Cassandra


from tests.common import kill_subprocess, load_check




logger = logging.getLogger(__name__)

class TestCassandra(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    @attr('cassandra_jmx')
    def testCassandraJmx(self):
        agentConfig = {
            'version': '0.1',
            'api_key': 'toto'
        }

        c = load_check('cassandra', CASSANDRA_CONF, agentConfig)

        timers_first_check = []
        for instance in CASSANDRA_CONF['instances']:
            start = time.time()
            c.check(instance)
            timers_first_check.append(time.time() - start)

        metrics = c.get_metrics()
        self.assertTrue(type(metrics) == type([]))
        self.assertTrue(len(metrics) > 20, metrics)

        timers_second_check = []
        for instance in CASSANDRA_CONF['instances']:
            start = time.time()
            c.check(instance)
            timers_second_check.append(time.time() - start)

        c.kill_jmx_connectors()

        b={}
        for k in metrics:
          b[k[0]]="1"

        for k in metrics:
            print "{0}".format((k[0], k[3]['tags']))
        raise Exception(b.keys())


        self.assertEquals(len([t for t in timers_first_check if t > 10]), 0, timers_first_check)
        self.assertEquals(len([t for t in timers_second_check if t > 1.5]), 0, timers_second_check)


CASSANDRA_CONF = {'init_config': {'conf': [{'exclude': {'attribute': ['MinimumCompactionThreshold',
                                                     'MaximumCompactionThreshold',
                                                     'RowCacheKeysToSave',
                                                     'KeyCacheSavePeriodInSeconds',
                                                     'RowCacheSavePeriodInSeconds',
                                                     'PendingTasks',
                                                     'Scores',
                                                     'RpcTimeout'],
                                       'keyspace': 'system'},
                           'include': {'attribute': ['BloomFilterDiskSpaceUsed',
                                                     'BloomFilterFalsePositives',
                                                     'BloomFilterFalseRatio',
                                                     'Capacity',
                                                     'CompressionRatio',
                                                     'CompletedTasks',
                                                     'ExceptionCount',
                                                     'Hits',
                                                     'RecentHitRate',
                                                     'LiveDiskSpaceUsed',
                                                     'LiveSSTableCount',
                                                     'Load',
                                                     'MaxRowSize',
                                                     'MeanRowSize',
                                                     'MemtableColumnsCount',
                                                     'MemtableDataSize',
                                                     'MemtableSwitchCount',
                                                     'MinRowSize',
                                                     'ReadCount',
                                                     'Requests',
                                                     'Size',
                                                     'TotalDiskSpaceUsed',
                                                     'TotalReadLatencyMicros',
                                                     'TotalWriteLatencyMicros',
                                                     'UpdateInterval',
                                                     'WriteCount'],
                                       'domain': 'org.apache.cassandra.db'}},
                          {'exclude': {'attribute': ['PendingTasks',
                                                     'Token']},
                           'include': {'attribute': ['ActiveCount',
                                                     'CompletedTasks',
                                                     'CurrentlyBlockedTasks',
                                                     'TotalBlockedTasks'],
                                       'domain': 'org.apache.cassandra.internal'}},
                          {'include': {'attribute': ['TotalTimeouts'],
                                       'domain': 'org.apache.cassandra.net'}}]},
 'instances': [{'host': 'localhost', 'port': 7199}]}
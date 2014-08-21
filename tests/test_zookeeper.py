import unittest
from StringIO import StringIO
from tests.common import get_check
from checks import AgentCheck

CONFIG = """
init_config:

instances:
    - host: 127.0.0.1
      port: 2181
      expected_mode: follower
      tags: []
"""

CONFIG2 = """
init_config:

instances:
    - host: 127.0.0.1
      port: 2182
      tags: []
"""

class TestZookeeper(unittest.TestCase):
    def test_zk_stat_parsing_lt_v344(self):
        zk, instances = get_check('zk', CONFIG)
        stat_response = """Zookeeper version: 3.2.2--1, built on 03/16/2010 07:31 GMT
Clients:
 /10.42.114.160:32634[1](queued=0,recved=12,sent=0)
 /10.37.137.74:21873[1](queued=0,recved=53613,sent=0)
 /10.37.137.74:21876[1](queued=0,recved=57436,sent=0)
 /10.115.77.32:32990[1](queued=0,recved=16,sent=0)
 /10.37.137.74:21891[1](queued=0,recved=55011,sent=0)
 /10.37.137.74:21797[1](queued=0,recved=19431,sent=0)

Latency min/avg/max: -10/0/20007
Received: 101032173
Sent: 0
Outstanding: 0
Zxid: 0x1034799c7
Mode: leader
Node count: 487
"""
        expected = [
            ('zookeeper.latency.min',              -10),
            ('zookeeper.latency.avg',                0),
            ('zookeeper.latency.max',            20007),
            ('zookeeper.bytes_received',    101032173L),
            ('zookeeper.bytes_sent',                0L),
            ('zookeeper.connections',                6),
            ('zookeeper.bytes_outstanding',         0L),
            ('zookeeper.zxid.epoch',                 1),
            ('zookeeper.zxid.count',          55024071),
            ('zookeeper.nodes',                    487L),
        ]

        buf = StringIO(stat_response)
        metrics, tags, mode = zk.parse_stat(buf)

        self.assertEquals(tags, ['mode:leader'])
        self.assertEquals(metrics, expected)

        zk.check(instances[0])
        service_checks = zk.get_service_checks()
        self.assertEquals(len(service_checks), 2)
        self.assertEquals(service_checks[0]['check'], 'zookeeper.ruok')
        # Don't check status of ruok because it can vary if ZK is running.
        self.assertEquals(service_checks[1]['check'], 'zookeeper.mode')
        self.assertEquals(service_checks[1]['status'], AgentCheck.CRITICAL)

    def test_zk_stat_parsing_gte_v344(self):
        zk, instances = get_check('zk', CONFIG2)
        stat_response = """Zookeeper version: 3.4.5--1, built on 03/16/2010 07:31 GMT
Clients:
 /10.42.114.160:32634[1](queued=0,recved=12,sent=0)
 /10.37.137.74:21873[1](queued=0,recved=53613,sent=0)
 /10.37.137.74:21876[1](queued=0,recved=57436,sent=0)
 /10.115.77.32:32990[1](queued=0,recved=16,sent=0)
 /10.37.137.74:21891[1](queued=0,recved=55011,sent=0)
 /10.37.137.74:21797[1](queued=0,recved=19431,sent=0)

Latency min/avg/max: -10/0/20007
Received: 101032173
Sent: 0
Connections: 1
Outstanding: 0
Zxid: 0x1034799c7
Mode: leader
Node count: 487
"""
        expected = [
            ('zookeeper.latency.min',              -10),
            ('zookeeper.latency.avg',                0),
            ('zookeeper.latency.max',            20007),
            ('zookeeper.bytes_received',    101032173L),
            ('zookeeper.bytes_sent',                0L),
            ('zookeeper.connections',                1),
            ('zookeeper.bytes_outstanding',         0L),
            ('zookeeper.zxid.epoch',                 1),
            ('zookeeper.zxid.count',          55024071),
            ('zookeeper.nodes',                    487L),
        ]

        buf = StringIO(stat_response)
        metrics, tags, mode = zk.parse_stat(buf)

        self.assertEquals(tags, ['mode:leader'])
        self.assertEquals(metrics, expected)

        zk.check(instances[0])
        service_checks = zk.get_service_checks()
        self.assertEquals(len(service_checks), 1)
        self.assertEquals(service_checks[0]['check'], 'zookeeper.ruok')
        self.assertEquals(service_checks[0]['status'], AgentCheck.CRITICAL)

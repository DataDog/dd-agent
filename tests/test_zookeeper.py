import unittest
from StringIO import StringIO
from tests.common import get_check

CONFIG = """
init_config:

instances:
    - host: 127.0.0.1
      port: 2181
      tags: []
"""

class TestZookeeper(unittest.TestCase):
    def test_zk_stat_parsing(self):
        Zookeeper, instances = get_check('zk', CONFIG)
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
            ('zookeeper.clients',                    6),
            ('zookeeper.latency.min',              -10),
            ('zookeeper.latency.avg',                0),
            ('zookeeper.latency.max',            20007),
            ('zookeeper.bytes_received',    101032173L),
            ('zookeeper.bytes_sent',                0L),
            ('zookeeper.bytes_outstanding',         0L),
            ('zookeeper.zxid.epoch',                 1),
            ('zookeeper.zxid.count',          55024071),
            ('zookeeper.nodes',                    487L),
        ]

        buf = StringIO(stat_response)
        metrics, tags = Zookeeper.parse_stat(buf)

        self.assertEquals(tags, ['mode:leader'])
        self.assertEquals(metrics, expected)


import unittest
import os
import os.path

from checks.cassandra import Cassandra

class TestCassandra(unittest.TestCase):
    def setUp(self):
        self.info = open(os.path.join("cassandra", "info"), "r").read()
        self.tpstats = open(os.path.join("cassandra", "tpstats"), "r").read()
        self.cfstats = open(os.path.join("cassandra", "cfstats"), "r").read()
        self.c = Cassandra()
        
    def tearDown(self):
        pass
        
    def testParseInfo(self):
        res = {}
        self.c._parseInfo(self.info, res)
        self.assertNotEquals(len(res.keys()), 0)
        # {'load': '457.02', 'token': '36299342986353445520010708318471778930', 'uptime': '95', 'heap': '521.86'}
        self.assertEquals(res.get("load"), "467988")
        self.assertEquals(res.get("token"), "36299342986353445520010708318471778930")
        self.assertEquals(res.get("uptime"), "95")
        self.assertEquals(res.get("heap_used"), "521.86")
        self.assertEquals(res.get("heap_total"), "1019.88")
        
    def testParseCfstats(self):
        res = {}
        self.c._parseCfstats(self.cfstats, res)
        self.assertNotEquals(len(res.keys()), 0)
        
    def testParseTpstats(self):
        res = {}
        self.c._parseTpstats(self.tpstats, res)
        self.assertNotEquals(len(res.keys()), 0)
        
if __name__ == '__main__':
    unittest.main()
